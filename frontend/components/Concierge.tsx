"use client";

import { useState } from "react";
import { useEffect } from "react";
import { API_URL } from "@/lib/api";

type Step = { name: string; status: string; detail: Record<string, unknown> };
type Candidate = {
  id: number;
  name?: string;
  neighbourhood?: string;
  price_per_night?: number;
  total_price?: number;
  currency?: string;
  rating_overall?: number;
  review_count?: number;
  rationale?: string;
};
type Insight = {
  property_id: number;
  summary?: string;
  pros?: string[];
  cons?: string[];
  consistency_score?: number;
  citations?: { review_id: number; quote: string }[];
};
type ConciergeFinal = {
  type?: string;
  title?: string;
  summary?: string;
  budget_total?: number | null;
  estimated_total?: number | null;
  currency?: string | null;
  days?: { day: number; title: string; description?: string; property_id?: number | null }[];
  stays?: { title: string; nights?: number; property_id?: number | null; why?: string; swap_strategy?: string }[];
  items?: { property_id: number; why?: string; best_for?: string; caveat?: string | null }[];
  candidates?: Candidate[];
  review_intelligence?: { headline?: string; insights?: Insight[]; warnings?: string[] };
  traveler_notes?: string[];
  usage?: { tokens?: number; cost_usd?: number; providers?: string[]; latency_ms?: number };
};

const CONCIERGE_STORAGE_KEY = "travel_concierge_state_v1";

type StoredConciergeState = {
  message: string;
  steps: Step[];
  final: ConciergeFinal | null;
};

function textValue(value: unknown) {
  if (typeof value === "string") return value;
  if (typeof value === "number") return String(value);
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return null;
}

function findCandidate(final: ConciergeFinal, id?: number | null) {
  if (!id) return undefined;
  return final.candidates?.find((candidate) => candidate.id === id);
}

function price(candidate?: Candidate) {
  if (!candidate) return null;
  const currency = candidate.currency ?? "";
  const nightly = candidate.price_per_night ? `${currency}${Math.round(candidate.price_per_night)}/night` : null;
  const total = candidate.total_price ? `${currency}${Math.round(candidate.total_price)} total` : null;
  return [nightly, total].filter(Boolean).join(" · ");
}

export function Concierge() {
  const [message, setMessage] = useState("Plan a 4-night London trip for a couple: one mid-range stay near the tube and one splurge night somewhere with a river view. Budget £900 total.");
  const [steps, setSteps] = useState<Step[]>([]);
  const [final, setFinal] = useState<ConciergeFinal | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const saved = window.localStorage.getItem(CONCIERGE_STORAGE_KEY);
    if (!saved) return;
    try {
      const parsed = JSON.parse(saved) as StoredConciergeState;
      if (parsed.message) setMessage(parsed.message);
      if (Array.isArray(parsed.steps)) setSteps(parsed.steps);
      if (parsed.final) setFinal(parsed.final);
    } catch {
      window.localStorage.removeItem(CONCIERGE_STORAGE_KEY);
    }
  }, []);

  useEffect(() => {
    if (loading) return;
    window.localStorage.setItem(
      CONCIERGE_STORAGE_KEY,
      JSON.stringify({ message, steps, final })
    );
  }, [final, loading, message, steps]);

  async function ask() {
    setLoading(true);
    setSteps([]);
    setFinal(null);
    setError(null);
    window.localStorage.removeItem(CONCIERGE_STORAGE_KEY);
    try {
      const response = await fetch(`${API_URL}/api/concierge`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ message, session_id: "demo" })
      });
      if (!response.ok || !response.body) throw new Error("Concierge stream failed to start");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      const consumeBlock = (block: string) => {
        const lines = block.split(/\r?\n/);
        const event = lines.find((line) => line.startsWith("event: "))?.slice(7).trim();
        const data = lines
          .filter((line) => line.startsWith("data: "))
          .map((line) => line.slice(6))
          .join("\n");
        if (!event || !data) return;
        const parsed = JSON.parse(data);
        if (event === "request") {
          setSteps((current) => [...current, { name: "Request", status: "started", detail: parsed }]);
        }
        if (event === "step") setSteps((current) => [...current, parsed]);
        if (event === "final") setFinal(parsed);
        if (event === "done") {
          setSteps((current) => [...current, { name: "Trace saved", status: "finished", detail: parsed }]);
        }
      };

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const chunks = buffer.split(/\r?\n\r?\n/);
        buffer = chunks.pop() ?? "";
        chunks.forEach(consumeBlock);
      }
      if (buffer.trim()) consumeBlock(buffer);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Concierge failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <aside className={`fixed bottom-5 right-5 z-20 max-h-[calc(100vh-2rem)] w-[460px] max-w-[calc(100vw-2rem)] overflow-hidden rounded-[2rem] border border-white/80 bg-white/95 shadow-2xl shadow-black/20 backdrop-blur-xl transition duration-300 ${loading ? "ring-4 ring-coral/15" : ""}`}>
      <div className="max-h-[calc(100vh-2rem)] overflow-auto p-4">
      <div className="mb-2 flex items-center justify-between">
        <div>
          <h2 className="font-black">AI concierge</h2>
          {loading ? <div className="text-[11px] font-medium text-black/50">Agents are streaming a grounded answer</div> : null}
        </div>
        <span className={`rounded-full px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-white ${loading ? "animate-pulse bg-coral" : "bg-ink"}`}>4-agent SSE</span>
      </div>
      <textarea
        className="h-24 w-full rounded-2xl border border-black/10 bg-white/80 p-3 text-sm shadow-inner outline-none transition focus:border-coral focus:ring-4 focus:ring-coral/10"
        value={message}
        onChange={(event) => setMessage(event.target.value)}
      />
      <button className="button mt-2 relative overflow-hidden" onClick={ask} disabled={loading}>
        <span className="relative z-10 flex items-center gap-2">
          {loading ? <span className="h-3 w-3 animate-spin rounded-full border-2 border-white/40 border-t-white" /> : null}
          {loading ? "Building your answer..." : "Ask concierge"}
        </span>
        {loading ? <span className="absolute inset-x-0 bottom-0 h-1 animate-pulse bg-white/70" /> : null}
      </button>
      {error ? <div className="mt-2 rounded-2xl bg-red-50 p-3 text-xs text-red-700">{error}</div> : null}
      {loading ? (
        <div className="mt-3 overflow-hidden rounded-3xl border border-coral/15 bg-gradient-to-br from-coral/10 via-white to-sand p-3 shadow-inner">
          <div className="flex items-center gap-3">
            <div className="relative h-10 w-10">
              <span className="absolute inset-0 animate-ping rounded-full bg-coral/25" />
              <span className="absolute inset-1 rounded-full bg-coral/15" />
              <span className="absolute inset-3 rounded-full bg-coral" />
            </div>
            <div>
              <div className="text-sm font-black">Concierge is working</div>
              <div className="text-xs leading-5 text-black/55">Parsing intent, retrieving stays, reading reviews, and composing a recommendation.</div>
            </div>
          </div>
          <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white">
            <div className="h-full w-2/3 animate-pulse rounded-full bg-gradient-to-r from-coral via-fuchsia-500 to-cyan-400" />
          </div>
        </div>
      ) : null}
      <div className="mt-3 space-y-2 text-xs">
        {steps.map((step, index) => (
          <div key={`${step.name}-${index}`} className={`rounded-2xl bg-sand p-2 shadow-sm transition duration-300 hover:-translate-y-0.5 hover:shadow-md ${loading && index === steps.length - 1 ? "ring-2 ring-coral/20" : ""}`}>
            <div className="flex items-center justify-between gap-2">
              <b className="flex items-center gap-2">
                {loading && index === steps.length - 1 ? <span className="h-2 w-2 animate-pulse rounded-full bg-coral" /> : null}
                {step.name}
              </b>
              <span className="rounded-full bg-white px-2 py-0.5 text-[10px] font-semibold">{step.status}</span>
            </div>
            <div className="mt-1 space-y-0.5 text-[11px] text-black/60">
              {Object.entries(step.detail).slice(0, 4).map(([key, value]) => {
                const display = textValue(value);
                return display ? (
                  <div key={key}>
                    <span className="font-semibold">{key.replaceAll("_", " ")}:</span> {display}
                  </div>
                ) : null;
              })}
            </div>
          </div>
        ))}
      </div>
      {final ? (
        <div className="mt-3 space-y-3">
          <div className="rounded-3xl bg-ink p-4 text-white shadow-xl shadow-ink/20">
            <div className="text-[10px] font-bold uppercase tracking-wide text-white/60">{final.type ?? "answer"}</div>
            <h3 className="mt-1 text-lg font-black leading-tight">{final.title ?? "Concierge recommendation"}</h3>
            {final.summary ? <p className="mt-2 text-sm leading-6 text-white/80">{final.summary}</p> : null}
            <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
              {final.budget_total ? <span className="rounded-full bg-white/10 px-2 py-1">Budget {final.currency}{final.budget_total}</span> : null}
              {final.estimated_total ? <span className="rounded-full bg-white/10 px-2 py-1">Estimate {final.currency}{Math.round(final.estimated_total)}</span> : null}
              {final.usage?.tokens ? <span className="rounded-full bg-white/10 px-2 py-1">{final.usage.tokens} tokens</span> : null}
            </div>
          </div>

          {final.stays?.length ? (
            <div className="space-y-2">
              <h4 className="text-sm font-black">Recommended stays</h4>
              {final.stays.map((stay, index) => {
                const candidate = findCandidate(final, stay.property_id);
                return (
                  <div key={`${stay.title}-${index}`} className="rounded-2xl border border-black/10 bg-white p-3 shadow-sm transition hover:-translate-y-0.5 hover:shadow-lg">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="text-sm font-black">{stay.title}</div>
                        {candidate ? <a className="text-xs font-semibold text-coral" href={`/properties/${candidate.id}`}>#{candidate.id} {candidate.name}</a> : null}
                      </div>
                      {stay.nights ? <span className="rounded-full bg-sand px-2 py-1 text-[10px] font-bold">{stay.nights} nights</span> : null}
                    </div>
                    {candidate ? <div className="mt-1 text-xs text-black/60">{candidate.neighbourhood} · {price(candidate)} · {candidate.rating_overall?.toFixed?.(1)} rating</div> : null}
                    {stay.why ? <p className="mt-2 text-xs leading-5">{stay.why}</p> : null}
                    {stay.swap_strategy ? <p className="mt-1 text-[11px] text-black/50">Swap idea: {stay.swap_strategy}</p> : null}
                  </div>
                );
              })}
            </div>
          ) : null}

          {final.items?.length ? (
            <div className="space-y-2">
              <h4 className="text-sm font-black">Top matches</h4>
              {final.items.map((item) => {
                const candidate = findCandidate(final, item.property_id);
                return (
                  <div key={item.property_id} className="rounded-2xl border border-black/10 bg-white p-3 shadow-sm transition hover:-translate-y-0.5 hover:shadow-lg">
                    <a className="text-sm font-black text-coral" href={`/properties/${item.property_id}`}>#{item.property_id} {candidate?.name ?? "Listing"}</a>
                    {candidate ? <div className="mt-1 text-xs text-black/60">{candidate.neighbourhood} · {price(candidate)}</div> : null}
                    {item.best_for ? <div className="mt-2 text-xs font-semibold">{item.best_for}</div> : null}
                    {item.why ? <p className="mt-1 text-xs leading-5">{item.why}</p> : null}
                    {item.caveat ? <p className="mt-1 text-[11px] text-black/50">Trade-off: {item.caveat}</p> : null}
                  </div>
                );
              })}
            </div>
          ) : null}

          {final.days?.length ? (
            <div className="space-y-2">
              <h4 className="text-sm font-black">Day-by-day plan</h4>
              {final.days.map((day) => (
                <div key={`${day.day}-${day.title}`} className="rounded-2xl bg-sand p-3 text-xs">
                  <b>Day {day.day}: {day.title}</b>
                  {day.description ? <p className="mt-1 leading-5 text-black/60">{day.description}</p> : null}
                </div>
              ))}
            </div>
          ) : null}

          {final.review_intelligence?.insights?.length ? (
            <div className="space-y-2">
              <h4 className="text-sm font-black">Review intelligence</h4>
              {final.review_intelligence.insights.slice(0, 3).map((insight) => (
                <div key={insight.property_id} className="rounded-2xl bg-sand p-3 text-xs">
                  <a className="font-black text-coral" href={`/properties/${insight.property_id}`}>Listing #{insight.property_id}</a>
                  {insight.summary ? <p className="mt-1 leading-5">{insight.summary}</p> : null}
                  {insight.citations?.slice(0, 2).map((citation) => (
                    <blockquote key={citation.review_id} className="mt-2 border-l-2 border-coral pl-2 text-[11px] text-black/60">
                      Review #{citation.review_id}: “{citation.quote}”
                    </blockquote>
                  ))}
                </div>
              ))}
            </div>
          ) : null}

          {[...(final.traveler_notes ?? []), ...(final.review_intelligence?.warnings ?? [])].length ? (
            <div className="rounded-2xl bg-amber-50 p-3 text-xs text-amber-900">
              <b>Notes</b>
              {Array.from(new Set([...(final.traveler_notes ?? []), ...(final.review_intelligence?.warnings ?? [])])).map((note, index) => (
                <div key={`${note}-${index}`} className="mt-1">{note}</div>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
      </div>
    </aside>
  );
}
