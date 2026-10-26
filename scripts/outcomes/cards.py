"""Propose (and with --apply, write) outcome-fitted coding/debugging thetas for cards.

Evidence per card, from data/outcomes/systems.jsonl (router-scale thetas):
- exact: a common-scaffold system whose base model is the card's model (scale.EXACT). Fine-tunes and
  vendor agent products (Claude Code, Codex, Junie, Cursor) are not used; they measure scaffold effects.
- lower bound: a predecessor (scale.PREDECESSOR, or a card listed in another card's `supersedes`) fitted
  above the card. A successor is assumed at least as strong as its predecessor.
se = hypot(fit+link se, scaffold sd), scaffold sd = median within-model sd across scaffolds in component A.

Apply rules: exact evidence with >= 100 tasks -> coding theta := fit, every axis shifted by the same
delta, coding/debugging se := fitted se. field_provenance.skills := 'verified' only for API-served exact
models (local Ollama cards run a Q4 quant of the fitted weights: delta applied only if |delta| >= 0.15,
provenance kept). Lower-bound evidence is applied only when the violation exceeds its se.
Usage: .venv/bin/python scripts/outcomes/cards.py [--apply]
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from panda_router.outcomes.scale import EXACT, PREDECESSOR  # noqa: E402

OUT = ROOT / "data" / "outcomes"
CARDS = ROOT / "cards"
NOT_BASE = ("entropo", "swerl", "skywork", "frog", "deepswe", "mcts")
SOURCES = {"A": "https://github.com/swe-bench/experiments (per-instance resolved lists; IRT fit in data/outcomes)",
           "B": "https://huggingface.co/datasets/ibragim-bad/swe_rebench_07_2026_trajectories (resolved flags "
                "only; IRT fit in data/outcomes)"}


def load_cards() -> dict:
    return {p.stem: json.loads(p.read_text()) for p in sorted(CARDS.glob("*.json"))}


def scaffold_sd(sysdf: pd.DataFrame) -> float:
    a = sysdf[(sysdf.component == "A") & (sysdf.base_model != "")]
    sds = a.groupby("base_model").theta_router.agg(["std", "count"])
    return float(sds[sds["count"] >= 3]["std"].median())


def evidence(sysdf: pd.DataFrame, components: tuple[str, ...], sd: float, n_items: dict) -> dict:
    """card id -> {'exact': (theta, se, systems, component)} and/or {'lower': [(theta, se, system), ...]}."""
    use = sysdf[sysdf.component.isin(components) & (sysdf.kind != "agentic_system")
                & ~sysdf.system.str.lower().str.contains("|".join(NOT_BASE))]
    ev: dict = {}
    # newest component wins for exact evidence (B is 2026-07; A spans 2023-2026)
    for comp in sorted(components):
        for model, g in use[use.component == comp].groupby("base_model"):
            se = float(np.hypot(g.se_router.median(), sd))
            th = float(g.theta_router.median())
            if model in EXACT and n_items[comp] >= 100:
                ev.setdefault(EXACT[model], {})["exact"] = (th, se, g.system.tolist(), comp)
            if model in PREDECESSOR:
                ev.setdefault(PREDECESSOR[model], {}).setdefault("lower", []).append((th, se, g.system.iloc[0]))
    cards = load_cards()
    for cid, c in cards.items():  # supersedes: newer card >= fitted older card
        for old in c.get("supersedes") or []:
            if "exact" in ev.get(old, {}):
                th, se, systems, _ = ev[old]["exact"]
                ev.setdefault(cid, {}).setdefault("lower", []).append((th, se, systems[0]))
    return ev


def proposals(ev: dict, cards: dict) -> list[dict]:
    rows = []
    for cid, e in sorted(ev.items()):
        cur = cards[cid]["skills"]["coding"]["theta"]
        row = {"card": cid, "current": cur, "provenance": cards[cid]["field_provenance"].get("skills")}
        if "exact" in e:
            th, se, systems, comp = e["exact"]
            local = bool(cards[cid].get("local"))
            delta = round(th - cur, 1)
            row.update(kind="exact", fitted=round(th, 2), se=round(se, 2), delta=delta, component=comp,
                       systems=systems, apply=(abs(delta) >= 0.15) if local else True,
                       verify=not local)
        else:
            th, se, sysname = max(e["lower"])
            viol = th - cur
            row.update(kind="lower_bound", fitted=round(th, 2), se=round(se, 2), systems=[sysname],
                       delta=round(max(viol, 0.0), 1), apply=viol > se, verify=False)
        rows.append(row)
    return rows


def apply(rows: list[dict], cards: dict, sources: dict):
    for r in rows:
        if not r["apply"] or (r["delta"] == 0 and not r["verify"]):
            continue
        p = CARDS / f"{r['card']}.json"
        c = json.loads(p.read_text())  # re-read: other workers may have edited cards meanwhile
        d = r["delta"]
        skills = {k: {**v, "theta": round(min(10.0, max(0.0, v["theta"] + d)), 2)} for k, v in c["skills"].items()}
        if r["kind"] == "exact":
            for k in ("coding", "debugging"):
                if k in skills:
                    skills[k] = {**skills[k], "se": max(r["se"], 0.3)}
        fp = dict(c["field_provenance"])
        if r["verify"]:
            fp["skills"] = "verified"
        prov = "verified" if r["verify"] else c["provenance"]
        src = sources[r["component"]] if r["kind"] == "exact" else "data/outcomes/REPORT.md (predecessor lower bound)"
        note = (f" Outcome calibration 2026-10-26: coding fitted {r['fitted']} +/- {r['se']} on the router scale "
                f"from {', '.join(r['systems'])} ({'exact model' if r['kind'] == 'exact' else 'predecessor lower bound'}"
                f"{'; Q4 local quant not measured, fitted on full-precision runs' if c.get('local') else ''}); "
                f"all axes shifted by {d:+.1f}. See data/outcomes/REPORT.md.")
        new = {**c, "skills": skills, "field_provenance": fp, "provenance": prov,
               "sources": [*c.get("sources", []), *([src] if src not in c.get("sources", []) else [])],
               "notes": (c.get("notes") or "").rstrip() + note, "card_version": "2026-10-26"}
        p.write_text(json.dumps(new, indent=2, ensure_ascii=False) + "\n")
        print("updated", r["card"], f"{d:+.1f}", "verified" if r["verify"] else "")


def main():
    sysdf = pd.read_json(OUT / "systems.jsonl", lines=True).fillna({"base_model": ""})
    fit = json.loads((OUT / "fit.json").read_text())
    n_items = {k: v["n_items"] for k, v in fit["components"].items()}
    sd = scaffold_sd(sysdf)
    cards = load_cards()
    res = {"scaffold_sd": sd}
    for name, comps in (("without_rebench07", ("A",)), ("with_rebench07", ("A", "B"))):
        res[name] = proposals(evidence(sysdf, comps, sd, n_items), cards)
    (OUT / "card_deltas.json").write_text(json.dumps(res, indent=1))
    for r in res["with_rebench07"]:
        print({k: r[k] for k in ("card", "kind", "current", "fitted", "se", "delta", "apply", "verify")})
    if "--apply" in sys.argv:
        apply(res["with_rebench07"], cards, SOURCES)


if __name__ == "__main__":
    main()
