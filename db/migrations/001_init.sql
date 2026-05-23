CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS properties (
  id BIGINT PRIMARY KEY,
  city TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'inside_airbnb',
  name TEXT NOT NULL,
  description TEXT,
  property_type TEXT,
  room_type_normalized TEXT,
  neighbourhood TEXT,
  latitude DOUBLE PRECISION NOT NULL,
  longitude DOUBLE PRECISION NOT NULL,
  geog GEOGRAPHY(Point, 4326) GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography) STORED,
  accommodates INTEGER,
  bedrooms NUMERIC,
  beds NUMERIC,
  bathrooms NUMERIC,
  price_per_night NUMERIC,
  currency TEXT CHECK (currency IN ('EUR', 'GBP')),
  amenities_normalized TEXT[] DEFAULT '{}',
  picture_url TEXT,
  photo_urls TEXT[] DEFAULT '{}',
  host_name TEXT,
  host_is_superhost BOOLEAN DEFAULT FALSE,
  instant_bookable BOOLEAN DEFAULT FALSE,
  near_transit BOOLEAN DEFAULT FALSE,
  nearest_transit TEXT,
  review_count INTEGER DEFAULT 0,
  rating_overall NUMERIC,
  rating_cleanliness NUMERIC,
  rating_location NUMERIC,
  rating_value NUMERIC,
  rating_communication NUMERIC,
  price_percentile_in_area NUMERIC,
  ai_review_summary TEXT,
  ai_review_summary_citations BIGINT[] DEFAULT '{}',
  embedding halfvec(768),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS reviews (
  id BIGINT PRIMARY KEY,
  property_id BIGINT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  date DATE,
  reviewer_name TEXT,
  rating NUMERIC,
  language TEXT DEFAULT 'en',
  comments TEXT,
  sent_cleanliness SMALLINT,
  sent_location SMALLINT,
  sent_value SMALLINT,
  sent_staff SMALLINT,
  sent_noise SMALLINT,
  embedding halfvec(768)
);

CREATE TABLE IF NOT EXISTS calendar (
  property_id BIGINT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  date DATE NOT NULL,
  available BOOLEAN NOT NULL,
  price NUMERIC,
  PRIMARY KEY (property_id, date)
);

CREATE TABLE IF NOT EXISTS neighbourhoods (
  city TEXT NOT NULL,
  name TEXT NOT NULL,
  geojson JSONB,
  centroid GEOGRAPHY(Point, 4326),
  PRIMARY KEY (city, name)
);

CREATE TABLE IF NOT EXISTS wishlist (
  id BIGSERIAL PRIMARY KEY,
  session_id TEXT NOT NULL,
  property_id BIGINT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (session_id, property_id)
);

CREATE TABLE IF NOT EXISTS agent_traces (
  id BIGSERIAL PRIMARY KEY,
  request_id UUID NOT NULL UNIQUE,
  session_id TEXT,
  query TEXT NOT NULL,
  steps JSONB NOT NULL DEFAULT '[]'::jsonb,
  total_tokens INTEGER DEFAULT 0,
  total_cost_usd NUMERIC DEFAULT 0,
  total_latency_ms INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_properties_geog ON properties USING gist (geog);
CREATE INDEX IF NOT EXISTS idx_properties_city_price ON properties (city, price_per_night);
CREATE INDEX IF NOT EXISTS idx_properties_city_neighbourhood ON properties (city, neighbourhood);
CREATE INDEX IF NOT EXISTS idx_properties_amenities ON properties USING gin (amenities_normalized);
CREATE INDEX IF NOT EXISTS idx_properties_embedding ON properties USING hnsw (embedding halfvec_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_reviews_property ON reviews (property_id);
CREATE INDEX IF NOT EXISTS idx_reviews_language ON reviews (language);
CREATE INDEX IF NOT EXISTS idx_reviews_embedding ON reviews USING hnsw (embedding halfvec_cosine_ops) WHERE embedding IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_calendar_availability ON calendar (property_id, date, available);
