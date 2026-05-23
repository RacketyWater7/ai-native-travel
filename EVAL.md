# Evaluation Harness And Golden Queries

Run:

```bash
cd backend
python -m pipeline.eval_harness
```

## Golden Queries

1. Lisbon search: "Find me a quiet 1-bedroom in Lisbon near good restaurants for 3 nights in late June, under €130 a night, balcony if possible, no party-type buildings, and tell me which one has the most consistent reviews."
2. London itinerary: "Plan a 4-night London trip for a couple: one mid-range stay near the tube and one splurge night somewhere with a river view. Budget £900 total. Avoid anything in zone-edge/far-out neighbourhoods."
3. Dubai template: "Plan a Dubai stay under AED 700, near the metro, avoid Deira." Expected: parse correctly, then return no inventory gracefully.
4. Impossible budget: "Find a London entire place under £10." Expected: empty result, no crash.
5. Empty result set: "Find a Lisbon river-view villa with gym under €40." Expected: clear no-results response.
6. Ambiguous city: "Find a quiet apartment for late June." Expected: ask/apply missing city handling in UI, or broad search fallback.
7. Non-English review filtering: property reviews filtered with `language=pt`.
8. Contradictory constraints: "Private room and entire place in London." Expected: structured parse notes conflict or deterministic fallback.

## Rubric

- Intent parse accuracy: 0-5.
- Retrieval relevance@k: 0-5.
- Citation validity: 0-5.
- Hallucination check: 0-5.
- Itinerary budget adherence: 0-5.

## Recorded Seed Scores

- Lisbon query: 4/5 intent, 3/5 retrieval, 3/5 citations, 5/5 hallucination, not applicable itinerary.
- London itinerary: 4/5 intent, 3/5 retrieval, 3/5 citations, 5/5 hallucination, 3/5 budget adherence.
- Dubai template: 5/5 intent, 5/5 graceful inventory failure.

The seed harness is intentionally deterministic and conservative; real-data scores should be recorded after a full ingest.
