# usage: python3 assets/script/generate_tag_index.py _posts -o assets/meta/tags.json

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

# Matches a leading front matter block: --- ... --- at the very start of file
FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def extract_front_matter(text: str) -> dict | None:
    """Return the parsed front matter dict, or None if not found/invalid."""
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return None
    raw_yaml = match.group(1)
    try:
        data = yaml.safe_load(raw_yaml)
    except yaml.YAMLError as exc:
        print(f"  ! YAML parse error: {exc}", file=sys.stderr)
        return None
    if not isinstance(data, dict):
        return None
    return data


def normalize_tags(value) -> list[str]:
    """Turn a tags value (str, list, or other) into a clean list of strings."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, (list, tuple)):
        result = []
        for item in value:
            if item is None:
                continue
            item_str = str(item).strip()
            if item_str:
                result.append(item_str)
        return result
    # Fallback: stray scalar type (int, bool, etc.) - stringify it
    return [str(value).strip()]


def build_index(root: Path) -> dict:
    """Walk root recursively, build {tag: [relative file paths]}."""
    index: dict[str, list[str]] = {}

    md_files = sorted(root.rglob("*.md"))
    if not md_files:
        print(f"No .md files found under {root}", file=sys.stderr)

    for md_path in md_files:
        try:
            text = md_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            print(f"  ! Could not read {md_path}: {exc}", file=sys.stderr)
            continue

        front_matter = extract_front_matter(text)
        if front_matter is None:
            print(f"  - Skipping {md_path} (no/invalid front matter)", file=sys.stderr)
            continue

        tags = normalize_tags(front_matter.get("tags"))
        if not tags:
            print(f"  - Skipping {md_path} (no 'tags' set)", file=sys.stderr)
            continue

        file_name = md_path.name
        for tag in tags:
            index.setdefault(tag, []).append(file_name)

    # Sort tags alphabetically and dedupe/sort file lists for stable output
    return {
        tag: sorted(set(files))
        for tag, files in sorted(index.items(), key=lambda kv: kv[0].lower())
    }


def main():
    parser = argparse.ArgumentParser(
        description="Build a tag -> [md files] index from front matter."
    )
    parser.add_argument("root", type=Path, help="Root folder containing subfolders of .md files")
    parser.add_argument(
        "-o", "--output", type=Path, default=Path("tags.json"),
        help="Output JSON file path (default: tags.json)"
    )
    parser.add_argument(
        "--indent", type=int, default=2,
        help="JSON indentation (default: 2)"
    )
    args = parser.parse_args()

    if not args.root.is_dir():
        parser.error(f"{args.root} is not a directory")

    index = build_index(args.root)

    args.output.write_text(
        json.dumps(index, indent=args.indent, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )

    total_files = len({f for files in index.values() for f in files})
    print(f"\nFound {len(index)} tags across {total_files} files.")
    print(f"Wrote index to {args.output}")


if __name__ == "__main__":
    main()