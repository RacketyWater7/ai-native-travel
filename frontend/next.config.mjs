/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "picsum.photos" },
      { protocol: "https", hostname: "**.airbnb.com" },
      { protocol: "https", hostname: "**.muscache.com" }
    ]
  }
};

export default nextConfig;
