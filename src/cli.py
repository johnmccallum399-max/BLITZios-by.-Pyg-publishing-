"""CLI entry point for quick testing without the API/UI.

Usage:
    python -m src.cli "What are the top 3 trends in AI-powered legal tech for 2025?"
    python -m src.cli --search "legal tech"
    python -m src.cli --stats
"""

import argparse
import json
import sys

from src.core.orchestrator import BLITZOrchestrator
from src.core.state_manager import KnowledgeArchive


def main(argv=None):
    parser = argparse.ArgumentParser(description="BLITZ Intelligence OS CLI")
    parser.add_argument("query", nargs="?", help="Research question to run")
    parser.add_argument("--search", metavar="TERM", help="Search the knowledge archive")
    parser.add_argument("--stats", action="store_true", help="Show archive statistics")
    parser.add_argument("--max-iterations", type=int, default=None, help="Loop bound (1-5)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON state")
    args = parser.parse_args(argv)

    archive = KnowledgeArchive()

    if args.stats:
        print(json.dumps(archive.get_stats(), indent=2))
        return 0

    if args.search:
        results = archive.search(args.search)
        print(f"Found {len(results)} record(s) matching '{args.search}':\n")
        for record in results:
            print(f"  [{record['timestamp'][:19]}] {record['query']}")
            print(f"    id={record['id']} confidence="
                  f"{record.get('scores', {}).get('average_confidence', '?')}")
        return 0

    if not args.query:
        parser.print_help()
        return 1

    orchestrator = BLITZOrchestrator(archive=archive)
    print(f"Researching: {args.query}\n")
    result = orchestrator.run(args.query, max_iterations=args.max_iterations)

    if not result["success"]:
        print(f"FAILED: {result.get('error')}", file=sys.stderr)
        return 1

    state = result["state"]
    if args.json:
        print(json.dumps(state, indent=2, default=str))
    else:
        print(state["response"])
        print(f"\nArchived as {result['doc_id']} "
              f"({result['elapsed_seconds']}s, archive now has "
              f"{result['stats']['total_entries']} entries)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
