export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type PropertyCard = {
  id: number;
  city: string;
  name: string;
  neighbourhood: string | null;
  latitude: number;
  longitude: number;
  room_type_normalized: string | null;
  accommodates: number | null;
  bedrooms: number | null;
  price_per_night: number | null;
  total_price: number | null;
  currency: string | null;
  amenities_normalized: string[];
  picture_url: string | null;
  near_transit: boolean;
  nearest_transit: string | null;
  rating_overall: number | null;
  review_count: number;
  price_percentile_in_area: number | null;
  ai_review_summary: string | null;
  rationale: string | null;
};

export type SearchResponse = {
  items: PropertyCard[];
  total: number;
  page: number;
  page_size: number;
  weights: Record<string, number>;
};

export async function searchProperties(params: Record<string, string | number | boolean | undefined>) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") query.set(key, String(value));
  });
  const response = await fetch(`${API_URL}/api/search?${query.toString()}`, { cache: "no-store" });
  if (!response.ok) throw new Error("Search failed");
  return (await response.json()) as SearchResponse;
}
