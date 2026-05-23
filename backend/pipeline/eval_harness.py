from datetime import date

from app.agents.orchestrator import parse_intent_deterministic


QUERIES = [
    "Find me a quiet 1-bedroom in Lisbon near good restaurants for 3 nights in late June, under €130 a night, balcony if possible, no party-type buildings, and tell me which one has the most consistent reviews.",
    "Plan a 4-night London trip for a couple: one mid-range stay near the tube and one splurge night somewhere with a river view. Budget £900 total. Avoid anything in zone-edge/far-out neighbourhoods.",
    "Plan a Dubai stay under AED 700, near the metro, avoid Deira.",
    "Find a London entire place under £10.",
    "Find a quiet apartment for late June.",
]


def main() -> None:
    for query in QUERIES:
        parsed = parse_intent_deterministic(query, today=date(2026, 5, 23))
        print("=" * 80)
        print(query)
        print(parsed.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
