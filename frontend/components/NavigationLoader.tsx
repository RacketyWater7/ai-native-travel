"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

export function NavigationLoader() {
  const [active, setActive] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    let timeout: ReturnType<typeof setTimeout> | undefined;
    const start = (event: MouseEvent) => {
      const target = event.target as HTMLElement | null;
      const anchor = target?.closest("a");
      if (!anchor) return;
      const href = anchor.getAttribute("href");
      if (!href || href.startsWith("#") || href.startsWith("http") || href === pathname) return;
      setActive(true);
      if (timeout) clearTimeout(timeout);
      timeout = setTimeout(() => setActive(false), 8000);
    };
    document.addEventListener("click", start);
    return () => {
      document.removeEventListener("click", start);
      if (timeout) clearTimeout(timeout);
    };
  }, [pathname]);

  useEffect(() => {
    const timeout = setTimeout(() => setActive(false), 350);
    return () => clearTimeout(timeout);
  }, [pathname]);

  return (
    <>
      <div
        className={`fixed left-0 top-0 z-[9999] h-1 bg-gradient-to-r from-coral via-fuchsia-500 to-cyan-400 shadow-[0_0_18px_rgba(255,90,95,0.7)] transition-all duration-500 ${
          active ? "w-full opacity-100" : "w-0 opacity-0"
        }`}
      />
      {active ? (
        <div className="fixed left-1/2 top-4 z-[9999] -translate-x-1/2 rounded-full border border-white/70 bg-white/90 px-4 py-2 text-xs font-bold text-ink shadow-xl shadow-black/10 backdrop-blur">
          Navigating...
        </div>
      ) : null}
    </>
  );
}
