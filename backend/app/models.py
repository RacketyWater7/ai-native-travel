from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class SearchParams(BaseModel):
    city: str | None = None
    check_in: date | None = None
    check_out: date | None = None
    adults: int = 1
    children: int = 0
    rooms: int = 1
    min_price: float | None = None
    max_price: float | None = None
    min_rating: float | None = None
    room_type: str | None = None
    property_type: str | None = None
    amenities: list[str] | None = None
    exclude_neighbourhoods: list[str] | None = None
    near_transit: bool | None = None
    q: str | None = None
    sort: Literal["price_asc", "rating", "popularity", "distance"] = "rating"
    page: int = 1
    page_size: int = 20
    lat: float | None = None
    lng: float | None = None


class PropertyCard(BaseModel):
    id: int
    city: str
    name: str
    neighbourhood: str | None
    latitude: float
    longitude: float
    room_type_normalized: str | None
    accommodates: int | None
    bedrooms: float | None
    price_per_night: float | None
    total_price: float | None = None
    currency: str | None
    amenities_normalized: list[str]
    picture_url: str | None
    near_transit: bool
    nearest_transit: str | None
    rating_overall: float | None
    review_count: int
    price_percentile_in_area: float | None
    ai_review_summary: str | None
    rationale: str | None = None


class SearchResponse(BaseModel):
    items: list[PropertyCard]
    total: int
    page: int
    page_size: int
    weights: dict[str, float] = Field(default_factory=dict)


class Review(BaseModel):
    id: int
    property_id: int
    date: date | None
    reviewer_name: str | None
    language: str | None
    comments: str | None
    sent_cleanliness: int | None
    sent_location: int | None
    sent_value: int | None
    sent_staff: int | None
    sent_noise: int | None


class TravelQuery(BaseModel):
    city: str | None = None
    check_in: date | None = None
    check_out: date | None = None
    nights: int | None = None
    adults: int = 2
    children: int = 0
    rooms: int = 1
    budget_total: float | None = None
    budget_per_night: float | None = None
    currency: str | None = None
    party_type: Literal["couple", "family", "solo", "group"] | None = None
    hard_constraints: dict[str, Any] = Field(default_factory=dict)
    soft_preferences: dict[str, Any] = Field(default_factory=dict)
    sort_hint: str | None = None


class ConciergeRequest(BaseModel):
    message: str
    session_id: str = "anonymous"
    current_filters: dict[str, Any] = Field(default_factory=dict)


class TraceStep(BaseModel):
    name: str
    status: Literal["started", "finished", "degraded", "failed"]
    detail: dict[str, Any] = Field(default_factory=dict)
    latency_ms: int | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
