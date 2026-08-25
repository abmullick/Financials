#!/usr/bin/env python3
"""
Validate retirement engine calculations against a saved JSON export.

Usage:
    python3 validate_export.py [path/to/retirement-plan.json]

If no path is provided, it looks for the most recent retirement-plan.json
in the current directory.
"""

import json
import sys
from pathlib import Path

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from models import PlannerInputs, AdHocExpense
from retirement_engine import run_projection, run_monte_carlo


def find_latest_json() -> Path | None:
    candidates = sorted(Path(".").glob("retirement-plan.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def main():
    if len(sys.argv) > 1:
        json_path = Path(sys.argv[1])
    else:
        json_path = find_latest_json()
        if not json_path:
            print("No retirement-plan.json found. Pass a path as an argument.", file=sys.stderr)
            sys.exit(1)

    if not json_path.exists():
        print(f"File not found: {json_path}", file=sys.stderr)
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        export = json.load(f)

    mode = export.get("mode", "deterministic")
    inputs_dict = export.get("inputs", {})
    saved_outputs = export.get("outputs", {})

    # Convert ad-hoc expense dicts to model instances if present
    ad_hoc = inputs_dict.get("adhoc_expenses", [])
    if ad_hoc:
        inputs_dict["adhoc_expenses"] = [AdHocExpense(**item) for item in ad_hoc]

    try:
        inputs = PlannerInputs(**inputs_dict)
    except Exception as e:
        print(f"Failed to reconstruct inputs from JSON: {e}", file=sys.stderr)
        sys.exit(2)

    print(f"Mode : {mode}")
    print(f"Inputs loaded from : {json_path}")
    print()

    if mode == "monte_carlo":
        fresh = run_monte_carlo(inputs)
        compare_section = "Monte Carlo outputs"
    else:
        fresh = run_projection(inputs)
        compare_section = "Deterministic outputs"

    # Compare top-level keys
    saved_keys = set(saved_outputs.keys())
    fresh_keys = set(fresh.keys())
    missing_in_fresh = saved_keys - fresh_keys
    extra_in_fresh = fresh_keys - saved_keys

    if missing_in_fresh:
        print(f"WARNING: Saved output has keys missing in fresh run: {sorted(missing_in_fresh)}")
    if extra_in_fresh:
        print(f"INFO: Fresh output has extra keys not in saved export: {sorted(extra_in_fresh)}")

    # Compare common metrics
    diffs = []
    common_keys = sorted(saved_keys & fresh_keys)

    for key in common_keys:
        saved_val = saved_outputs[key]
        fresh_val = fresh[key]

        if isinstance(saved_val, (int, float)) and isinstance(fresh_val, (int, float)):
            if abs(saved_val - fresh_val) > 1e-6:
                diffs.append((key, saved_val, fresh_val))
        elif saved_val != fresh_val:
            diffs.append((key, saved_val, fresh_val))

    if diffs:
        print(f"MISMATCHES in {compare_section}:")
        for key, saved, fresh in diffs[:20]:
            print(f"  {key}: saved={saved!r} fresh={fresh!r}")
        sys.exit(3)
    else:
        print(f"OK: {compare_section} match the saved JSON exactly.")


if __name__ == "__main__":
    main()
