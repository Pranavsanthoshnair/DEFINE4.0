"""
Build stratified train / val / test splits from raw.jsonl.

Input:  ml/intent/data/raw.jsonl
Output: ml/intent/data/train.jsonl
        ml/intent/data/val.jsonl
        ml/intent/data/test.jsonl
        ml/intent/data/sample.jsonl  (200-row sample safe to commit to git)

Split: 80 / 10 / 10, stratified by (lang, label).

Usage:
  python ml/intent/build_dataset.py
"""
from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
RANDOM_SEED = 42


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def stratified_split(rows: list[dict], val_frac: float = 0.1, test_frac: float = 0.1):
    """Split rows into train/val/test, stratified by (lang, label)."""
    random.seed(RANDOM_SEED)
    buckets: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        key = (row.get("lang", "?"), row.get("label", "?"))
        buckets[key].append(row)

    train, val, test = [], [], []
    for rows_in_bucket in buckets.values():
        random.shuffle(rows_in_bucket)
        n = len(rows_in_bucket)
        n_test = max(1, round(n * test_frac))
        n_val = max(1, round(n * val_frac))
        test.extend(rows_in_bucket[:n_test])
        val.extend(rows_in_bucket[n_test : n_test + n_val])
        train.extend(rows_in_bucket[n_test + n_val :])

    random.shuffle(train)
    random.shuffle(val)
    random.shuffle(test)
    return train, val, test


def main() -> None:
    raw_path = DATA_DIR / "raw.jsonl"
    if not raw_path.exists():
        raise SystemExit(f"raw.jsonl not found at {raw_path}. Run generate_data.py first.")

    rows = load_jsonl(raw_path)
    print(f"Loaded {len(rows)} total rows from {raw_path}")

    train, val, test = stratified_split(rows)

    write_jsonl(DATA_DIR / "train.jsonl", train)
    write_jsonl(DATA_DIR / "val.jsonl", val)
    write_jsonl(DATA_DIR / "test.jsonl", test)

    # 200-row sample safe to commit
    sample = random.sample(rows, min(200, len(rows)))
    write_jsonl(DATA_DIR / "sample.jsonl", sample)

    print(f"train={len(train)}  val={len(val)}  test={len(test)}")
    print(f"Wrote splits to {DATA_DIR}")

    # Print per (lang, label) counts for train
    from collections import Counter
    counts = Counter((r["lang"], r["label"]) for r in train)
    print("\nTrain distribution:")
    for (lang, label), n in sorted(counts.items()):
        print(f"  [{lang}] {label}: {n}")


if __name__ == "__main__":
    main()
