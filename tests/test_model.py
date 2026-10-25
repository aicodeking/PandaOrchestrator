import json
import math

import numpy as np
import pytest
import torch

from panda_router.model.corn import corn_level_probs, corn_loss, corn_targets_to_logits, soft_to_corn_targets
from panda_router.model.decode import corn_probs_np
from panda_router.model.losses import head_losses, pair_loss, parse_delta
from panda_router.model.soft_matcher import CardPool, p_success, regret_loss, sample_pools
from panda_router.profile import TaskProfile
from panda_router.taxonomy import CATEGORIES, CHECKLIST_IDS, FLAGS, SKILL_AXES

TOKENIZER = "jhu-clsp/ettin-encoder-32m"


# ---------------------------------------------------------------- CORN
def test_corn_round_trip():
    g = torch.Generator().manual_seed(0)
    q = torch.softmax(torch.randn(64, 10, generator=g, dtype=torch.float64) * 2, -1)
    t, w = soft_to_corn_targets(q)
    assert t.shape == (64, 9) and w.shape == (64, 9)
    probs = corn_level_probs(corn_targets_to_logits(t, 1e-12))
    assert torch.allclose(probs, q, atol=1e-8)
    assert np.allclose(corn_probs_np(corn_targets_to_logits(t, 1e-12).numpy()), q.numpy(), atol=1e-8)


def test_corn_loss_minimised_at_target_logits():
    q = torch.softmax(torch.randn(8, 11, dtype=torch.float64), -1)
    logits = corn_targets_to_logits(soft_to_corn_targets(q)[0]).requires_grad_(True)
    corn_loss(logits, q).backward()
    assert logits.grad.abs().max() < 1e-6


def test_corn_handles_degenerate_targets():
    q = torch.zeros(3, 10)
    q[0, 0], q[1, 9], q[2, 4] = 1, 1, 1
    logits = torch.zeros(3, 9, requires_grad=True)
    loss = corn_loss(logits, q)
    loss.backward()
    assert torch.isfinite(loss) and torch.isfinite(logits.grad).all()


# ---------------------------------------------------------------- losses
def _fake_out(b=4, requires_grad=True):
    out = {"category": torch.randn(b, len(CATEGORIES)), "difficulty": torch.randn(b, 9),
           "skills": torch.randn(b, len(SKILL_AXES), 10), "flags": torch.randn(b, len(FLAGS)),
           "checklist": torch.randn(b, len(CHECKLIST_IDS)), "out_tokens": torch.randn(b, 3).sort(-1).values + 3}
    return {k: v.requires_grad_(requires_grad) for k, v in out.items()}


def _fake_y(b=4):
    return {"category": torch.softmax(torch.randn(b, len(CATEGORIES)), -1),
            "difficulty": torch.softmax(torch.randn(b, 10), -1),
            "skills": torch.softmax(torch.randn(b, len(SKILL_AXES), 11), -1),
            "flags": torch.rand(b, len(FLAGS)), "checklist": torch.rand(b, len(CHECKLIST_IDS)),
            "out_tokens": torch.rand(b) + 3, "in_tokens": torch.full((b,), 4000.0)}


def test_head_losses_shapes_and_grads():
    out, y = _fake_out(), _fake_y()
    losses = head_losses(out, y)
    assert set(losses) == {"category", "difficulty", "skills", "flags", "checklist", "out_tokens"}
    assert all(v.ndim == 0 and torch.isfinite(v) for v in losses.values())
    sum(losses.values()).backward()
    assert all(v.grad is not None for v in out.values())


def test_head_losses_row_weights():
    out, y = _fake_out(4, requires_grad=False), _fake_y(4)
    base = head_losses(out, y)
    y["w"] = torch.ones(4)
    assert all(torch.allclose(base[k], v) for k, v in head_losses(out, y).items())
    y["w"] = torch.tensor([1.0, 1.0, 0.0, 0.0])
    sub = head_losses({k: v[:2] for k, v in out.items()}, {k: v[:2] for k, v in y.items()})
    assert all(torch.allclose(sub[k], v, atol=1e-6) for k, v in head_losses(out, y).items())


def test_anchor_loss_masks_missing_rows():
    from panda_router.model.losses import anchor_loss

    out = _fake_out(3, requires_grad=False)
    assert anchor_loss(out, torch.full((3,), float("nan"))) is None
    out["difficulty"] = torch.tensor([[-9.0] * 9] * 3)  # expected level ~1
    loss = anchor_loss(out, torch.tensor([1.0, float("nan"), float("nan")]))
    assert float(loss) < 1e-3


def test_encode_labels_weight_and_anchor(fake_dir):
    from panda_router.train.data import encode_labels, load_jsonl

    ex = load_jsonl(fake_dir / "train.jsonl")[0]
    ex["meta"] = {**(ex.get("meta") or {}), "single_teacher": True}
    lab = encode_labels(ex, 0.5, 4.2)
    assert lab["w"] == np.float32(0.5) and lab["anchor"] == np.float32(4.2)
    assert np.isnan(encode_labels({**ex, "meta": {}})["anchor"]) and encode_labels({**ex, "meta": {}})["w"] == 1.0


def test_pair_loss_direction():
    out = _fake_out(2, requires_grad=False)
    out["difficulty"] = torch.tensor([[5.0] * 9, [-5.0] * 9])  # row0 hard, row1 easy
    assert float(pair_loss(out, [(0, 1, {"difficulty": "+"})])) == 0.0
    assert float(pair_loss(out, [(1, 0, {"difficulty": "+"})])) > 1.0
    assert parse_delta("flags.long_context", 1) == 1 and parse_delta("difficulty", "-") == -1
    assert pair_loss(out, [(0, 1, {"unknown.key": "+"})]) is None


# ---------------------------------------------------------------- soft matcher
def np_p_success(diff, skills, theta, se, a, lam=0.5, n_quad=20):
    """Direct numpy transcription of the CONTRACTS.md formula (loops): z = theta_eff - pen ~ N(mu, sd)
    with delta-method sd, Gauss-Hermite over z, exact sum over difficulty levels."""
    x, wx = np.polynomial.hermite.hermgauss(n_quad)
    e = np.array([sum(l * p for l, p in enumerate(s)) for s in skills])
    w = e / e.sum() if e.sum() > 1e-6 else np.eye(len(e))[SKILL_AXES.index("reasoning")]
    out = []
    for m in range(theta.shape[0]):
        gap = e - theta[m]
        mu = float(np.dot(w, theta[m])) - lam * float(np.dot(w, np.maximum(0.0, gap)))
        sd = math.sqrt(sum((w[k] * (1 + lam * (gap[k] > 0)) * se[m, k]) ** 2 for k in range(len(w))))
        total = 0.0
        for xq, wgt in zip(x, wx):
            z = mu + sd * math.sqrt(2) * xq
            for lvl in range(1, 11):
                total += wgt / math.sqrt(math.pi) * diff[lvl - 1] / (1 + math.exp(-a[m] * (z - lvl)))
        out.append(total)
    return np.array(out)


def test_soft_matcher_matches_numpy_reference():
    g = torch.Generator().manual_seed(1)
    pool = sample_pools(3, 4, g)
    y = _fake_y(3)
    y["skills"][2] = 0.0
    y["skills"][2, :, 0] = 1.0  # all skills ~0 -> reasoning fallback
    p = p_success(y["difficulty"].double(), y["skills"].double(), pool.theta.double(), pool.se.double(), pool.a.double())
    for b in range(3):
        ref = np_p_success(y["difficulty"][b].numpy(), y["skills"][b].numpy(), pool.theta[b].numpy(),
                           pool.se[b].numpy(), pool.a[b].numpy())
        assert np.allclose(p[b].numpy(), ref, atol=1e-9), (p[b], ref)
    try:
        from panda_router.matcher.core import success_probabilities
    except ImportError:
        return
    skills = {ax: y["skills"][0, k].tolist() for k, ax in enumerate(SKILL_AXES)}
    ref, _, _ = success_probabilities(skills, y["difficulty"][0].numpy(), pool.theta[0].numpy(),
                                      pool.se[0].numpy(), pool.a[0].numpy())
    assert np.allclose(p[0].numpy(), ref, atol=1e-6)


def test_soft_matcher_gradients_flow_and_regret_nonnegative():
    out, y = _fake_out(5), _fake_y(5)
    pool = sample_pools(5, 6, torch.Generator().manual_seed(2))
    pred = {"difficulty": corn_level_probs(out["difficulty"]), "skills": corn_level_probs(out["skills"]),
            "out_p50": out["out_tokens"][:, 1]}
    lab = {"difficulty": y["difficulty"], "skills": y["skills"], "out_p50": y["out_tokens"]}
    r = regret_loss(pred, lab, y["in_tokens"], pool, reduce=False)
    assert (r >= -1e-6).all()
    r.mean().backward()
    for k in ("difficulty", "skills", "out_tokens"):
        assert out[k].grad is not None and out[k].grad.abs().sum() > 0, k


def test_regret_zero_when_prediction_equals_label():
    y = _fake_y(4)
    pool = sample_pools(4, 5, torch.Generator().manual_seed(3))
    lab = {"difficulty": y["difficulty"], "skills": y["skills"], "out_p50": y["out_tokens"]}
    r = regret_loss(lab, lab, y["in_tokens"], pool, tau=1e-4, reduce=False)
    assert torch.allclose(r, torch.zeros(4), atol=1e-5)


def test_harder_task_lowers_p_success():
    y = _fake_y(2)
    y["difficulty"] = torch.zeros(2, 10)
    y["difficulty"][0, 1], y["difficulty"][1, 8] = 1, 1
    y["skills"][1] = y["skills"][0]
    pool = sample_pools(1, 3, torch.Generator().manual_seed(4))
    pool = CardPool(*(getattr(pool, f).expand(2, *getattr(pool, f).shape[1:]) for f in pool.__dataclass_fields__))
    p = p_success(y["difficulty"], y["skills"], pool.theta, pool.se, pool.a)
    assert (p[0] > p[1]).all()


# ---------------------------------------------------------------- data + end-to-end
@pytest.fixture(scope="module")
def tiny_backbone(tmp_path_factory):
    from transformers import AutoTokenizer, ModernBertConfig, ModernBertModel

    tok = AutoTokenizer.from_pretrained(TOKENIZER)
    d = tmp_path_factory.mktemp("tiny_backbone")
    cfg = ModernBertConfig(vocab_size=len(tok), hidden_size=32, intermediate_size=64, num_hidden_layers=2,
                           num_attention_heads=2, global_attn_every_n_layers=1, local_attention=16,
                           pad_token_id=tok.pad_token_id, bos_token_id=tok.cls_token_id,
                           eos_token_id=tok.sep_token_id, cls_token_id=tok.cls_token_id, sep_token_id=tok.sep_token_id)
    torch.manual_seed(0)
    ModernBertModel(cfg).save_pretrained(d)
    tok.save_pretrained(d)
    return d


@pytest.fixture(scope="module")
def fake_dir(tmp_path_factory):
    from panda_router.train.fake_data import generate

    return generate(tmp_path_factory.mktemp("fake"), n=48, seed=0)


def test_fake_data_contract_and_pair_sampler(fake_dir, tiny_backbone):
    from transformers import AutoTokenizer

    from panda_router.train.data import PairAwareBatchSampler, ProfileDataset, load_jsonl
    from panda_router.train.fake_data import validate_example

    rows = load_jsonl(fake_dir / "train.jsonl")
    for r in rows:
        validate_example(r)
    ds = ProfileDataset(rows, AutoTokenizer.from_pretrained(tiny_backbone))
    assert ds.pairs, "fixture should contain minimal pairs"
    sampler = PairAwareBatchSampler(ds, 8, seed=0)
    batches = sampler.batches()
    assert sorted(i for b in batches for i in b) == list(range(len(ds)))
    where = {i: k for k, b in enumerate(batches) for i in b}
    assert all(where[i] == where[j] for i, (j, _) in ds.pairs.items())
    b = ds.collate(batches[0])
    assert b["input_ids"].shape[1] in (64, 128, 256, 512)


def test_rotary_runs_fp32_under_autocast(tiny_backbone):
    from panda_router.model.net import ProfilerModel

    model = ProfilerModel.from_backbone(str(tiny_backbone))
    rot = [m for m in model.backbone.modules() if type(m).__name__.endswith("RotaryEmbedding")]
    assert rot and all(getattr(m, "_fp32_patched", False) for m in rot)
    x, pos = torch.zeros(1, 4, 8), torch.arange(300, 304)[None]
    with torch.autocast(device_type="cpu", dtype=torch.bfloat16):
        cos_ac = rot[0](x, pos)[0]
    assert torch.allclose(cos_ac, rot[0](x, pos)[0])


def test_train_export_onnx_profiler_end_to_end(fake_dir, tiny_backbone, tmp_path):
    from panda_router.model.onnx_profiler import OnnxProfiler, TorchProfiler, bench_latency
    from panda_router.train.export import export_artifacts
    from panda_router.train.trainer import TrainConfig, train

    cfg = TrainConfig(backbone=str(tiny_backbone), data_dir=str(fake_dir), out=str(tmp_path / "run"), epochs=1,
                      batch_size=8, device="cpu", bf16=False, max_steps=3, regret_weight=0.1, pair_weight=0.5)
    summary = train(cfg)
    assert {"pair", "regret"} & set(summary["history"][0]["train"])
    ckpt = tmp_path / "run" / "best"
    heads = json.loads((ckpt / "heads.json").read_text())
    assert len(heads["temperatures"]["skills"]) == len(SKILL_AXES)

    from panda_router.train.export import exclusion_stages

    metrics = export_artifacts(ckpt, tmp_path / "art", fake_dir)
    assert metrics["torch_vs_onnx_max_abs"] < 1e-3
    stages = exclusion_stages(tmp_path / "art" / "model.onnx", 2)
    assert stages[0] == [] and len(stages[1]) == 6 and len(stages[2]) > 6
    for f in ("model.onnx", "model.int8.onnx", "tokenizer.json", "heads.json", "metrics.json"):
        assert (tmp_path / "art" / f).exists(), f

    task = {"text": "Fix the flaky retry logic in the payment webhook.",
            "context": {"repo_languages": ["python"], "files_in_scope": 3, "requires_tools": True}}
    for quantized in (True, False):
        prof = OnnxProfiler(tmp_path / "art", quantized=quantized).profile(task)
        assert isinstance(prof, TaskProfile)
        TaskProfile.from_dict(prof.to_dict())
        assert abs(sum(prof.category.values()) - 1) < 1e-5 and set(prof.category) == set(CATEGORIES)
        assert abs(sum(prof.difficulty) - 1) < 1e-5
        assert all(abs(sum(v) - 1) < 1e-5 for v in prof.skills.values())
        assert set(prof.flags) == set(FLAGS) and set(prof.checklist) == set(CHECKLIST_IDS)
        q = prof.out_tokens_log10
        assert q["p10"] <= q["p50"] <= q["p90"]
    tp = TorchProfiler(ckpt).profile(task)
    op = OnnxProfiler(tmp_path / "art", quantized=False).profile(task)
    assert np.allclose(tp.difficulty, op.difficulty, atol=1e-4)
    from panda_router.serve.router import profiler_name

    assert profiler_name(OnnxProfiler(tmp_path / "art")) == "OnnxProfiler(art/model.int8.onnx)"
    lat = bench_latency(OnnxProfiler(tmp_path / "art"), [task], n=5, warmup=1)
    assert lat["p50_ms"] > 0
