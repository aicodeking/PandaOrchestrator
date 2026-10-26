import math
import random

import numpy as np
import pytest

from panda_router.eval import metrics as M
from panda_router.eval.anchors import fit_1pl, to_1_10
from panda_router.eval.baselines import average_labels, label_profile
from panda_router.eval.gold import is_gold, scrub
from panda_router.eval.validate import validate_example
from panda_router.taxonomy import CATEGORIES, CHECKLIST_IDS, FLAGS, SKILL_AXES


def _gauss(center, lo, hi, sigma=0.6):
    w = [math.exp(-0.5 * ((k - center) / sigma) ** 2) for k in range(lo, hi + 1)]
    s = sum(w)
    return [x / s for x in w]


def make_labels(rng: random.Random) -> dict:
    c1, c2 = rng.sample(CATEGORIES, 2)
    return {
        "category": {c1: 0.75, c2: 0.25},
        "difficulty": _gauss(rng.randint(1, 10), 1, 10),
        "skills": {ax: _gauss(rng.randint(0, 10), 0, 10) for ax in SKILL_AXES},
        "flags": {f: float(rng.random() < 0.4) for f in FLAGS},
        "checklist": {c: float(rng.random() < 0.4) for c in CHECKLIST_IDS},
        "out_tokens_log10": rng.uniform(1.5, 4.5),
    }


@pytest.fixture(scope="module")
def labels():
    rng = random.Random(0)
    return [make_labels(rng) for _ in range(60)]


def test_perfect_predictions(labels):
    preds = [label_profile(l).to_dict() for l in labels]
    m = M.profiler_metrics(labels, preds)
    assert m["category"]["acc"] == 1.0 and m["category"]["top2"] == 1.0
    assert m["difficulty"]["mae"] == 0.0 and m["difficulty"]["spearman"] == pytest.approx(1.0)
    assert m["difficulty"]["qwk"] == pytest.approx(1.0)
    assert m["skills"]["mae_mean"] == 0.0
    assert m["flags"]["f1_macro"] == 1.0 and m["flags"]["auroc_macro"] == 1.0
    assert m["checklist"]["f1_macro"] == 1.0 and m["checklist"]["f1_micro"] == 1.0
    assert m["out_tokens"]["mae_log10"] == 0.0
    assert m["flags"]["ece_macro"] == 0.0  # hard 0/1 targets predicted exactly


def test_metric_primitives():
    assert M.f1_binary([1, 1, 0, 0], [1, 0, 1, 0]) == pytest.approx(0.5)
    assert M.f1_binary([0, 0], [0, 0]) is None
    assert M.auroc([0, 0, 1, 1], [0.1, 0.4, 0.35, 0.8]) == pytest.approx(0.75)
    assert M.auroc([1, 1], [0.2, 0.3]) is None
    # All predictions at confidence 0.8, 50% correct -> ECE 0.3.
    assert M.ece([0.8] * 4, [1, 0, 1, 0]) == pytest.approx(0.3)
    assert M.qwk([1, 2, 3], [1, 2, 3]) == pytest.approx(1.0)
    assert M.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert M.expected([0, 1, 0], np.array([1.0, 2.0, 3.0])) == 2.0


def test_wrong_predictions_are_penalised(labels):
    rng = random.Random(1)
    shuffled = labels[:]
    rng.shuffle(shuffled)
    preds = [label_profile(l).to_dict() for l in shuffled]
    m = M.profiler_metrics(labels, preds)
    assert m["category"]["acc"] < 0.5
    assert m["difficulty"]["mae"] > 1.0
    assert m["flags"]["f1_macro"] < 0.8


def test_anchor_spearman(labels):
    preds = [label_profile(l).to_dict() for l in labels]
    anchors = [M.expected(l["difficulty"], M.DIFF_LEVELS) if i % 2 else None for i, l in enumerate(labels)]
    d = M.profiler_metrics(labels, preds, anchors)["difficulty"]
    assert d["anchor_n"] == 30 and d["spearman_pred_vs_anchor"] == pytest.approx(1.0)


def test_validate_and_average(labels):
    ex = {"id": "gold-x", "source": "wildchat", "pair_of": None, "task": {"text": "hi", "context": {}},
          "labels": labels[0], "meta": {}}
    assert validate_example(ex) == []
    avg = average_labels(labels[:10])
    assert validate_example({**ex, "labels": avg}) == []
    bad = {**ex, "labels": {**labels[0], "difficulty": [0.5] * 10}}
    assert validate_example(bad)


def test_gold_partition_rule_and_scrub():
    import hashlib

    ids = [f"owner__repo-{i}" for i in range(500)]
    gold = [i for i in ids if is_gold(i)]
    assert all(int(hashlib.sha1(i.encode()).hexdigest(), 16) % 10 == 0 for i in gold)
    assert 20 < len(gold) < 80
    s = scrub("see C:/Users/alice/Desktop/x.py and mail bob@example.com", aggressive=True)
    assert "alice" not in s and "bob@example.com" not in s


def test_fit_1pl_recovers_order():
    rng = np.random.default_rng(0)
    n_inst, n_models = 200, 4
    b_true = rng.normal(0, 1.5, n_inst)
    th_true = np.array([-1.0, 0.0, 1.0, 2.0])
    inst, model, k, n = [], [], [], []
    for i in range(n_inst):
        for m in range(n_models):
            p = 1 / (1 + np.exp(-(th_true[m] - b_true[i])))
            inst.append(i), model.append(m), n.append(10), k.append(rng.binomial(10, p))
    b, th, se = fit_1pl(np.array(inst), np.array(model), np.array(k), np.array(n), n_inst, n_models)
    assert M.spearman(b, b_true) > 0.85
    assert list(np.argsort(th)) == [0, 1, 2, 3]
    d = to_1_10(b, b)
    assert d.min() >= 1 and d.max() <= 10


def _tasks(labels):
    return [{"text": f"task {i}", "context": {"requires_tools": i % 3 == 0, "estimated_input_tokens": 2000 + 100 * i}}
            for i in range(len(labels))]


@pytest.mark.parametrize("cards", ["synthetic", "repo"])
def test_routing_regret_zero_when_pred_equals_oracle(labels, tmp_path, cards):
    pytest.importorskip("panda_router.matcher")
    from panda_router.eval.routing import CARDS_DIR, RoutingEvaluator

    if cards == "repo" and not any(CARDS_DIR.glob("*.json")):
        pytest.skip("no cards/ directory")
    cards_dir = tmp_path if cards == "synthetic" else None  # empty dir -> synthetic cards
    ev = RoutingEvaluator(cards_dir=cards_dir, n_pools=20, pools_per_task=5, seed=3)
    assert (ev.card_source == "synthetic") == (cards == "synthetic")
    sub = labels[:15]
    oracle = [label_profile(l) for l in sub]
    rng = random.Random(5)
    other = [label_profile(l) for l in rng.sample(labels, len(sub))]
    res = ev.evaluate(_tasks(sub), oracle, {"same": [label_profile(l) for l in sub], "other": other})
    for mode, v in res["metrics"]["same"].items():
        assert v["n"] > 0
        assert v["pick_agreement"] == 1.0, mode
        assert v["utility_regret"] == pytest.approx(0.0, abs=1e-12), mode
        assert v["cost_ratio"] == pytest.approx(1.0), mode
        assert v["infeasible_rate"] == 0.0
    assert res["metrics"]["other"]["all"]["pick_agreement"] < 1.0
    assert set(res["metrics"]) == {"same", "other", "always_strongest", "always_cheapest"}


def test_run_eval_with_stub_profiler(labels, tmp_path):
    pytest.importorskip("panda_router.matcher")
    import json

    from panda_router.eval.runner import markdown_summary, run_eval
    from panda_router.profile import Profiler

    rows = [{"id": f"g{i}", "source": "wildchat" if i % 2 else "swe-rebench", "pair_of": None, "task": t, "labels": l, "meta": {}}
            for i, (t, l) in enumerate(zip(_tasks(labels[:12]), labels[:12]))]
    p = tmp_path / "gold.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows))
    by_text = {r["task"]["text"]: r["labels"] for r in rows}

    class Oracle(Profiler):
        def profile(self, task):
            return label_profile(by_text[task["text"]])

    rep = run_eval("stub", "test", str(p), n_pools=10, pools_per_task=3, cards_dir=str(tmp_path / "nocards"), profiler=Oracle())
    assert rep["profiler_metrics"]["category"]["acc"] == 1.0
    assert rep["routing"]["metrics"]["predicted"]["all"]["utility_regret"] == pytest.approx(0.0, abs=1e-12)
    assert "Routing" in markdown_summary(rep)


def test_gold_hygiene_drops_train_duplicates_and_flags_repo(tmp_path):
    import json

    from panda_router.eval.gold import hygiene

    def row(i, text, source, repo=None):
        return {"id": i, "source": source, "task": {"text": text}, "meta": {"repo": repo}}

    (tmp_path / "train.jsonl").write_text(json.dumps(row("t1", "Fix   the BUG!", "wildchat")) + "\n"
                                          + json.dumps(row("t2", "issue", "swe-rebench", "a/b")) + "\n")
    for s in ("val", "test"):
        (tmp_path / f"{s}.jsonl").write_text("")
    kept, dropped = hygiene([row("g1", "fix the bug", "wildchat"), row("g2", "other", "swe-rebench", "a/b"),
                             row("g3", "other2", "swe-smith", "c/d")], tmp_path)
    assert dropped == ["g1"]
    assert [r["meta"].get("repo_in_train") for r in kept] == [True, False]
