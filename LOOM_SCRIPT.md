# Five-Minute Loom Shot List

1. Architecture overview: show the README Mermaid diagram and explain ingestion, Postgres/PostGIS/pgvector, FastAPI, SSE agents, Redis, and Next.js.
2. Traditional search: open the app, choose London, set a price cap, toggle near transit, and open a listing card.
3. Natural-language search: type `a quiet 1-bed in Lisbon under €130 with a balcony for late June`, click Apply, and show visible filter chips changing.
4. Property detail: show the gallery, AI review summary, citation IDs, reviews, price breakdown, and mocked Reserve confirmation.
5. Concierge: run the London itinerary golden query and show Intent, Retrieval, and Itinerary steps streaming.
6. Graceful failure: ask for Dubai inventory and show the parsed unsupported city response rather than a crash.
7. Close with setup: point to `SETUP.md`, `EVAL.md`, and the one-command local run.
