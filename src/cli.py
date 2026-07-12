"""CLI entry point for quick testing without the API/UI.

Usage:
    python -m src.cli --status                  # what mode am I in, what to expect
    python -m src.cli "What are the top 3 trends in AI-powered legal tech for 2025?"
    python -m src.cli --search "legal tech"     # track: find past research
    python -m src.cli --stats                   # track: archive totals
"""

import argparse
import json
import sys

from src.core.config import Config
from src.core.orchestrator import BLITZOrchestrator
from src.core.state_manager import KnowledgeArchive


def print_status(archive: KnowledgeArchive):
    mode = Config.capability_mode()
    stats = archive.get_stats()
    print("BLITZ Intelligence OS — status\n")
    print(f"  Mode:       {mode['label']}")
    print(f"  Reasoning:  {mode['reasoning']}")
    print(f"  Evidence:   {mode['evidence']}")
    print(f"  Expect:     {mode['expect']}")
    if mode["upgrade"]:
        print(f"  To upgrade: {mode['upgrade']}")
    print("\n  Knowledge archive")
    print(f"    Entries:        {stats['total_entries']}")
    print(f"    Evidence items: {stats['total_evidence_items']}")
    print(f"    Total spend:    ${stats['total_cost']:.4f}")
    print("\n  Cost guards: max ${:.2f}/query, max {} iterations".format(
        Config.MAX_COST_PER_QUERY, Config.MAX_ITERATIONS))
    print('\n  Run a query:  python -m src.cli "your research question"')


def main(argv=None):
    parser = argparse.ArgumentParser(description="BLITZ Intelligence OS CLI")
    parser.add_argument("query", nargs="?", help="Research question to run")
    parser.add_argument("--status", action="store_true",
                        help="Show capability mode, expectations, and archive stats")
    parser.add_argument("--search", metavar="TERM", help="Search the knowledge archive")
    parser.add_argument("--stats", action="store_true", help="Show archive statistics")
    parser.add_argument("--max-iterations", type=int, default=None, help="Loop bound (1-5)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON state")
    args = parser.parse_args(argv)

    archive = KnowledgeArchive()

    if args.status:
        print_status(archive)
        return 0

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
        print('Track it later:  python -m src.cli --search "<term>"   |   --stats   |   --status')
    return 0


if __name__ == "__main__":
    sys.exit(main())
