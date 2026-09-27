#!/usr/bin/env python3
"""
Generate submission.jsonl for the 30 canonical test pairs.
Format per challenge-brief.md §7.2:
{"test_id": "T01", "body": "...", "cta": "...", "send_as": "...", "suppression_key": "...", "rationale": "..."}
"""
from __future__ import annotations
import json
from pathlib import Path
from bot import compose

def main():
    base_dir = Path(__file__).parent
    expanded_dir = base_dir / "expanded"
    
    test_pairs_path = expanded_dir / "test_pairs.json"
    if not test_pairs_path.exists():
        print(f"Error: {test_pairs_path} not found. Run dataset/generate_dataset.py first.")
        return

    with open(test_pairs_path) as f:
        pairs = json.load(f)["pairs"]

    # Load categories
    categories = {}
    for cat_file in (expanded_dir / "categories").glob("*.json"):
        with open(cat_file) as f:
            data = json.load(f)
            categories[data.get("slug", cat_file.stem)] = data

    submission_lines = []
    for pair in pairs:
        test_id = pair["test_id"]
        tid = pair["trigger_id"]
        mid = pair["merchant_id"]
        cid = pair.get("customer_id")

        with open(expanded_dir / "triggers" / f"{tid}.json") as f:
            trigger = json.load(f)
        with open(expanded_dir / "merchants" / f"{mid}.json") as f:
            merchant = json.load(f)

        customer = None
        if cid:
            with open(expanded_dir / "customers" / f"{cid}.json") as f:
                customer = json.load(f)

        category = categories.get(merchant.get("category_slug", ""))

        res = compose(category, merchant, trigger, customer)

        row = {
            "test_id": test_id,
            "body": res["body"],
            "cta": res["cta"],
            "send_as": res["send_as"],
            "suppression_key": res["suppression_key"],
            "rationale": res["rationale"]
        }
        submission_lines.append(row)

    out_path = base_dir / "submission.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for row in submission_lines:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Successfully generated {len(submission_lines)} rows in {out_path}")

if __name__ == "__main__":
    main()
