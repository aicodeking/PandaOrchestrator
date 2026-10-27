"""Build REPORT.md tables from eval JSONs. .venv/bin/python eval_reports/v4_profiler/make_report.py"""
import json
from pathlib import Path

R = Path("eval_reports/v4_profiler")
V3 = Path("eval_reports/v3")
CANDS = ["t150m_s32m_soup", "t400m_s32m_soup", "t150m_s68m_seed0", "t400m_s68m_seed0"]


def j(p):
    p = Path(p)
    return json.loads(p.read_text()) if p.exists() else {}


def row(name, art, gold, test, outc, att, bench):
    m = j(f"{art}/metrics.json")
    g, t = gold.get("profiler_metrics", {}), test.get("profiler_metrics", {})
    gd, td = g.get("difficulty", {}), t.get("difficulty", {})
    pol = att.get("routing", {}).get("policies", {}).get("max_utility", {})
    size = Path(f"{art}/model.int8.onnx").stat().st_size / 1e6
    lat = bench.get("int8", {}).get("p50_ms")
    f = lambda x, n=3: "n/a" if x is None else f"{x:.{n}f}"
    return [name, f(m.get("int8", {}).get("val_score"), 2), f"{size:.0f}", f(lat, 1),
            f(g.get("category", {}).get("acc")), f(gd.get("spearman")), f(gd.get("pred_mean", 0) - gd.get("label_mean", 0), 2),
            f(td.get("spearman")), f(td.get("pred_mean", 0) - td.get("label_mean", 0), 2),
            f(outc.get("heldout_issue", {}).get("spearman")), f(att.get("attempt_irt", {}).get("spearman")),
            f(pol.get("success_per_100"), 1), f(pol.get("cost_per_100_usd"))]


H = ["candidate", "val int8", "MB", "p50 ms", "gold cat acc", "gold diff rho", "gold diff bias", "test diff rho",
     "test diff bias", "outcome rho", "attempt rho", "max_util succ/100", "cost/100 $"]
rows = [row("v3 (baseline)", "artifacts/panda-router-v3", j(V3 / "v3_gold.json"), j(V3 / "v3_test.json"),
            j(V3 / "outcome_v3.json"), j(V3 / "attempt_v3_caloff.json"), j(R / "bench_v3.json"))]
for c in CANDS:
    rows.append(row(c, f"artifacts/v4_candidates/{c}", j(R / f"{c}_gold.json"), j(R / f"{c}_test.json"),
                    j(R / f"outcome_{c}.json"), j(R / f"attempt_{c}.json"), j(f"artifacts/v4_candidates/{c}/metrics.json").get("cpu_latency_batch1", {})))
cost = [json.loads(x) for x in Path("checkpoints/v4/cost_log.jsonl").read_text().splitlines() if x.strip()]
out = ["| " + " | ".join(H) + " |", "|" + "---|" * len(H)] + ["| " + " | ".join(r) + " |" for r in rows]
out += ["", f"Modal total: ${cost[-1]['total_usd']:.2f} over {len(cost)} jobs (cap $15)."]
(R / "tables.md").write_text("\n".join(out))
print("\n".join(out))
