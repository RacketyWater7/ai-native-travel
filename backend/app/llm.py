import json
from typing import Any

import httpx

from app.config import get_settings


COMPARE_PROMPT = """You are the review intelligence agent for an AI-native booking product.

Use only the supplied property rows. Do not invent facts, do not claim live availability beyond the rows,
and mention listing IDs when making a concrete recommendation. Write a crisp verdict a traveler can trust:
best overall, best value, best review confidence, and any trade-off. Keep it under 120 words.

Return plain text only.
"""


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
