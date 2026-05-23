import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AI Native Travel Discovery",
  description: "Booking product surface with a streaming AI concierge"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
