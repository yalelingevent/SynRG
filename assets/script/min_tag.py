# use: python3 assets/script/min_tag.py assets/meta/tags.json --all -o assets/meta/min-tag.json

import argparse
import json
import sys
from pathlib import Path
 
 
def load_tag_index(path: Path) -> dict[str, set[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {tag: set(files) for tag, files in data.items()}
 
 
def remove_dominated_tags(tag_to_files: dict[str, set[str]]) -> dict[str, set[str]]:
    """
    Drop any tag whose post set is a subset of another tag's post set.
    Such a tag is never uniquely necessary: swapping it for the
    dominating tag in any cover never covers fewer posts. Ties
    (identical post sets) are broken by name so exactly one survives.
    """
    items = list(tag_to_files.items())
    kept = {}
    for i, (tag, files) in enumerate(items):
        dominated = False
        for j, (other_tag, other_files) in enumerate(items):
            if i == j:
                continue
            if files <= other_files and (files != other_files or tag > other_tag):
                dominated = True
                break
        if not dominated:
            kept[tag] = files
    return kept
 
 
def min_set_cover(tag_to_files: dict[str, set[str]], universe: set[str]):
    """
    Exact minimum set cover via branch-and-bound.
    Returns (best_size, best_combo, uncoverable_posts).
    """
    file_to_tags: dict[str, list[str]] = {f: [] for f in universe}
    for tag, files in tag_to_files.items():
        for f in files:
            if f in file_to_tags:
                file_to_tags[f].append(tag)
 
    # Try larger tags first within each branch -> finds good solutions
    # early, which makes the pruning bound tighter sooner.
    for f in file_to_tags:
        file_to_tags[f].sort(key=lambda t: len(tag_to_files[t]), reverse=True)
 
    uncoverable = {f for f, tags in file_to_tags.items() if not tags}
    coverable_universe = universe - uncoverable
 
    best = {"size": len(tag_to_files) + 1, "combo": None}
 
    def backtrack(remaining: set[str], chosen: list[str]):
        if not remaining:
            if len(chosen) < best["size"]:
                best["size"] = len(chosen)
                best["combo"] = list(chosen)
            return
        if len(chosen) + 1 >= best["size"]:
            return  # even one more tag ties or loses to current best
        target = min(remaining, key=lambda f: len(file_to_tags[f]))
        for tag in file_to_tags[target]:
            chosen.append(tag)
            backtrack(remaining - tag_to_files[tag], chosen)
            chosen.pop()
 
    backtrack(coverable_universe, [])
    size = best["size"] if best["combo"] is not None else None
    return size, best["combo"], uncoverable
 
 
def all_min_set_covers(tag_to_files: dict[str, set[str]], universe: set[str], n: int, limit: int | None = None):
    """
    Enumerate every distinct set cover of exactly size n (the known
    minimum). Returns (solutions, hit_limit) where solutions is a list
    of sorted tag-name lists, and hit_limit is True if the search was
    cut off early because `limit` was reached (meaning there may be
    more solutions not shown).
    """
    file_to_tags: dict[str, list[str]] = {f: [] for f in universe}
    for tag, files in tag_to_files.items():
        for f in files:
            if f in file_to_tags:
                file_to_tags[f].append(tag)
    for f in file_to_tags:
        file_to_tags[f].sort(key=lambda t: len(tag_to_files[t]), reverse=True)
 
    coverable_universe = {f for f in universe if file_to_tags[f]}
 
    solutions: list[list[str]] = []
    seen: set[frozenset] = set()
    hit_limit = False
 
    def backtrack(remaining: set[str], chosen: list[str]):
        nonlocal hit_limit
        if limit is not None and len(solutions) >= limit:
            hit_limit = True
            return
        if not remaining:
            if len(chosen) == n:
                key = frozenset(chosen)
                if key not in seen:
                    seen.add(key)
                    solutions.append(sorted(chosen))
            return
        if len(chosen) >= n:
            return  # can't cover what's left without exceeding n
        target = min(remaining, key=lambda f: len(file_to_tags[f]))
        for tag in file_to_tags[target]:
            chosen.append(tag)
            backtrack(remaining - tag_to_files[tag], chosen)
            chosen.pop()
            if limit is not None and len(solutions) >= limit:
                hit_limit = True
                return
 
    backtrack(coverable_universe, [])
    return solutions, hit_limit
 
 
def main():
    parser = argparse.ArgumentParser(
        description="Find the minimum number of tags that together cover all posts."
    )
    parser.add_argument(
        "index", type=Path, nargs="?", default=Path("tags.json"),
        help="Path to the tag index JSON produced by generate_tag_index.py (default: tags.json)"
    )
    parser.add_argument(
        "-o", "--output", type=Path, default=None,
        help="Optional path to also write the chosen tag names as a JSON array"
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Find every distinct minimal cover, not just one"
    )
    parser.add_argument(
        "--limit", type=int, default=1000,
        help="Max number of minimal covers to collect with --all, as a safety cap (default: 1000)"
    )
    args = parser.parse_args()
 
    if not args.index.is_file():
        parser.error(f"{args.index} not found")
 
    tag_to_files = load_tag_index(args.index)
    universe = set().union(*tag_to_files.values()) if tag_to_files else set()
 
    if not universe:
        print("No tagged posts found.")
        return
 
    pruned = remove_dominated_tags(tag_to_files)
    size, combo, uncoverable = min_set_cover(pruned, universe)
 
    print(f"Total tagged posts: {len(universe)}")
    print(f"Total tags: {len(tag_to_files)} ({len(pruned)} remain after removing dominated tags)")
 
    if uncoverable:
        print(f"\n{len(uncoverable)} post(s) have no tags and can never be covered by any tag:")
        for f in sorted(uncoverable):
            print(f"  - {f}")
 
    if size is None:
        print("\nNo combination of tags covers every (taggable) post.")
        return
 
    print(f"\nMinimum number of tags needed to cover all coverable posts: {size}")
 
    if not args.all:
        sorted_combo = sorted(combo)
        print("One minimal combination:")
        for tag in sorted_combo:
            files = sorted(tag_to_files[tag])
            print(f"  - {tag}  ({len(files)} posts)")
            for f in files:
                print(f"      • {f}")
 
        print(f"\nExact tag names (as a list): {sorted_combo}")
 
        if args.output:
            output_data = {tag: sorted(tag_to_files[tag]) for tag in sorted_combo}
            args.output.write_text(json.dumps(output_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"Tag names and their files also written to {args.output}")
        return
 
    # --all mode: enumerate every distinct minimal combination
    solutions, hit_limit = all_min_set_covers(pruned, universe, size, limit=args.limit)
    print(f"Found {len(solutions)} distinct minimal combination(s) of size {size}:")
    for i, sol in enumerate(solutions, start=1):
        print(f"\n[{i}] {sol}")
        for tag in sol:
            files = sorted(tag_to_files[tag])
            print(f"  - {tag}  ({len(files)} posts)")
            for f in files:
                print(f"      • {f}")
 
    if hit_limit:
        print(
            f"\nStopped after reaching the limit of {args.limit} combinations "
            f"— there may be more. Re-run with --limit to raise the cap."
        )
 
    if args.output:
        output_data = [
            {tag: sorted(tag_to_files[tag]) for tag in sol}
            for sol in solutions
        ]
        args.output.write_text(json.dumps(output_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"\nAll combinations also written to {args.output}")
 
 
if __name__ == "__main__":
    main()