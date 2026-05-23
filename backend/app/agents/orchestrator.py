import asyncio
import json
import re
import time
import uuid
from collections.abc import AsyncIterator
from datetime import date, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

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


async def _event(event: str, data: dict[str, Any]) -> dict[str, str]:
    return {"event": event, "data": json.dumps(data, default=str)}


async def concierge_stream(
    conn: AsyncConnection, request: ConciergeRequest
) -> AsyncIterator[dict[str, str]]:
    request_id = str(uuid.uuid4())
    steps: list[TraceStep] = []
    started = time.perf_counter()

    async def emit_step(name: str, status: str, detail: dict[str, Any]) -> dict[str, str]:
        step = TraceStep(name=name, status=status, detail=detail)
        steps.append(step)
        return await _event("step", step.model_dump())

    yield await _event("request", {"request_id": request_id})

    yield await emit_step("Intent", "started", {"message": request.message})
    intent = parse_intent_deterministic(request.message)
    await asyncio.sleep(0)
    yield await emit_step("Intent", "finished", {"travel_query": intent.model_dump()})

    route = "itinerary" if "plan" in request.message.lower() or "trip" in request.message.lower() else "search"
    if intent.city and intent.city.lower() not in {"lisbon", "london"}:
        yield await emit_step("Retrieval", "degraded", {"reason": "no inventory for this city"})
        final = {"type": "empty", "message": f"No inventory is loaded for {intent.city}.", "items": []}
        yield await _event("final", final)
    else:
        yield await emit_step("Retrieval", "started", {"route": route})
        response = await search_properties(conn, travel_query_to_search(intent))
        yield await emit_step(
            "Retrieval",
            "finished",
            {"count": response.total, "weights": response.weights, "top_ids": [p.id for p in response.items[:5]]},
        )

        if route == "itinerary":
            yield await emit_step("Itinerary", "started", {"budget_total": intent.budget_total})
            stays = response.items[:2]
            total = sum(float(stay.total_price or stay.price_per_night or 0) for stay in stays)
            final = {
                "type": "itinerary",
                "budget_total": intent.budget_total,
                "estimated_total": total,
                "days": [
                    {"day": 1, "title": "Arrive and settle in", "property": stays[0].model_dump() if stays else None},
                    {"day": 3, "title": "Swap to the splurge stay", "property": stays[1].model_dump() if len(stays) > 1 else None},
                ],
            }
            yield await emit_step("Itinerary", "finished", {"estimated_total": total})
            yield await _event("final", final)
        else:
            yield await emit_step("Review Intelligence", "started", {"candidate_count": len(response.items)})
            most_consistent = response.items[0] if response.items else None
            yield await emit_step(
                "Review Intelligence",
                "finished",
                {"most_consistent_id": most_consistent.id if most_consistent else None},
            )
            yield await _event(
                "final",
                {"type": "search", "items": [item.model_dump() for item in response.items]},
            )

    elapsed_ms = int((time.perf_counter() - started) * 1000)
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
            "tokens": 0,
            "cost": 0,
            "latency": elapsed_ms,
        },
    )
    yield await _event("done", {"request_id": request_id, "latency_ms": elapsed_ms})
