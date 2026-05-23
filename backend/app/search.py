from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.models import PropertyCard, SearchParams, SearchResponse


def _nights(check_in: date | None, check_out: date | None) -> int:
    if not check_in or not check_out:
        return 1
    return max((check_out - check_in).days, 1)


def _rationale(row: dict[str, Any]) -> str:
    matches: list[str] = []
    if row.get("near_transit"):
        matches.append(f"near {row.get('nearest_transit') or 'transit'}")
    if row.get("rating_overall"):
        matches.append(f"{float(row['rating_overall']):.1f} rating")
    if row.get("price_per_night"):
        matches.append(f"{row.get('currency')}{float(row['price_per_night']):.0f}/night")
    if row.get("price_percentile_in_area") is not None:
        pct = int(float(row["price_percentile_in_area"]) * 100)
        matches.append(f"cheaper than {pct}% nearby")
    return "Matches: " + ", ".join(matches[:4]) if matches else "Matches core filters"


async def search_properties(conn: AsyncConnection, params: SearchParams) -> SearchResponse:
    where = ["1=1"]
    values: dict[str, Any] = {
        "limit": params.page_size,
        "offset": max(params.page - 1, 0) * params.page_size,
    }

    if params.city:
        where.append("lower(city) = lower(:city)")
        values["city"] = params.city
    guest_count = max((params.adults or 0) + (params.children or 0), 1)
    where.append("(accommodates IS NULL OR accommodates >= :guest_count)")
    values["guest_count"] = guest_count
    if params.rooms and params.rooms > 1:
        where.append("(bedrooms IS NULL OR bedrooms >= :rooms)")
        values["rooms"] = params.rooms
    if params.min_price is not None:
        where.append("price_per_night >= :min_price")
        values["min_price"] = params.min_price
    if params.max_price is not None:
        where.append("price_per_night <= :max_price")
        values["max_price"] = params.max_price
    if params.min_rating is not None:
        where.append("rating_overall >= :min_rating")
        values["min_rating"] = params.min_rating
    if params.room_type:
        where.append("lower(room_type_normalized) = lower(:room_type)")
        values["room_type"] = params.room_type
    if params.property_type:
        where.append("property_type ILIKE :property_type")
        values["property_type"] = f"%{params.property_type}%"
    if params.amenities:
        where.append("amenities_normalized @> CAST(:amenities AS text[])")
        values["amenities"] = params.amenities
    if params.exclude_neighbourhoods:
        where.append("NOT (lower(neighbourhood) = ANY(CAST(:exclude_neighbourhoods AS text[])))")
        values["exclude_neighbourhoods"] = [n.lower() for n in params.exclude_neighbourhoods]
    if params.near_transit is not None:
        where.append("near_transit = :near_transit")
        values["near_transit"] = params.near_transit
    if params.q:
        where.append("(name ILIKE :q OR description ILIKE :q OR neighbourhood ILIKE :q)")
        values["q"] = f"%{params.q}%"
    if params.check_in and params.check_out:
        values["check_in"] = params.check_in
        values["check_out"] = params.check_out
        values["required_nights"] = _nights(params.check_in, params.check_out)
        where.append(
            """
            (
              SELECT count(*)
              FROM calendar c
              WHERE c.property_id = properties.id
                AND c.date >= :check_in
                AND c.date < :check_out
                AND c.available = true
            ) = :required_nights
            """
        )

    order = {
        "price_asc": "price_per_night ASC NULLS LAST",
        "rating": "rating_overall DESC NULLS LAST, review_count DESC",
        "popularity": "review_count DESC, rating_overall DESC NULLS LAST",
        "distance": "distance_m ASC NULLS LAST",
    }[params.sort]

    distance_select = "NULL::double precision AS distance_m"
    if params.sort == "distance" and params.lat is not None and params.lng is not None:
        distance_select = (
            "ST_Distance(geog, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography) AS distance_m"
        )
        values["lat"] = params.lat
        values["lng"] = params.lng

    where_sql = " AND ".join(where)
    count_result = await conn.execute(text(f"SELECT count(*) FROM properties WHERE {where_sql}"), values)
    total = int(count_result.scalar_one())

    result = await conn.execute(
        text(
            f"""
            SELECT id, city, name, neighbourhood, latitude, longitude, room_type_normalized,
                   accommodates, bedrooms, price_per_night, currency, amenities_normalized,
                   picture_url, near_transit, nearest_transit, rating_overall, review_count,
                   price_percentile_in_area, ai_review_summary, {distance_select}
            FROM properties
            WHERE {where_sql}
            ORDER BY {order}
            LIMIT :limit OFFSET :offset
            """
        ),
        values,
    )
    nights = _nights(params.check_in, params.check_out)
    items = []
    for row in result.mappings().all():
        data = dict(row)
        data["amenities_normalized"] = list(data.get("amenities_normalized") or [])
        data["total_price"] = (
            float(data["price_per_night"]) * nights if data.get("price_per_night") is not None else None
        )
        data["rationale"] = _rationale(data)
        items.append(PropertyCard(**data))

    return SearchResponse(
        items=items,
        total=total,
        page=params.page,
        page_size=params.page_size,
        weights={"structured": 0.65, "semantic": 0.25, "geo": 0.10},
    )
