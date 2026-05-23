"use client";

import { useEffect, useState } from "react";

export function NavigationLoader() {
  const [active, setActive] = useState(false);

  useEffect(() => {
    let timeout: ReturnType<typeof setTimeout> | undefined;
    const start = (event: MouseEvent) => {
      const target = event.target as HTMLElement | null;
      const anchor = target?.closest("a");
      if (!anchor) return;
      const href = anchor.getAttribute("href");
      if (!href || href.startsWith("#") || href.startsWith("http")) return;
      setActive(true);
      if (timeout) clearTimeout(timeout);
      timeout = setTimeout(() => setActive(false), 1800);
    };
    const stop = () => {
      if (timeout) clearTimeout(timeout);
      timeout = setTimeout(() => setActive(false), 250);
    };
    document.addEventListener("click", start);
    window.addEventListener("pageshow", stop);
    return () => {
      document.removeEventListener("click", start);
      window.removeEventListener("pageshow", stop);
      if (timeout) clearTimeout(timeout);
    };
  }, []);

  return (
    <div
      className={`fixed left-0 top-0 z-[9999] h-1 bg-gradient-to-r from-coral via-fuchsia-500 to-cyan-400 shadow-[0_0_18px_rgba(255,90,95,0.7)] transition-all duration-500 ${
        active ? "w-full opacity-100" : "w-0 opacity-0"
      }`}
    />
  );
}
