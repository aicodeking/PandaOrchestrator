import json
import math

import pytest

from panda_router.datagen import label, merge, pairwise, validate
from panda_router.datagen.common import is_gold_reserved, norm_context, sha_int
from panda_router.datagen.dedup_split import assign_splits, dedup
from panda_router.datagen.jsonio import extract_json
from panda_router.datagen.real import scrub_pii
from panda_router.taxonomy import CATEGORIES, CHECKLIST_IDS, FLAGS, SKILL_AXES


def _ans(cat="bugfix", diff=5, cat2=None, skill=4, bit=0, out=1000):
    return {"cat": cat, "cat2": cat2, "diff": diff, "skills": {ax: skill for ax in SKILL_AXES},
            "flags": {f: bit for f in FLAGS}, "check": {c: bit for c in CHECKLIST_IDS}, "out_tokens": out}


def _record(**kw):
    r = {"id": "syn-000001", "source": "synthetic", "pair_of": None,
         "task": {"text": "fix the bug", "context": {"repo_languages": ["python"], "files_in_scope": 1}},
         "labels": merge.merge([_ans(), _ans(diff=6, bit=1)]), "meta": {"teachers": ["codex", "kimi"], "agreement": 0.9}}
    r.update(kw)
    return r


# --- smoothing -----------------------------------------------------------------------------

def test_gaussian_dist_normalised_and_peaked():
    d = merge.gaussian_dist(5, 1, 10)
    assert len(d) == 10 and math.isclose(sum(d), 1, abs_tol=1e-9)
    assert max(range(10), key=lambda i: d[i]) == 4
    assert math.isclose(d[3], d[5])  # symmetric
    assert d[4] > 0.5  # sigma=0.6 is light smoothing


def test_smooth_points_at_edges_and_between():
    d = merge.smooth_points([0], 0, 10)
    assert math.isclose(sum(d), 1) and d[0] > 0.7
    d = merge.smooth_points([4, 6], 0, 10)
    assert math.isclose(d[4], d[6]) and d[4] > d[5]  # disagreement stays bimodal
    d = merge.smooth_points([5.5], 1, 10)
    assert math.isclose(d[4], d[5])


# --- merge ---------------------------------------------------------------------------------

def test_merge_soft_labels():
    a = _ans(cat="implementation", cat2="refactor", diff=4, bit=1, out=1000)
    b = _ans(cat="implementation", diff=6, bit=0, out=100)
    L = merge.merge([a, b])
    assert math.isclose(sum(L["category"].values()), 1)
    assert math.isclose(L["category"]["implementation"], 0.875)
    assert math.isclose(L["category"]["refactor"], 0.125)
    assert len(L["difficulty"]) == 10 and math.isclose(sum(L["difficulty"]), 1, abs_tol=1e-5)
    exp = sum((i + 1) * p for i, p in enumerate(L["difficulty"]))
    assert math.isclose(exp, 5, abs_tol=1e-3)
    assert set(L["skills"]) == set(SKILL_AXES) and all(len(v) == 11 for v in L["skills"].values())
    assert all(v == 0.5 for v in L["flags"].values()) and set(L["flags"]) == set(FLAGS)
    assert set(L["checklist"]) == set(CHECKLIST_IDS)
    assert math.isclose(L["out_tokens_log10"], 2.5)


def test_merge_override_and_empty():
    o = [0.1] * 10
    assert merge.merge([_ans()], o)["difficulty"] == o
    with pytest.raises(ValueError):
        merge.merge([])


def test_merge_with_partial_tiebreak():
    a, b = _ans(cat="bugfix", diff=2), _ans(cat="refactor", diff=8)
    L = merge.merge([a, b], tiebreak=[{"cat": "bugfix", "cat2": None, "diff": 3}])
    assert math.isclose(L["category"]["bugfix"], 2 / 3, abs_tol=1e-5)
    exp = sum((i + 1) * p for i, p in enumerate(L["difficulty"]))
    assert math.isclose(exp, 13 / 3, abs_tol=1e-2)
    assert L["flags"] == merge.merge([a, b])["flags"]  # tie-break never touches other fields


def test_answers_for_uses_any_two_full_teachers_and_ollama_only_on_dispute():
    from panda_router.datagen.pipeline import answers_for

    ans = {"codex": {"x": _ans(diff=2), "y": _ans(diff=4)}, "kimi": {}, "grok": {"x": _ans(diff=7), "y": _ans(diff=5)},
           "ollama": {"x": {"cat": "bugfix", "cat2": None, "diff": 3}, "y": {"cat": "bugfix", "cat2": None, "diff": 9}}}
    names, full, extra = answers_for("x", ans)
    assert names == ["codex", "grok", "ollama"] and len(full) == 2 and len(extra) == 1
    names, full, extra = answers_for("y", ans)
    assert names == ["codex", "grok"] and extra == []
    assert answers_for("z", ans)[1] == []


def test_agreement_bounds():
    assert merge.agreement([_ans(), _ans()]) == 1.0
    lo = merge.agreement([_ans(cat="bugfix", diff=1, skill=0, bit=0), _ans(cat="research", diff=10, skill=10, bit=1)])
    assert lo == 0.0
    assert 0 < merge.agreement([_ans(diff=3), _ans(diff=5)]) < 1


# --- teacher answer cleaning ---------------------------------------------------------------

def test_clean_answer_coerces_and_rejects():
    raw = {"cat": "bugfix", "cat2": "bugfix", "diff": "7", "skills": {"coding": 12, "debugging": "6"},
           "flags": {"needs_tools": "yes"}, "check": {c: 1 for c in CHECKLIST_IDS}, "out_tokens": "2500"}
    a = label.clean_answer(raw)
    assert a["cat2"] is None and a["diff"] == 7 and a["skills"]["coding"] == 10 and a["skills"]["math"] == 0
    assert a["flags"]["needs_tools"] == 1 and a["flags"]["needs_web"] == 0
    with pytest.raises(ValueError):
        label.clean_answer({**raw, "cat": "cooking"})
    with pytest.raises(ValueError):
        label.clean_answer({**raw, "diff": 11})
    with pytest.raises(ValueError):
        label.clean_answer({**raw, "check": {}})


def test_strong_disagreement():
    assert label.strong_disagreement(_ans(diff=2), _ans(diff=5))
    assert label.strong_disagreement(_ans(cat="bugfix"), _ans(cat="refactor"))
    assert not label.strong_disagreement(_ans(diff=4), _ans(diff=6))


# --- JSON extraction -----------------------------------------------------------------------

def test_extract_json_variants():
    assert extract_json('{"a": 1}') == {"a": 1}
    assert extract_json('• ```json\n  {"a": [1, 2]}\n  ```\n') == {"a": [1, 2]}
    assert extract_json('Sure! Here you go:\n{"tasks": [{"text": "```py\\nx=1\\n```"}]}\nDone.') == {"tasks": [{"text": "```py\nx=1\n```"}]}
    assert extract_json('{"t": "line1\nline2"}') == {"t": "line1\nline2"}  # raw newline tolerated
    with pytest.raises(ValueError):
        extract_json("no json here")


# --- gold exclusion, context, PII ----------------------------------------------------------

def test_gold_rule():
    ids = [f"repo__x-{i}" for i in range(200)]
    reserved = [i for i in ids if is_gold_reserved(i)]
    assert all(sha_int(i) % 10 == 0 for i in reserved) and 5 <= len(reserved) <= 40


def test_norm_context():
    c = norm_context({"repo_languages": "Python", "files_in_scope": "3", "has_images": "false", "x": 1})
    assert c == {"repo_languages": ["python"], "files_in_scope": 3, "has_images": False}


def test_scrub_pii():
    s = scrub_pii("mail me at jane.doe@example.com key sk-abcdefghijklmnop1234 ip 10.0.0.1", aggressive=True)
    assert "jane.doe" not in s and "sk-abc" not in s and "10.0.0.1" not in s


# --- pairwise / BT -------------------------------------------------------------------------

def test_bt_recovers_order_and_calibration_is_monotone():
    true = {"a": 0, "b": 1, "c": 2, "d": 3}
    js = []
    for x in true:
        for y in true:
            if x != y:
                js += [{"a": x, "b": y, "harder": x if true[x] > true[y] else y}] * 3
    s = pairwise.fit_bt(js)
    assert sorted(s, key=s.get) == ["a", "b", "c", "d"]
    cal = pairwise.calibrate(s, {"a": 6, "b": 2, "c": 8, "d": 4}, {k: "bugfix" for k in s})
    assert [cal[k] for k in "abcd"] == [2, 4, 6, 8]
    assert pairwise.consistency(js)["order_consistency"] == 1.0


def test_sample_pairs_within_category():
    items = [{"id": f"x{i}", "category": "bugfix" if i < 10 else "research", "diff_mean": i % 10} for i in range(20)]
    cat = {it["id"]: it["category"] for it in items}
    pairs = pairwise.sample_pairs(items, 30)
    assert len(pairs) == 30 and len(set(pairs)) == 30
    assert all(cat[a] == cat[b] and a != b for a, b in pairs)


# --- dedup / split -------------------------------------------------------------------------

def test_dedup_and_split():
    import numpy as np

    emb = np.array([[1, 0], [0.999, 0.0447], [0, 1]], dtype=np.float32)
    emb /= np.linalg.norm(emb, axis=1, keepdims=True)
    recs = [{"id": "syn-1", "source": "synthetic"}, {"id": "reb-1", "source": "swe-rebench"}, {"id": "syn-2", "source": "synthetic"}]
    kept, dropped = dedup(recs, emb)
    assert kept == [1, 2] and dropped == [(0, 1)]  # real source kept over synthetic
    clusters = {f"t{i}": f"c{i // 10}" for i in range(1000)}
    sp = assign_splits(clusters)
    by_c = {}
    for t, s in sp.items():
        by_c.setdefault(clusters[t], set()).add(s)
    assert all(len(v) == 1 for v in by_c.values())
    frac = {s: sum(v == s for v in sp.values()) / 1000 for s in ("train", "val", "test")}
    assert 0.06 <= frac["val"] <= 0.09 and 0.06 <= frac["test"] <= 0.09


# --- validation ----------------------------------------------------------------------------

def test_validate_record_ok_and_errors():
    assert validate.validate_record(_record()) == []
    bad = _record()
    bad["labels"]["difficulty"] = [0.5] * 10
    assert any("difficulty" in e for e in validate.validate_record(bad))
    bad = _record()
    del bad["labels"]["skills"]["math"]
    assert validate.validate_record(bad)
    bad = _record()
    bad["labels"]["flags"].pop("needs_web")
    assert validate.validate_record(bad)
    bad = _record()
    bad["labels"]["category"] = {"cooking": 1.0}
    assert validate.validate_record(bad)
    assert validate.validate_record(_record(source="minimal-pair"))  # needs pair_of + meta.edit
    mp = _record(id="mp-1", source="minimal-pair", pair_of="syn-000001")
    mp["meta"].update(edit="add_screenshots", expected_delta={"flags.needs_vision": 1})
    assert validate.validate_record(mp) == []
    assert validate.validate_record(_record(pair_of="x"))


def test_validate_splits(tmp_path):
    orig = _record()
    mp = _record(id="mp-1", source="minimal-pair", pair_of="syn-000001")
    mp["meta"].update(edit="simplify", expected_delta={"difficulty": "-"})
    (tmp_path / "train.jsonl").write_text(json.dumps(orig) + "\n")
    (tmp_path / "val.jsonl").write_text(json.dumps(mp) + "\n")
    (tmp_path / "test.jsonl").write_text("")
    rep = validate.validate_splits(tmp_path)
    assert any("minimal pair" in e for e in rep["val"]["errors"])
    (tmp_path / "train.jsonl").write_text(json.dumps(orig) + "\n" + json.dumps(mp) + "\n")
    (tmp_path / "val.jsonl").write_text("")
    rep = validate.validate_splits(tmp_path)
    assert all(not v["errors"] for v in rep.values())


def test_categories_cover_taxonomy():
    assert set(label.CATEGORY_DEFS) == set(CATEGORIES) and set(label.FLAG_DEFS) == set(FLAGS)
