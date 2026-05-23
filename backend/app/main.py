from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection
from sse_starlette.sse import EventSourceResponse

from app.agents.orchestrator import concierge_stream, parse_intent_deterministic
from app.config import get_settings
from app.db import get_conn
from app.models import ConciergeRequest, SearchParams
from app.search import search_properties


settings = get_settings()
app = FastAPI(title="AI-Native Travel Discovery API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/search")
async def search(
    conn: Annotated[AsyncConnection, Depends(get_conn)],
    params: Annotated[SearchParams, Depends()],
):
    return await search_properties(conn, params)


@app.post("/api/intent")
async def parse_intent(payload: ConciergeRequest):
    return parse_intent_deterministic(payload.message)


@app.get("/api/properties/{property_id}")
async def property_detail(property_id: int, conn: Annotated[AsyncConnection, Depends(get_conn)]):
    result = await conn.execute(text("SELECT * FROM properties WHERE id = :id"), {"id": property_id})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Property not found")
    return dict(row)


@app.get("/api/properties/{property_id}/reviews")
async def property_reviews(
    property_id: int,
    conn: Annotated[AsyncConnection, Depends(get_conn)],
    language: str | None = None,
    topic: str | None = None,
    limit: int = 50,
):
    where = ["property_id = :property_id"]
    values: dict[str, object] = {"property_id": property_id, "limit": limit}
    if language:
        where.append("language = :language")
        values["language"] = language
    if topic:
        where.append("comments ILIKE :topic")
        values["topic"] = f"%{topic}%"
    result = await conn.execute(
        text(f"SELECT * FROM reviews WHERE {' AND '.join(where)} ORDER BY date DESC LIMIT :limit"),
        values,
    )
    return [dict(row) for row in result.mappings().all()]


@app.get("/api/properties/{property_id}/calendar")
async def property_calendar(property_id: int, conn: Annotated[AsyncConnection, Depends(get_conn)]):
    result = await conn.execute(
        text("SELECT date, available, price FROM calendar WHERE property_id = :id ORDER BY date LIMIT 180"),
        {"id": property_id},
    )
    return [dict(row) for row in result.mappings().all()]


@app.post("/api/wishlist")
async def wishlist(payload: dict, conn: Annotated[AsyncConnection, Depends(get_conn)]):
    await conn.execute(
        text(
            """
            INSERT INTO wishlist (session_id, property_id)
            VALUES (:session_id, :property_id)
            ON CONFLICT (session_id, property_id) DO NOTHING
            """
        ),
        payload,
    )
    return {"ok": True}


@app.get("/api/compare")
async def compare(ids: str, conn: Annotated[AsyncConnection, Depends(get_conn)]):
    id_list = [int(item) for item in ids.split(",") if item.strip()]
    result = await conn.execute(
        text("SELECT * FROM properties WHERE id = ANY(CAST(:ids AS bigint[]))"),
        {"ids": id_list},
    )
    items = [dict(row) for row in result.mappings().all()]
    verdict = "Best value is the lowest price among similarly rated stays; review consistency uses stored aspect sentiment."
    return {"items": items, "ai_verdict": verdict}


@app.post("/api/concierge")
async def concierge(
    payload: ConciergeRequest, conn: Annotated[AsyncConnection, Depends(get_conn)]
) -> EventSourceResponse:
    return EventSourceResponse(concierge_stream(conn, payload))


@app.get("/api/traces/{request_id}")
async def trace(request_id: str, conn: Annotated[AsyncConnection, Depends(get_conn)]):
    result = await conn.execute(
        text("SELECT * FROM agent_traces WHERE request_id = :request_id"),
        {"request_id": request_id},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Trace not found")
    return dict(row)


@app.get("/api/metrics")
async def metrics(conn: Annotated[AsyncConnection, Depends(get_conn)]):
    result = await conn.execute(
        text(
            """
            SELECT count(*) AS traces,
                   coalesce(avg(total_latency_ms), 0) AS avg_latency_ms,
                   coalesce(sum(total_cost_usd), 0) AS total_cost_usd
            FROM agent_traces
            """
        )
    )
    return dict(result.mappings().one())


@app.post("/api/batch/compare")
async def batch_compare(payload: dict, conn: Annotated[AsyncConnection, Depends(get_conn)]):
    groups = payload.get("groups", [])
    out = []
    for ids in groups[:10]:
        result = await conn.execute(
            text("SELECT id, name, rating_overall FROM properties WHERE id = ANY(CAST(:ids AS bigint[]))"),
            {"ids": ids},
        )
        out.append({"ids": ids, "items": [dict(row) for row in result.mappings().all()]})
    return {"groups": out}
