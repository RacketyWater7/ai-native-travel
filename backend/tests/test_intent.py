from datetime import date

from app.agents.orchestrator import parse_intent_deterministic


def test_lisbon_golden_query_parses_budget_and_city():
    query = parse_intent_deterministic(
        "Find me a quiet 1-bedroom in Lisbon near good restaurants for 3 nights in late June, under €130 a night, balcony if possible",
        today=date(2026, 5, 23),
    )

    assert query.city == "Lisbon"
    assert query.currency == "EUR"
    assert query.nights == 3
    assert query.budget_per_night == 130
    assert query.soft_preferences["quiet"] is True
    assert query.soft_preferences["balcony"] is True


def test_dubai_template_parses_unsupported_city():
    query = parse_intent_deterministic("Find a Dubai stay under AED 700 and avoid Deira.")

    assert query.city == "Dubai"
    assert query.currency == "AED"
    assert query.hard_constraints["exclude_neighbourhoods"] == ["Deira"]
