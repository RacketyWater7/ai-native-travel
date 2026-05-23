import json
import re
import time
import uuid
from collections.abc import AsyncIterator
from datetime import date, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.llm import generate_concierge_answer, generate_intent, generate_review_intelligence
from app.models import ConciergeRequest, SearchParams, TraceStep, TravelQuery
from app.search import search_properties


def _late_june_window(today: date) -> tuple[date, date]:
    year = today.year if today.month <= 6 else today.year + 1
    return date(year, 6, 24), date(year, 6, 27)


def parse_intent_deterministic(message: str, today: date | None = None) -> TravelQuery:
    today = today or date.today()
    text_lower = message.lower()
    query = TravelQuery()

    if "lisbon" in text_lower:
        query.city = "Lisbon"
        query.currency = "EUR"
    elif "london" in text_lower:
        query.city = "London"
        query.currency = "GBP"
    elif "dubai" in text_lower:
        query.city = "Dubai"
        query.currency = "AED"

    nights_match = re.search(r"(\d+)[-\s]?night", text_lower)
    if nights_match:
        query.nights = int(nights_match.group(1))
    if "late june" in text_lower:
        check_in, check_out = _late_june_window(today)
        query.check_in = check_in
        query.check_out = check_in + timedelta(days=query.nights or (check_out - check_in).days)

    per_night = re.search(r"under\s*[€£]?\s*(\d+)\s*(?:a|per)?\s*night", text_lower)
    if not per_night:
        per_night = re.search(r"under\s*[€£]\s*(\d+)", text_lower)
    if per_night:
        query.budget_per_night = float(per_night.group(1))
    total = re.search(r"budget\s*[€£]?\s*(\d+)\s*total|[€£]\s*(\d+)\s*total", text_lower)
    if total:
        query.budget_total = float(next(group for group in total.groups() if group))

    if "couple" in text_lower:
        query.party_type = "couple"
        query.adults = 2
    if "family" in text_lower:
        query.party_type = "family"
    if "1-bedroom" in text_lower or "1 bedroom" in text_lower or "1-bed" in text_lower:
        query.hard_constraints["bedrooms"] = 1
    if "private room" in text_lower:
        query.hard_constraints["room_type"] = "Private room"
    if "entire" in text_lower:
        query.hard_constraints["room_type"] = "Entire home/apt"
    if "avoid" in text_lower:
        avoided = re.findall(r"avoid(?: anything in)? ([a-zA-Z\-/ ]+?)(?: neighbourhoods|\.|,|$)", message, re.I)
        if avoided:
            query.hard_constraints["exclude_neighbourhoods"] = [avoided[0].strip()]
    if "near the tube" in text_lower or "near tube" in text_lower or "near the metro" in text_lower:
        query.hard_constraints["near_transit"] = True

    prefs: dict[str, Any] = {}
    for key in ["quiet", "balcony", "river view", "restaurants", "no party", "splurge", "mid-range"]:
        if key in text_lower:
            prefs[key.replace(" ", "_").replace("-", "_")] = True
    if prefs:
        query.soft_preferences = prefs
    query.sort_hint = "rating"
    return query


def travel_query_to_search(query: TravelQuery) -> SearchParams:
    hard = query.hard_constraints
    amenities: list[str] = []
    if query.soft_preferences.get("balcony"):
        amenities.append("balcony")
    if query.soft_preferences.get("river_view"):
        amenities.append("river_view")
    return SearchParams(
        city=query.city,
        check_in=query.check_in,
        check_out=query.check_out,
        max_price=query.budget_per_night,
        room_type=hard.get("room_type"),
        amenities=amenities,
        exclude_neighbourhoods=hard.get("exclude_neighbourhoods", []),
        near_transit=hard.get("near_transit"),
        q="quiet restaurants" if query.soft_preferences.get("quiet") else None,
        sort="rating",
        page_size=8,
    )


def _compact_property(item: Any) -> dict[str, Any]:
    data = item.model_dump(mode="json") if hasattr(item, "model_dump") else dict(item)
    return {
        "id": data.get("id"),
        "name": data.get("name"),
        "city": data.get("city"),
        "neighbourhood": data.get("neighbourhood"),
        "room_type": data.get("room_type_normalized"),
        "accommodates": data.get("accommodates"),
        "bedrooms": data.get("bedrooms"),
        "price_per_night": data.get("price_per_night"),
        "total_price": data.get("total_price"),
        "currency": data.get("currency"),
        "amenities": data.get("amenities_normalized") or [],
        "near_transit": data.get("near_transit"),
        "nearest_transit": data.get("nearest_transit"),
        "rating_overall": data.get("rating_overall"),
        "review_count": data.get("review_count"),
        "price_percentile_in_area": data.get("price_percentile_in_area"),
        "ai_review_summary": data.get("ai_review_summary"),
        "rationale": data.get("rationale"),
    }


async def _review_snippets(conn: AsyncConnection, property_ids: list[int]) -> list[dict[str, Any]]:
    if not property_ids:
        return []
    result = await conn.execute(
        text(
            """
            SELECT id, property_id, date, reviewer_name, language, rating, comments,
                   sent_cleanliness, sent_location, sent_value, sent_staff, sent_noise
            FROM reviews
            WHERE property_id = ANY(CAST(:ids AS bigint[]))
              AND comments IS NOT NULL
            ORDER BY rating DESC NULLS LAST, date DESC NULLS LAST
            LIMIT 36
            """
        ),
        {"ids": property_ids[:8]},
    )
    snippets = []
    for row in result.mappings().all():
        data = dict(row)
        comment = data.get("comments") or ""
        data["comments"] = comment[:420]
        snippets.append(data)
    return snippets


def _usage_add(total: dict[str, Any], usage: dict[str, Any]) -> None:
    total["tokens"] = int(total.get("tokens", 0)) + int(usage.get("tokens", 0) or 0)
    total["cost_usd"] = float(total.get("cost_usd", 0)) + float(usage.get("cost_usd", 0) or 0)
    providers = total.setdefault("providers", [])
    provider = usage.get("provider")
    if provider and provider not in providers:
        providers.append(provider)


async def _event(event: str, data: dict[str, Any]) -> dict[str, str]:
    return {"event": event, "data": json.dumps(data, default=str)}


async def concierge_stream(
    conn: AsyncConnection, request: ConciergeRequest
) -> AsyncIterator[dict[str, str]]:
    request_id = str(uuid.uuid4())
    steps: list[TraceStep] = []
    started = time.perf_counter()
    usage_total: dict[str, Any] = {"tokens": 0, "cost_usd": 0, "providers": []}

    async def emit_step(name: str, status: str, detail: dict[str, Any]) -> dict[str, str]:
        step = TraceStep(name=name, status=status, detail=detail)
        steps.append(step)
        return await _event("step", step.model_dump())

    yield await _event("request", {"request_id": request_id})

    yield await emit_step("Intent", "started", {"message": request.message})
    fallback_intent = parse_intent_deterministic(request.message)
    intent, intent_usage = await generate_intent(
        request.message, request.current_filters, fallback_intent, date.today().isoformat()
    )
    _usage_add(usage_total, intent_usage)
    yield await emit_step(
        "Intent",
        "finished",
        {
            "agent": "Intent Agent",
            "provider": intent_usage.get("provider"),
            "travel_query": intent.model_dump(mode="json"),
        },
    )

    route = "itinerary" if "plan" in request.message.lower() or "trip" in request.message.lower() else "search"
    if intent.city and intent.city.lower() not in {"lisbon", "london"}:
        yield await emit_step(
            "Retrieval",
            "degraded",
            {
                "agent": "Retrieval Agent",
                "reason": f"No loaded inventory for {intent.city}",
                "supported_cities": ["Lisbon", "London"],
            },
        )
        final = {
            "type": "empty",
            "title": f"{intent.city} is not in the loaded inventory yet",
            "summary": (
                "I will not invent stays that are not in the database. "
                "This demo currently has searchable inventory for Lisbon and London."
            ),
            "traveler_notes": [
                "Try Lisbon or London for fully grounded recommendations.",
                "The agent still parsed your intent and preserved your hard constraints.",
            ],
            "intent": intent.model_dump(mode="json"),
            "items": [],
        }
        yield await _event("final", final)
    else:
        yield await emit_step(
            "Retrieval",
            "started",
            {"agent": "Retrieval Agent", "route": route, "search": travel_query_to_search(intent).model_dump(mode="json")},
        )
        response = await search_properties(conn, travel_query_to_search(intent))
        candidates = [_compact_property(item) for item in response.items[:8]]
        yield await emit_step(
            "Retrieval",
            "finished",
            {
                "agent": "Retrieval Agent",
                "count": response.total,
                "weights": response.weights,
                "top_ids": [p.id for p in response.items[:5]],
                "rationale": "Structured filters are combined with ranking signals already stored in the corpus.",
            },
        )

        yield await emit_step(
            "Review Intelligence",
            "started",
            {"agent": "Review Intelligence Agent", "candidate_count": len(candidates)},
        )
        snippets = await _review_snippets(conn, [int(item["id"]) for item in candidates])
        review_intelligence, review_usage = await generate_review_intelligence(
            intent, candidates, snippets
        )
        _usage_add(usage_total, review_usage)
        yield await emit_step(
            "Review Intelligence",
            "finished",
            {
                "agent": "Review Intelligence Agent",
                "provider": review_usage.get("provider"),
                "fallback_reason": review_usage.get("fallback_reason"),
                "headline": review_intelligence.get("headline"),
                "citations": sum(
                    len(item.get("citations", []))
                    for item in review_intelligence.get("insights", [])
                    if isinstance(item, dict)
                ),
            },
        )

        final_agent = "Itinerary Agent" if route == "itinerary" else "Concierge Answer Agent"
        yield await emit_step(final_agent.replace(" Agent", ""), "started", {"agent": final_agent})
        final, final_usage = await generate_concierge_answer(
            route, request.message, intent, candidates, review_intelligence
        )
        _usage_add(usage_total, final_usage)
        final["intent"] = intent.model_dump(mode="json")
        final["candidates"] = candidates[:4]
        final["review_intelligence"] = review_intelligence
        final["usage"] = usage_total
        yield await emit_step(
            final_agent.replace(" Agent", ""),
            "finished",
            {
                "agent": final_agent,
                "provider": final_usage.get("provider"),
                "fallback_reason": final_usage.get("fallback_reason"),
                "tokens_so_far": usage_total["tokens"],
            },
        )
        yield await _event("final", final)

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    usage_total["latency_ms"] = elapsed_ms
    await conn.execute(
        text(
            """
            INSERT INTO agent_traces
              (request_id, session_id, query, steps, total_tokens, total_cost_usd, total_latency_ms)
            VALUES (:request_id, :session_id, :query, CAST(:steps AS jsonb), :tokens, :cost, :latency)
            """
        ),
        {
            "request_id": request_id,
            "session_id": request.session_id,
            "query": request.message,
            "steps": json.dumps([step.model_dump(mode="json") for step in steps]),
            "tokens": usage_total["tokens"],
            "cost": usage_total["cost_usd"],
            "latency": elapsed_ms,
        },
    )
    yield await _event("done", {"request_id": request_id, **usage_total})
