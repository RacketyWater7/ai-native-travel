import type { PropertyCard as Property } from "@/lib/api";

const money = (currency: string | null, value: number | null) => {
  if (value == null) return "Price pending";
  const symbol = currency === "GBP" ? "£" : "€";
  return `${symbol}${Math.round(value)}`;
};

export function PropertyCard({ property, onCompare }: { property: Property; onCompare?: (id: number) => void }) {
  const priceRank =
    property.price_percentile_in_area == null
      ? null
      : `Cheaper than ${Math.round(property.price_percentile_in_area * 100)}% nearby`;

  return (
    <article className="card overflow-hidden">
      <img
        className="h-48 w-full object-cover"
        src={property.picture_url ?? `https://picsum.photos/seed/${property.id}/800/600`}
        alt=""
      />
      <div className="space-y-3 p-4">
        <div>
          <div className="text-xs uppercase tracking-wide text-black/50">{property.city} · {property.neighbourhood}</div>
          <h3 className="text-lg font-bold">{property.name}</h3>
        </div>
        <div className="flex flex-wrap gap-2">
          {property.amenities_normalized.slice(0, 4).map((amenity) => (
            <span key={amenity} className="chip">{amenity.replaceAll("_", " ")}</span>
          ))}
          {property.near_transit ? <span className="chip">near {property.nearest_transit}</span> : null}
        </div>
        <p className="text-sm text-black/65">{property.rationale}</p>
        <div className="flex items-end justify-between">
          <div>
            <div className="text-2xl font-black">{money(property.currency, property.price_per_night)} <span className="text-sm font-medium">/ night</span></div>
            <div className="text-xs text-black/60">{money(property.currency, property.total_price)} total · {priceRank}</div>
          </div>
          <div className="text-right text-sm">
            <div className="font-bold">★ {property.rating_overall?.toFixed(2) ?? "New"}</div>
            <div className="text-black/50">{property.review_count} reviews</div>
          </div>
        </div>
        <div className="flex gap-2">
          <a className="button" href={`/properties/${property.id}`}>View stay</a>
          <button className="chip" onClick={() => onCompare?.(property.id)}>Compare</button>
        </div>
      </div>
    </article>
  );
}
