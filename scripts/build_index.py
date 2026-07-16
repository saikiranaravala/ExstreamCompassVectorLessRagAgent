"""Build (or rebuild) the corpus caches and BM25 indexes.

Usage:
    PYTHONPATH=src python scripts/build_index.py [--variant CloudNative] [--rebuild]

Run once after changing the docs tree so the first API query doesn't pay the
parse cost. Caches land in .atlas/corpus_{variant}.json.gz.
"""

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from compass.retrieval.service import DEFAULT_VARIANTS, QueryService  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=DEFAULT_VARIANTS, help="Only this variant")
    parser.add_argument("--rebuild", action="store_true", help="Ignore existing caches")
    args = parser.parse_args()

    service = QueryService()
    variants = (args.variant,) if args.variant else DEFAULT_VARIANTS

    for variant in variants:
        started = time.time()
        index = service.get_index(variant, rebuild=args.rebuild)
        print(f"{variant}: {index.n_docs} documents indexed in {time.time() - started:.1f}s")

    print(f"Caches written to: {service.cache_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
