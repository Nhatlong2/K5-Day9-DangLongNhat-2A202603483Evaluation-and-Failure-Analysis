"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item
from lab9.graders import GRADERS


def _finite_number(value: object) -> bool:
    return isinstance(value, int) or (isinstance(value, float) and math.isfinite(value))


def _report_index(report: dict, side: str, graded: set[str]) -> tuple[dict, list[str]]:
    """Index a report by its trial keys and collect violations of the manifest."""
    manifest = report.get("manifest")
    rows = report.get("rows")
    metrics = report.get("metrics")
    if not isinstance(manifest, dict) or not isinstance(rows, list) or not isinstance(metrics, dict):
        return {}, [f"{side} report is missing its manifest, rows or metrics"]

    problems = []
    if report.get("evaluator_failures"):
        problems.append(f"{side} report has evaluator failures")
    missing_summary = sorted(metric for metric in graded if metrics.get(metric) is None)
    if missing_summary:
        problems.append(f"{side} summary is missing graded metrics: {', '.join(missing_summary)}")
    invalid_summary = sorted(metric for metric, value in metrics.items()
                             if value is not None and not _finite_number(value))
    if invalid_summary:
        problems.append(f"{side} summary has non-finite or invalid metrics: {', '.join(invalid_summary)}")

    indexed: dict[tuple[str, int], frozenset[str]] = {}
    invalid_grades = set()
    bad_rows = 0
    for row in rows:
        if not isinstance(row, dict):
            bad_rows += 1
            continue
        item_id, seed = row.get("item_id"), row.get("seed")
        slices = row.get("slices") or []
        if (not isinstance(item_id, str) or not item_id or type(seed) is not int
                or not isinstance(slices, list) or not all(isinstance(tag, str) for tag in slices)):
            bad_rows += 1
            continue
        key = item_id, seed
        if key in indexed:
            problems.append(f"{side} has duplicate trial {item_id}@{seed}")
        indexed[key] = frozenset(slices)
        invalid_grades.update(metric for metric in graded if not _finite_number(row.get(metric)))
    if bad_rows:
        problems.append(f"{side} has {bad_rows} invalid trial row(s)")
    if invalid_grades:
        problems.append(f"{side} rows have missing or invalid grades: {', '.join(sorted(invalid_grades))}")

    items, seeds = manifest.get("items"), manifest.get("seeds")
    if (type(items) is not int or items < 1 or not isinstance(seeds, list) or not seeds
            or any(type(seed) is not int for seed in seeds) or len(set(seeds)) != len(seeds)):
        problems.append(f"{side} manifest has an invalid item count or seed list")
    else:
        selected_items = {item_id for item_id, _ in indexed}
        expected_grid = {(item_id, seed) for item_id in selected_items for seed in seeds}
        if len(rows) != items * len(seeds):
            problems.append(f"{side} row count does not match items × seeds")
        if len(selected_items) != items or indexed.keys() != expected_grid:
            problems.append(f"{side} trial grid does not match its manifest")
    return indexed, problems


def _is_looser(previous: dict, current: dict) -> bool:
    if previous.get("no_significant_drop") and not current.get("no_significant_drop"):
        return True
    if "min" in previous and ("min" not in current or current["min"] < previous["min"]):
        return True
    return any(key in previous and (key not in current or current[key] > previous[key])
               for key in ("max", "max_increase"))


def _ratchet(spec: dict, base_spec: dict) -> list[str]:
    if spec.get("eval_set_version") != base_spec.get("eval_set_version"):
        return []
    problems = []
    for kind, key_fields in (("metrics", ("id",)), ("slices", ("name", "metric"))):
        candidates = {tuple(entry[field] for field in key_fields): entry for entry in spec.get(kind, [])}
        for previous in base_spec.get(kind, []):
            key = tuple(previous[field] for field in key_fields)
            label = "/".join(key)
            current = candidates.get(key)
            if current is None:
                problems.append(f"ratchet: removed {kind} entry {label}")
                continue
            if previous.get("blocking") and not current.get("blocking"):
                problems.append(f"ratchet: {label} no longer blocks")
            if _is_looser(previous.get("threshold", previous), current.get("threshold", current)):
                problems.append(f"ratchet: looser thresholds for {label}")
    return problems


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    graded = {metric["id"] for metric in spec["metrics"] if metric["id"] in GRADERS}
    candidate, problems = _report_index(pr, "PR", graded)
    baseline, base_problems = _report_index(base, "baseline", graded)
    problems.extend(base_problems)
    if candidate.keys() != baseline.keys():
        problems.append("PR trial keys differ from the baseline")
    elif candidate != baseline:
        problems.append("PR slice tags differ from the baseline")
    if base_spec is not None:
        problems.extend(_ratchet(spec, base_spec))
    return problems


def _paired_evidence(candidate: dict, baseline: dict, boot: dict) -> tuple[str, bool]:
    keys = sorted(candidate.keys() & baseline.keys())
    if not keys:
        return "no paired observations", False
    delta, low, high = stats.paired_bootstrap(
        [candidate[key] for key in keys], [baseline[key] for key in keys],
        n_resamples=boot.get("n_resamples", 1000), rng=boot.get("rng", 2027),
        confidence=boot.get("confidence", 0.95),
    )
    return f"Δ {delta:+.3f} CI [{low:+.3f}, {high:+.3f}]", high >= 0


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked, lines = [], []
    for rule in spec.get("slices", []):
        name, metric = rule["name"], rule["metric"]
        key = f"slice:{name}/{metric}"
        candidate = per_item(pr, metric, slice_name=name)
        value = sum(candidate.values()) / len(candidate) if candidate else None
        ok = value is not None and ("min" not in rule or value >= rule["min"])
        note = ""
        if rule.get("no_significant_drop"):
            baseline = per_item(base, metric, slice_name=name)
            note, stable = _paired_evidence(candidate, baseline, spec.get("bootstrap", {}))
            ok = ok and stable
        if not ok and rule.get("blocking"):
            blocked.append(key)
        verdict = "ok" if ok else ("BLOCK" if rule.get("blocking") else "warn")
        shown = "missing" if value is None else f"{value:.4f}"
        lines.append(f"  {key:<32} {shown:<8} {note:<28} {verdict}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            note, stable = _paired_evidence(per_item(pr, mid), per_item(base, mid), bs)
            if not stable:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
