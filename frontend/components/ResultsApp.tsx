"use client";

import { useEffect, useMemo, useState } from "react";
import { API_URL, PropertyCard as Property, searchProperties } from "@/lib/api";
import { PropertyCard } from "@/components/PropertyCard";
import { Concierge } from "@/components/Concierge";

const AMENITIES = ["wifi", "kitchen", "washer", "balcony", "river_view", "free_parking", "gym"];

export function ResultsApp() {
  const [city, setCity] = useState("London");
  const [checkIn, setCheckIn] = useState("2026-06-24");
  const [checkOut, setCheckOut] = useState("2026-06-27");
  const [adults, setAdults] = useState(2);
  const [children, setChildren] = useState(0);
  const [rooms, setRooms] = useState(1);
  const [maxPrice, setMaxPrice] = useState("180");
  const [minRating, setMinRating] = useState("4.3");
  const [roomType, setRoomType] = useState("");
  const [amenities, setAmenities] = useState<string[]>([]);
  const [sort, setSort] = useState("rating");
  const [nearTransit, setNearTransit] = useState(true);
  const [nl, setNl] = useState("a quiet 1-bed in Lisbon under €130 with a balcony for late June");
  const [items, setItems] = useState<Property[]>([]);
  const [total, setTotal] = useState(0);
  const [compare, setCompare] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [compareToast, setCompareToast] = useState<string | null>(null);

  const chips = useMemo(
    () => [
      `city: ${city}`,
      `${checkIn} to ${checkOut}`,
      `${adults + children} guests`,
      `${rooms} room${rooms === 1 ? "" : "s"}`,
      `max price: ${maxPrice}`,
      `rating: ${minRating}+`,
      roomType ? `type: ${roomType}` : "any property type",
      nearTransit ? "near transit" : "any transit",
      ...amenities.map((amenity) => amenity.replaceAll("_", " "))
    ],
    [adults, amenities, checkIn, checkOut, children, city, maxPrice, minRating, nearTransit, roomType, rooms]
  );

  async function runSearch() {
    setLoading(true);
    setError(null);
    try {
      const data = await searchProperties({
        city,
        check_in: checkIn,
        check_out: checkOut,
        adults,
        children,
        rooms,
        max_price: maxPrice,
        min_rating: minRating,
        room_type: roomType,
        amenities,
        near_transit: nearTransit,
        sort,
        page_size: 12
      });
      setItems(data.items);
      setTotal(data.total);
    } catch (err) {
      setItems([]);
      setTotal(0);
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  }

  async function applyNaturalLanguage() {
    const response = await fetch(`${API_URL}/api/intent`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ message: nl, session_id: "demo" })
    });
    const intent = await response.json();
    if (intent.city) setCity(intent.city);
    if (intent.check_in) setCheckIn(intent.check_in);
    if (intent.check_out) setCheckOut(intent.check_out);
    if (intent.adults) setAdults(intent.adults);
    if (intent.children !== undefined) setChildren(intent.children);
    if (intent.rooms) setRooms(intent.rooms);
    if (intent.budget_per_night) setMaxPrice(String(intent.budget_per_night));
    if (intent.hard_constraints?.room_type) setRoomType(intent.hard_constraints.room_type);
    if (intent.soft_preferences?.balcony && !amenities.includes("balcony")) {
      setAmenities((current) => Array.from(new Set([...current, "balcony"])));
    }
    if (intent.hard_constraints?.near_transit !== undefined) {
      setNearTransit(Boolean(intent.hard_constraints.near_transit));
    }
  }

  useEffect(() => {
    runSearch().catch(() => setItems([]));
  }, [adults, amenities, checkIn, checkOut, children, city, maxPrice, minRating, nearTransit, roomType, rooms, sort]);

  function toggleAmenity(amenity: string) {
    setAmenities((current) =>
      current.includes(amenity) ? current.filter((item) => item !== amenity) : [...current, amenity]
    );
  }

  function addToCompare(property: Property) {
    setCompare((current) => Array.from(new Set([...current, property.id])).slice(0, 4));
    setCompareToast(`${property.name} added to compare`);
    window.setTimeout(() => setCompareToast(null), 2200);
  }

  return (
    <main className="min-h-screen px-6 py-6">
      <section className="mx-auto max-w-7xl">
        <div className="mb-6 rounded-[2rem] bg-ink p-8 text-white">
          <p className="text-sm uppercase tracking-[0.2em] text-white/60">AI-native travel discovery</p>
          <h1 className="mt-2 max-w-3xl text-4xl font-black">A real booking surface with an agentic concierge woven through it.</h1>
          <p className="mt-3 max-w-2xl text-white/70">Search Lisbon and London stays, edit filter chips, inspect maps and reviews, save comparisons, and stream grounded agent steps.</p>
        </div>

        <div className="card mb-6 grid gap-4 p-4 lg:grid-cols-[1.1fr_0.9fr]">
          <div>
            <label className="text-xs font-bold uppercase text-black/50">Natural language search</label>
            <div className="mt-2 flex gap-2">
              <input className="w-full rounded-full border border-black/10 px-4 py-3" value={nl} onChange={(event) => setNl(event.target.value)} />
              <button className="button" onClick={applyNaturalLanguage}>Apply</button>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">{chips.map((chip) => <span className="chip" key={chip}>{chip}</span>)}</div>
          </div>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <label className="text-sm">City<select className="mt-1 w-full rounded-2xl border p-2" value={city} onChange={(event) => setCity(event.target.value)}><option>London</option><option>Lisbon</option></select></label>
            <label className="text-sm">Check-in<input type="date" className="mt-1 w-full rounded-2xl border p-2" value={checkIn} onChange={(event) => setCheckIn(event.target.value)} /></label>
            <label className="text-sm">Check-out<input type="date" className="mt-1 w-full rounded-2xl border p-2" value={checkOut} onChange={(event) => setCheckOut(event.target.value)} /></label>
            <label className="text-sm">Max price<input type="range" min="40" max="300" className="mt-3 w-full" value={maxPrice} onChange={(event) => setMaxPrice(event.target.value)} /><span className="text-xs">{maxPrice}</span></label>
            <label className="text-sm">Adults<input type="number" min="1" className="mt-1 w-full rounded-2xl border p-2" value={adults} onChange={(event) => setAdults(Number(event.target.value))} /></label>
            <label className="text-sm">Children<input type="number" min="0" className="mt-1 w-full rounded-2xl border p-2" value={children} onChange={(event) => setChildren(Number(event.target.value))} /></label>
            <label className="text-sm">Rooms<input type="number" min="1" className="mt-1 w-full rounded-2xl border p-2" value={rooms} onChange={(event) => setRooms(Number(event.target.value))} /></label>
            <label className="text-sm">Rating<select className="mt-1 w-full rounded-2xl border p-2" value={minRating} onChange={(event) => setMinRating(event.target.value)}><option value="">Any</option><option value="4">4.0+</option><option value="4.3">4.3+</option><option value="4.6">4.6+</option></select></label>
            <label className="text-sm">Property type<select className="mt-1 w-full rounded-2xl border p-2" value={roomType} onChange={(event) => setRoomType(event.target.value)}><option value="">Any</option><option>Entire home/apt</option><option>Private room</option></select></label>
            <label className="text-sm">Sort<select className="mt-1 w-full rounded-2xl border p-2" value={sort} onChange={(event) => setSort(event.target.value)}><option value="rating">Rating</option><option value="price_asc">Price low-to-high</option><option value="popularity">Popularity</option></select></label>
            <label className="flex items-end gap-2 text-sm"><input type="checkbox" checked={nearTransit} onChange={(event) => setNearTransit(event.target.checked)} /> Near transit</label>
          </div>
          <div className="lg:col-span-2">
            <div className="mb-2 text-xs font-bold uppercase text-black/50">Amenities</div>
            <div className="flex flex-wrap gap-2">
              {AMENITIES.map((amenity) => (
                <button
                  key={amenity}
                  className={`chip ${amenities.includes(amenity) ? "bg-ink text-white" : ""}`}
                  onClick={() => toggleAmenity(amenity)}
                >
                  {amenity.replaceAll("_", " ")}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-2xl font-black">{loading ? "Loading stays..." : `${total} stays`}</h2>
          <a className={`chip transition ${compare.length ? "animate-pulse border-coral bg-white shadow-lg shadow-red-100" : ""}`} href={`/compare?ids=${compare.join(",")}`}>Compare {compare.length}</a>
        </div>
        {compareToast ? (
          <div className="fixed left-1/2 top-5 z-40 -translate-x-1/2 rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white shadow-2xl">
            {compareToast} · open Compare {compare.length}
          </div>
        ) : null}
        {error ? <div className="card mb-4 border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}
        <div className="grid gap-5 lg:grid-cols-[1fr_420px]">
          <div className="grid gap-5 md:grid-cols-2">
            {items.map((property) => (
              <PropertyCard
                key={property.id}
                property={property}
                isCompared={compare.includes(property.id)}
                onCompare={() => addToCompare(property)}
              />
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
