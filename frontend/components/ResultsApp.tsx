"use client";

import { useEffect, useMemo, useState } from "react";
import { API_URL, PropertyCard as Property, searchProperties } from "@/lib/api";
import { PropertyCard } from "@/components/PropertyCard";
import { Concierge } from "@/components/Concierge";

export function ResultsApp() {
  const [city, setCity] = useState("London");
  const [maxPrice, setMaxPrice] = useState("180");
  const [nearTransit, setNearTransit] = useState(true);
  const [nl, setNl] = useState("a quiet 1-bed in Lisbon under €130 with a balcony for late June");
  const [items, setItems] = useState<Property[]>([]);
  const [total, setTotal] = useState(0);
  const [compare, setCompare] = useState<number[]>([]);

  const chips = useMemo(() => [`city: ${city}`, `max price: ${maxPrice}`, nearTransit ? "near transit" : "any transit"], [city, maxPrice, nearTransit]);

  async function runSearch() {
    const data = await searchProperties({ city, max_price: maxPrice, near_transit: nearTransit, page_size: 12 });
    setItems(data.items);
    setTotal(data.total);
  }

  async function applyNaturalLanguage() {
    const response = await fetch(`${API_URL}/api/intent`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ message: nl, session_id: "demo" })
    });
    const intent = await response.json();
    if (intent.city) setCity(intent.city);
    if (intent.budget_per_night) setMaxPrice(String(intent.budget_per_night));
    setNearTransit(Boolean(intent.hard_constraints?.near_transit));
  }

  useEffect(() => {
    runSearch().catch(() => setItems([]));
  }, [city, maxPrice, nearTransit]);

  return (
    <main className="min-h-screen px-6 py-6">
      <section className="mx-auto max-w-7xl">
        <div className="mb-6 rounded-[2rem] bg-ink p-8 text-white">
          <p className="text-sm uppercase tracking-[0.2em] text-white/60">AI-native travel discovery</p>
          <h1 className="mt-2 max-w-3xl text-4xl font-black">A real booking surface with an agentic concierge woven through it.</h1>
          <p className="mt-3 max-w-2xl text-white/70">Search Lisbon and London stays, edit filter chips, inspect maps and reviews, save comparisons, and stream grounded agent steps.</p>
        </div>

        <div className="card mb-6 grid gap-4 p-4 lg:grid-cols-[1.2fr_0.8fr]">
          <div>
            <label className="text-xs font-bold uppercase text-black/50">Natural language search</label>
            <div className="mt-2 flex gap-2">
              <input className="w-full rounded-full border border-black/10 px-4 py-3" value={nl} onChange={(event) => setNl(event.target.value)} />
              <button className="button" onClick={applyNaturalLanguage}>Apply</button>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">{chips.map((chip) => <span className="chip" key={chip}>{chip}</span>)}</div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <label className="text-sm">City<select className="mt-1 w-full rounded-2xl border p-2" value={city} onChange={(event) => setCity(event.target.value)}><option>London</option><option>Lisbon</option></select></label>
            <label className="text-sm">Max price<input className="mt-1 w-full rounded-2xl border p-2" value={maxPrice} onChange={(event) => setMaxPrice(event.target.value)} /></label>
            <label className="flex items-end gap-2 text-sm"><input type="checkbox" checked={nearTransit} onChange={(event) => setNearTransit(event.target.checked)} /> Near transit</label>
          </div>
        </div>

        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-2xl font-black">{total} stays</h2>
          <a className="chip" href={`/compare?ids=${compare.join(",")}`}>Compare {compare.length}</a>
        </div>
        <div className="grid gap-5 lg:grid-cols-[1fr_420px]">
          <div className="grid gap-5 md:grid-cols-2">
            {items.map((property) => (
              <PropertyCard key={property.id} property={property} onCompare={(id) => setCompare((current) => Array.from(new Set([...current, id])).slice(0, 4))} />
            ))}
          </div>
          <div className="sticky top-5 h-[720px] rounded-3xl bg-[#dbe7df] p-4">
            <h3 className="font-black">Map view</h3>
            <p className="text-sm text-black/60">MapLibre/CARTO tiles are configured for production; seed demo renders synchronized price markers.</p>
            <div className="mt-4 grid gap-2">
              {items.slice(0, 10).map((property) => (
                <a key={property.id} href={`/properties/${property.id}`} className="rounded-2xl bg-white px-3 py-2 text-sm shadow-sm">
                  {property.currency === "GBP" ? "£" : "€"}{Math.round(property.price_per_night ?? 0)} · {property.neighbourhood}
                </a>
              ))}
            </div>
          </div>
        </div>
      </section>
      <Concierge />
    </main>
  );
}
