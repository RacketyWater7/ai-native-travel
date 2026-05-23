import json
import re
from typing import Any

import httpx

from app.config import get_settings
from app.models import TravelQuery


COMPARE_PROMPT = """You are the review intelligence agent for an AI-native booking product.

Use only the supplied property rows. Do not invent facts, do not claim live availability beyond the rows,
and mention listing IDs when making a concrete recommendation. Write a crisp verdict a traveler can trust:
best overall, best value, best review confidence, and any trade-off. Keep it under 120 words.

Return plain text only.
"""

INTENT_PROMPT = """You are the Intent Agent for a booking product.

Convert the traveler message into one strict JSON object matching this shape:
{"city": string|null, "check_in": "YYYY-MM-DD"|null, "check_out": "YYYY-MM-DD"|null, "nights": number|null, "adults": number, "children": number, "rooms": number, "budget_total": number|null, "budget_per_night": number|null, "currency": "EUR"|"GBP"|"AED"|null, "party_type": "couple"|"family"|"solo"|"group"|null, "hard_constraints": object, "soft_preferences": object, "sort_hint": string|null}

Guardrails:
- Extract only what the user asked for. Do not invent exact dates unless a relative date phrase is present.
- For relative dates, use the supplied current date.
- Put must-have requirements in hard_constraints and nice-to-have requirements in soft_preferences.
- Normalize rooms/bedrooms, room_type, excluded neighbourhoods, transit, quiet/no-party, view, balcony, restaurants, and vibe terms.
- Return JSON only. No markdown.
"""

REVIEW_INTELLIGENCE_PROMPT = """You are the Review Intelligence Agent for a travel booking product.

Use only the supplied listings and review snippets. Produce strict JSON:
{"headline": string, "best_property_id": number|null, "most_consistent_property_id": number|null, "insights": [{"property_id": number, "summary": string, "pros": [string], "cons": [string], "consistency_score": number, "citations": [{"review_id": number, "quote": string}]}], "warnings": [string]}

Guardrails:
- Cite only review_id values provided in REVIEW_SNIPPETS.
- Quote short exact snippets from supplied reviews only.
- If review evidence is thin, say so in warnings.
- Do not claim live availability except from supplied listing fields.
- Return JSON only. No markdown.
"""

ITINERARY_PROMPT = """You are the Itinerary Agent for an AI-native travel booking product.

Use only the supplied structured intent, candidate listings, and review intelligence. Produce strict JSON:
{"type": "itinerary", "title": string, "summary": string, "budget_total": number|null, "estimated_total": number|null, "currency": string|null, "days": [{"day": number, "title": string, "description": string, "property_id": number|null}], "stays": [{"title": string, "nights": number, "property_id": number|null, "why": string, "swap_strategy": string}], "citations": [{"property_id": number, "review_id": number|null, "label": string}], "traveler_notes": [string]}

Guardrails:
- Recommend only supplied property IDs.
- Respect hard constraints first; call out any unmet constraint.
- Keep totals grounded in supplied price_per_night and requested nights.
- Avoid raw database dumps; write for a normal traveler.
- Return JSON only. No markdown.
"""

SEARCH_ANSWER_PROMPT = """You are the Concierge Answer Agent for a booking product.

Use only the supplied structured intent, ranked candidates, and review intelligence. Produce strict JSON:
{"type": "search", "title": string, "summary": string, "items": [{"property_id": number, "why": string, "best_for": string, "caveat": string|null}], "citations": [{"property_id": number, "review_id": number|null, "label": string}], "traveler_notes": [string]}

Guardrails:
- Recommend only supplied property IDs.
- Explain trade-offs in plain traveler language.
- If evidence is missing, say what is missing.
- Return JSON only. No markdown.
"""


def _json_from_text(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.I).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.S)
        if not match:
            raise
        value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("LLM returned non-object JSON")
    return value


def _safe_error_reason(error: Exception) -> str:
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        try:
            payload = error.response.json()
            message = payload.get("error", {}).get("message") or error.response.text
        except Exception:
            message = error.response.text
        return f"Gemini HTTP {status}: {str(message)[:180]}"
    return f"{error.__class__.__name__}: {str(error)[:180]}"


async def _gemini_json(prompt: str, payload: dict[str, Any], max_tokens: int = 900) -> tuple[dict[str, Any], dict[str, Any]]:
    settings = get_settings()
    if settings.mock_llm or not settings.gemini_api_key:
        raise RuntimeError("LLM is not configured")
    body = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": f"{prompt}\n\nINPUT:\n{json.dumps(payload, default=str)}"}],
            }
        ],
        "generationConfig": {
            "temperature": 0.15,
            "maxOutputTokens": max_tokens,
            "responseMimeType": "application/json",
        },
    }
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash:generateContent?key={settings.gemini_api_key}"
    )
    async with httpx.AsyncClient(timeout=18) as client:
        response = await client.post(url, json=body)
        response.raise_for_status()
        result = response.json()
    text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
    usage = result.get("usageMetadata", {})
    tokens = usage.get("totalTokenCount", 0)
    return _json_from_text(text), {
        "provider": "gemini-2.5-flash",
        "tokens": tokens,
        "cost_usd": 0,
    }


async def generate_intent(
    message: str, current_filters: dict[str, Any], fallback: TravelQuery, today: str
) -> tuple[TravelQuery, dict[str, Any]]:
    try:
        data, usage = await _gemini_json(
            INTENT_PROMPT,
            {
                "message": message,
                "current_filters": current_filters,
                "today": today,
                "deterministic_fallback": fallback.model_dump(mode="json"),
            },
            max_tokens=700,
        )
        merged = fallback.model_dump()
        for key, value in data.items():
            if value not in (None, "", [], {}):
                merged[key] = value
        return TravelQuery.model_validate(merged), usage
    except Exception as error:
        return fallback, {
            "provider": "deterministic_fallback",
            "tokens": 0,
            "cost_usd": 0,
            "fallback_reason": _safe_error_reason(error),
        }


async def generate_review_intelligence(
    intent: TravelQuery, candidates: list[dict[str, Any]], reviews: list[dict[str, Any]]
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not candidates:
        return {
            "headline": "No matching stays were found in the loaded inventory.",
            "best_property_id": None,
            "most_consistent_property_id": None,
            "insights": [],
            "warnings": ["No candidates were available for review synthesis."],
        }, {"provider": "deterministic", "tokens": 0, "cost_usd": 0}
    try:
        return await _gemini_json(
            REVIEW_INTELLIGENCE_PROMPT,
            {
                "intent": intent.model_dump(mode="json"),
                "candidates": candidates,
                "review_snippets": reviews,
            },
            max_tokens=1100,
        )
    except Exception as error:
        reason = _safe_error_reason(error)
        best = max(
            candidates,
            key=lambda item: (
                float(item.get("rating_overall") or 0),
                int(item.get("review_count") or 0),
            ),
        )
        review_by_property: dict[int, list[dict[str, Any]]] = {}
        for review in reviews:
            review_by_property.setdefault(int(review["property_id"]), []).append(review)
        insights = []
        for item in candidates[:4]:
            pid = int(item["id"])
            citations = [
                {"review_id": review["id"], "quote": (review.get("comments") or "")[:180]}
                for review in review_by_property.get(pid, [])[:2]
            ]
            insights.append(
                {
                    "property_id": pid,
                    "summary": item.get("ai_review_summary") or item.get("rationale") or "Strong match for the requested filters.",
                    "pros": [item.get("rationale") or "Matches the ranked search criteria."],
                    "cons": [],
                    "consistency_score": float(item.get("rating_overall") or 0),
                    "citations": citations,
                }
            )
        return {
            "headline": f"#{best['id']} is the strongest review-backed match in the current result set.",
            "best_property_id": best["id"],
            "most_consistent_property_id": best["id"],
            "insights": insights,
            "warnings": [f"Used deterministic review synthesis because the LLM call fell back: {reason}"],
        }, {
            "provider": "deterministic_fallback",
            "tokens": 0,
            "cost_usd": 0,
            "fallback_reason": reason,
        }


async def generate_concierge_answer(
    route: str,
    message: str,
    intent: TravelQuery,
    candidates: list[dict[str, Any]],
    review_intelligence: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    prompt = ITINERARY_PROMPT if route == "itinerary" else SEARCH_ANSWER_PROMPT
    try:
        data, usage = await _gemini_json(
            prompt,
            {
                "message": message,
                "intent": intent.model_dump(mode="json"),
                "candidates": candidates,
                "review_intelligence": review_intelligence,
            },
            max_tokens=1200,
        )
        return data, usage
    except Exception as error:
        reason = _safe_error_reason(error)
        if route == "itinerary":
            nights = max(intent.nights or 1, 1)
            first = candidates[0] if candidates else None
            second = candidates[1] if len(candidates) > 1 else first
            first_nights = max(1, nights - 1) if second and second != first else nights
            second_nights = nights - first_nights if second and second != first else 0
            estimated = 0.0
            stays = []
            for title, stay, stay_nights in [
                ("Base stay", first, first_nights),
                ("Splurge stay", second, second_nights),
            ]:
                if stay and stay_nights:
                    estimated += float(stay.get("price_per_night") or 0) * stay_nights
                    stays.append(
                        {
                            "title": title,
                            "nights": stay_nights,
                            "property_id": stay["id"],
                            "why": stay.get("rationale") or "Best available ranked match.",
                            "swap_strategy": "Use the next ranked candidate with the same hard constraints.",
                        }
                    )
            return {
                "type": "itinerary",
                "title": f"{nights}-night {intent.city or 'travel'} plan",
                "summary": review_intelligence.get("headline", "Built from ranked available stays."),
                "budget_total": intent.budget_total,
                "estimated_total": round(estimated, 2),
                "currency": intent.currency,
                "days": [
                    {
                        "day": 1,
                        "title": "Arrive and settle in",
                        "description": "Start with the strongest practical match for location, budget, and reviews.",
                        "property_id": first["id"] if first else None,
                    },
                    {
                        "day": max(first_nights + 1, 1),
                        "title": "Switch stay if useful",
                        "description": "Use the second stay for the requested splurge or different neighborhood experience.",
                        "property_id": second["id"] if second_nights and second else None,
                    },
                ],
                "stays": stays,
                "citations": [],
                "traveler_notes": [f"Used deterministic itinerary planning because the LLM call fell back: {reason}"],
            }, {
                "provider": "deterministic_fallback",
                "tokens": 0,
                "cost_usd": 0,
                "fallback_reason": reason,
            }
        return {
            "type": "search",
            "title": f"Best matches in {intent.city or 'your destination'}",
            "summary": review_intelligence.get("headline", "Ranked using the loaded inventory and filters."),
            "items": [
                {
                    "property_id": item["id"],
                    "why": item.get("rationale") or "Matches the requested filters.",
                    "best_for": "Strong overall match",
                    "caveat": None,
                }
                for item in candidates[:4]
            ],
            "citations": [],
            "traveler_notes": [f"Used deterministic answer writing because the LLM call fell back: {reason}"],
        }, {
            "provider": "deterministic_fallback",
            "tokens": 0,
            "cost_usd": 0,
            "fallback_reason": reason,
        }


def _fallback_compare_verdict(items: list[dict[str, Any]]) -> str:
    if not items:
        return "Pick 2-4 listings to compare."
    ranked = sorted(
        items,
        key=lambda item: (
            float(item.get("rating_overall") or 0),
            int(item.get("review_count") or 0),
            -float(item.get("price_per_night") or 10_000),
        ),
        reverse=True,
    )
    best = ranked[0]
    cheapest = min(items, key=lambda item: float(item.get("price_per_night") or 10_000))
    best_rating = float(best.get("rating_overall") or 0)
    cheapest_price = float(cheapest.get("price_per_night") or 0)
    return (
        f"Best overall: #{best['id']} {best['name']} because it combines a "
        f"{best_rating:.2f} rating with {best.get('review_count', 0)} reviews. "
        f"Best value: #{cheapest['id']} at {cheapest.get('currency', '')}{cheapest_price:.0f}/night. "
        "This verdict is grounded in stored listing, price, rating, amenity, and review-count rows."
    )


async def generate_compare_verdict(items: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    settings = get_settings()
    if settings.mock_llm or not settings.gemini_api_key:
        return _fallback_compare_verdict(items), {"provider": "deterministic", "tokens": 0, "cost_usd": 0}

    compact_items = [
        {
            "id": item.get("id"),
            "name": item.get("name"),
            "city": item.get("city"),
            "neighbourhood": item.get("neighbourhood"),
            "room_type": item.get("room_type_normalized"),
            "price_per_night": float(item["price_per_night"]) if item.get("price_per_night") is not None else None,
            "currency": item.get("currency"),
            "rating_overall": float(item["rating_overall"]) if item.get("rating_overall") is not None else None,
            "review_count": item.get("review_count"),
            "near_transit": item.get("near_transit"),
            "nearest_transit": item.get("nearest_transit"),
            "amenities": item.get("amenities_normalized") or [],
            "ai_review_summary": item.get("ai_review_summary"),
        }
        for item in items
    ]
    body = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": f"{COMPARE_PROMPT}\n\nPROPERTY_ROWS:\n{json.dumps(compact_items)}"}],
            }
        ],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 220},
    }
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash:generateContent?key={settings.gemini_api_key}"
    )
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.post(url, json=body)
            response.raise_for_status()
            payload = response.json()
        text = payload["candidates"][0]["content"]["parts"][0]["text"].strip()
        if len(text.split()) < 18:
            fallback = _fallback_compare_verdict(items)
            return fallback, {"provider": "deterministic_quality_gate", "tokens": 0, "cost_usd": 0}
        usage = payload.get("usageMetadata", {})
        return text, {
            "provider": "gemini-2.5-flash",
            "tokens": usage.get("totalTokenCount", 0),
            "cost_usd": 0,
        }
    except Exception:
        return _fallback_compare_verdict(items), {"provider": "deterministic_fallback", "tokens": 0, "cost_usd": 0}
