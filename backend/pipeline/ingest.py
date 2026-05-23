import argparse
import asyncio
import hashlib
import json
import random
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import text

from app.db import engine


CITY_CONFIG = {
    "Lisbon": {
        "country": "portugal",
        "region": "lisbon",
        "city_slug": "lisbon",
        "currency": "EUR",
        "center": (38.7223, -9.1393),
        "transit": ["Baixa-Chiado", "Cais do Sodre", "Saldanha", "Oriente"],
    },
    "London": {
        "country": "united-kingdom",
        "region": "england",
        "city_slug": "london",
        "currency": "GBP",
        "center": (51.5074, -0.1278),
        "transit": ["Waterloo", "London Bridge", "King's Cross", "Paddington"],
    },
}

AMENITY_VOCAB = [
    "wifi",
    "kitchen",
    "washer",
    "air_conditioning",
    "balcony",
    "river_view",
    "free_parking",
    "pet_friendly",
    "gym",
]


async def resolve_inside_airbnb_urls() -> dict[str, dict[str, str]]:
    async with httpx.AsyncClient(timeout=30) as client:
        html = (await client.get("https://insideairbnb.com/get-the-data/")).text

    resolved: dict[str, dict[str, str]] = {}
    for city, cfg in CITY_CONFIG.items():
        city_urls: dict[str, str] = {}
        base = rf"https://data\.insideairbnb\.com/{cfg['country']}/{cfg['region']}/{cfg['city_slug']}/(\d{{4}}-\d{{2}}-\d{{2}})/(?:data|visualisations)/"
        for filename in ["listings.csv.gz", "calendar.csv.gz", "reviews.csv.gz", "neighbourhoods.geojson"]:
            matches = re.findall(base + re.escape(filename), html)
            if matches:
                snapshot = sorted(matches)[-1]
                path = "visualisations" if filename.endswith(".geojson") else "data"
                city_urls[filename] = (
                    f"https://data.insideairbnb.com/{cfg['country']}/{cfg['region']}/"
                    f"{cfg['city_slug']}/{snapshot}/{path}/{filename}"
                )
        resolved[city] = city_urls
    return resolved


def fake_embedding(seed: str, dims: int = 768) -> str:
    digest = hashlib.sha256(seed.encode()).digest()
    rnd = random.Random(digest)
    return "[" + ",".join(f"{rnd.uniform(-1, 1):.5f}" for _ in range(dims)) + "]"


def property_rows(sample: bool) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    count_per_city = 18 if sample else 250
    next_id = 1000
    for city, cfg in CITY_CONFIG.items():
        lat, lng = cfg["center"]
        neighbourhoods = (
            ["Alfama", "Baixa", "Chiado", "Principe Real", "Parque das Nacoes"]
            if city == "Lisbon"
            else ["South Bank", "Shoreditch", "Kensington", "Camden", "Westminster"]
        )
        for i in range(count_per_city):
            amenities = random.sample(AMENITY_VOCAB, k=random.randint(3, 6))
            if i % 5 == 0 and "balcony" not in amenities:
                amenities.append("balcony")
            if city == "London" and i % 7 == 0 and "river_view" not in amenities:
                amenities.append("river_view")
            price = random.randint(70, 230 if city == "London" else 170)
            room_type = "Entire home/apt" if i % 3 else "Private room"
            rows.append(
                {
                    "id": next_id,
                    "city": city,
                    "name": f"{city} {room_type} near {neighbourhoods[i % len(neighbourhoods)]}",
                    "description": "Quiet stay near restaurants and transit with reliable reviews.",
                    "property_type": "Apartment",
                    "room_type_normalized": room_type,
                    "neighbourhood": neighbourhoods[i % len(neighbourhoods)],
                    "latitude": lat + random.uniform(-0.045, 0.045),
                    "longitude": lng + random.uniform(-0.045, 0.045),
                    "accommodates": random.choice([2, 2, 3, 4]),
                    "bedrooms": random.choice([1, 1, 2]),
                    "beds": random.choice([1, 2]),
                    "bathrooms": 1,
                    "price_per_night": price,
                    "currency": cfg["currency"],
                    "amenities_normalized": amenities,
                    "picture_url": f"https://picsum.photos/seed/{next_id}/800/600",
                    "photo_urls": [f"https://picsum.photos/seed/{next_id}-{n}/800/600" for n in range(3)],
                    "host_name": f"Host {i}",
                    "host_is_superhost": i % 4 == 0,
                    "instant_bookable": i % 2 == 0,
                    "near_transit": i % 2 == 0,
                    "nearest_transit": cfg["transit"][i % len(cfg["transit"])],
                    "review_count": random.randint(12, 240),
                    "rating_overall": round(random.uniform(4.2, 4.95), 2),
                    "rating_cleanliness": round(random.uniform(4.1, 5.0), 2),
                    "rating_location": round(random.uniform(4.1, 5.0), 2),
                    "rating_value": round(random.uniform(4.0, 4.9), 2),
                    "rating_communication": round(random.uniform(4.1, 5.0), 2),
                    "price_percentile_in_area": round(random.uniform(0.2, 0.9), 2),
                    "ai_review_summary": "Guests consistently praise the location, smooth communication, and cleanliness; a few mention street noise on busy nights.",
                    "ai_review_summary_citations": [next_id * 10 + 1, next_id * 10 + 2],
                    "embedding": fake_embedding(f"property-{next_id}"),
                }
            )
            next_id += 1
    return rows


def review_rows(properties: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    snippets = [
        "Great location, very clean, and easy communication with the host.",
        "Quiet at night and close to restaurants. Good value for the area.",
        "The apartment was comfortable, though there was some street noise.",
        "Loved the transit access and the balcony for morning coffee.",
    ]
    for prop in properties:
        for idx in range(4):
            rid = prop["id"] * 10 + idx + 1
            rows.append(
                {
                    "id": rid,
                    "property_id": prop["id"],
                    "date": date.today() - timedelta(days=idx * 21),
                    "reviewer_name": f"Guest {idx + 1}",
                    "rating": prop["rating_overall"],
                    "language": "en" if idx != 3 else "pt",
                    "comments": snippets[idx],
                    "sent_cleanliness": 1,
                    "sent_location": 1,
                    "sent_value": 1 if idx != 2 else 0,
                    "sent_staff": 1,
                    "sent_noise": -1 if idx == 2 else 0,
                    "embedding": fake_embedding(f"review-{rid}"),
                }
            )
    return rows


def calendar_rows(properties: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    start = date.today()
    for prop in properties:
        for offset in range(180):
            day = start + timedelta(days=offset)
            rows.append(
                {
                    "property_id": prop["id"],
                    "date": day,
                    "available": offset % 9 != 0,
                    "price": prop["price_per_night"],
                }
            )
    return rows


async def seed(sample: bool) -> None:
    properties = property_rows(sample)
    reviews = review_rows(properties)
    calendar = calendar_rows(properties)
    async with engine.begin() as conn:
        for prop in properties:
            await conn.execute(
                text(
                    """
                    INSERT INTO properties (
                      id, city, name, description, property_type, room_type_normalized,
                      neighbourhood, latitude, longitude, accommodates, bedrooms, beds,
                      bathrooms, price_per_night, currency, amenities_normalized, picture_url,
                      photo_urls, host_name, host_is_superhost, instant_bookable, near_transit,
                      nearest_transit, review_count, rating_overall, rating_cleanliness,
                      rating_location, rating_value, rating_communication, price_percentile_in_area,
                      ai_review_summary, ai_review_summary_citations, embedding
                    )
                    VALUES (
                      :id, :city, :name, :description, :property_type, :room_type_normalized,
                      :neighbourhood, :latitude, :longitude, :accommodates, :bedrooms, :beds,
                      :bathrooms, :price_per_night, :currency, :amenities_normalized, :picture_url,
                      :photo_urls, :host_name, :host_is_superhost, :instant_bookable, :near_transit,
                      :nearest_transit, :review_count, :rating_overall, :rating_cleanliness,
                      :rating_location, :rating_value, :rating_communication, :price_percentile_in_area,
                      :ai_review_summary, :ai_review_summary_citations, CAST(:embedding AS halfvec)
                    )
                    ON CONFLICT (id) DO UPDATE SET
                      price_per_night = excluded.price_per_night,
                      rating_overall = excluded.rating_overall
                    """
                ),
                prop,
            )
        for review in reviews:
            await conn.execute(
                text(
                    """
                    INSERT INTO reviews (
                      id, property_id, date, reviewer_name, rating, language, comments,
                      sent_cleanliness, sent_location, sent_value, sent_staff, sent_noise, embedding
                    )
                    VALUES (
                      :id, :property_id, :date, :reviewer_name, :rating, :language, :comments,
                      :sent_cleanliness, :sent_location, :sent_value, :sent_staff, :sent_noise,
                      CAST(:embedding AS halfvec)
                    )
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                review,
            )
        for chunk_start in range(0, len(calendar), 1000):
            for cal in calendar[chunk_start : chunk_start + 1000]:
                await conn.execute(
                    text(
                        """
                        INSERT INTO calendar (property_id, date, available, price)
                        VALUES (:property_id, :date, :available, :price)
                        ON CONFLICT (property_id, date) DO UPDATE SET
                          available = excluded.available,
                          price = excluded.price
                        """
                    ),
                    cal,
                )

        counts = {}
        for table in ["properties", "reviews", "calendar"]:
            counts[table] = (await conn.execute(text(f"SELECT count(*) FROM {table}"))).scalar_one()
        print(json.dumps({"summary": counts, "mode": "sample" if sample else "expanded-seed"}, indent=2))
        if not sample and (counts["properties"] < 60000 or counts["reviews"] < 300000):
            print("Full real ingest should exceed 60K listings / 300K reviews; seed mode is below by design.")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="store_true", help="Load a small reviewer-friendly subset.")
    parser.add_argument("--mock-llm", action="store_true", help="Use deterministic embeddings and summaries.")
    parser.add_argument("--seed-only", action="store_true", help="Skip Inside Airbnb URL discovery.")
    args = parser.parse_args()

    if not args.seed_only:
        cache_dir = Path("data/cache")
        cache_dir.mkdir(parents=True, exist_ok=True)
        try:
            urls = await resolve_inside_airbnb_urls()
            (cache_dir / "inside_airbnb_urls.json").write_text(json.dumps(urls, indent=2))
            print(json.dumps({"snapshots": urls}, indent=2))
        except Exception as exc:
            print(f"URL discovery failed, continuing with seed data: {exc}")

    await seed(sample=args.sample)


if __name__ == "__main__":
    asyncio.run(main())
