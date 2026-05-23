import { API_URL } from "@/lib/api";

async function getProperty(id: string) {
  const response = await fetch(`${API_URL}/api/properties/${id}`, { cache: "no-store" });
  if (!response.ok) return null;
  return response.json();
}

async function getReviews(id: string) {
  const response = await fetch(`${API_URL}/api/properties/${id}/reviews?limit=12`, { cache: "no-store" });
  if (!response.ok) return [];
  return response.json();
}

export default async function PropertyPage({ params }: { params: { id: string } }) {
  const property = await getProperty(params.id);
  const reviews = await getReviews(params.id);
  if (!property) return <main className="p-8">Property not found.</main>;
  const symbol = property.currency === "GBP" ? "£" : "€";

  return (
    <main className="mx-auto max-w-6xl px-6 py-8">
      <a className="chip" href="/">Back to search</a>
      <div className="mt-5 grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <section>
          <img className="h-[420px] w-full rounded-[2rem] object-cover" src={property.picture_url} alt="" />
          <h1 className="mt-6 text-4xl font-black">{property.name}</h1>
          <p className="mt-2 text-black/60">{property.city} · {property.neighbourhood} · {property.room_type_normalized}</p>
          <div className="card mt-6 p-5">
            <h2 className="font-black">AI review summary</h2>
            <p className="mt-2 text-black/70">{property.ai_review_summary}</p>
            <p className="mt-2 text-xs text-black/50">Citations: {(property.ai_review_summary_citations ?? []).join(", ")}</p>
          </div>
          <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4">
            {(property.amenities_normalized ?? []).map((amenity: string) => (
              <span key={amenity} className="card p-3 text-sm">{amenity.replaceAll("_", " ")}</span>
            ))}
          </div>
          <section className="mt-8">
            <h2 className="text-2xl font-black">Reviews</h2>
            <div className="mt-3 grid gap-3">
              {reviews.map((review: any) => (
                <article key={review.id} id={`review-${review.id}`} className="card p-4">
                  <div className="text-sm font-bold">{review.reviewer_name} · #{review.id}</div>
                  <p className="mt-1 text-sm text-black/70">{review.comments}</p>
                </article>
              ))}
            </div>
          </section>
        </section>
        <aside className="card h-fit p-5">
          <div className="text-3xl font-black">{symbol}{Math.round(property.price_per_night)} <span className="text-sm font-medium">night</span></div>
          <div className="mt-4 rounded-2xl bg-sand p-4 text-sm">
            <div className="flex justify-between"><span>3 nights</span><b>{symbol}{Math.round(property.price_per_night * 3)}</b></div>
            <div className="flex justify-between"><span>Mock taxes and fees</span><b>{symbol}42</b></div>
            <div className="mt-2 flex justify-between border-t pt-2 text-base"><span>Total</span><b>{symbol}{Math.round(property.price_per_night * 3 + 42)}</b></div>
          </div>
          <a href={`/reserve/${property.id}`} className="button mt-4 block text-center">Reserve</a>
          <div className="mt-5 rounded-2xl bg-[#dbe7df] p-4 text-sm">Embedded map placeholder: {property.nearest_transit ? `near ${property.nearest_transit}` : property.neighbourhood}</div>
        </aside>
      </div>
    </main>
  );
}
