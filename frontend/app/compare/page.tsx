import { SERVER_API_URL } from "@/lib/api";

export default async function ComparePage({ searchParams }: { searchParams: { ids?: string } }) {
  const ids = searchParams.ids ?? "";
  let data = { items: [], ai_verdict: "Pick 2-4 listings to compare." };
  if (ids) {
    try {
      const response = await fetch(`${SERVER_API_URL}/api/compare?ids=${ids}`, { cache: "no-store" });
      if (response.ok) data = await response.json();
    } catch {
      data = { items: [], ai_verdict: "The API is not reachable from the frontend server right now." };
    }
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-8">
      <a className="chip" href="/">Back to search</a>
      <h1 className="mt-5 text-4xl font-black">Compare stays</h1>
      <div className="card mt-5 p-5">
        <h2 className="font-black">AI verdict</h2>
        <p className="mt-2 text-black/70">{data.ai_verdict}</p>
      </div>
      <div className="mt-5 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {data.items.map((item: any) => (
          <article className="card p-4" key={item.id}>
            <h3 className="font-bold">{item.name}</h3>
            <p className="text-sm text-black/60">{item.neighbourhood}</p>
            <p className="mt-3 text-2xl font-black">{item.currency === "GBP" ? "£" : "€"}{Math.round(item.price_per_night)}</p>
            <p className="text-sm">★ {item.rating_overall} · {item.review_count} reviews</p>
            <p className="mt-3 text-xs text-black/60">{(item.amenities_normalized ?? []).join(", ")}</p>
          </article>
        ))}
      </div>
    </main>
  );
}
