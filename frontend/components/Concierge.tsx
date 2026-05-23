"use client";

import { useState } from "react";
import { API_URL } from "@/lib/api";

type Step = { name: string; status: string; detail: Record<string, unknown> };

export function Concierge() {
  const [message, setMessage] = useState("Plan a 4-night London trip for a couple: one mid-range stay near the tube and one splurge night somewhere with a river view. Budget £900 total.");
  const [steps, setSteps] = useState<Step[]>([]);
  const [final, setFinal] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function ask() {
    setLoading(true);
    setSteps([]);
    setFinal("");
    setError(null);
    try {
      const response = await fetch(`${API_URL}/api/concierge`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ message, session_id: "demo" })
      });
      if (!response.ok || !response.body) throw new Error("Concierge stream failed to start");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      const consumeBlock = (block: string) => {
        const lines = block.split(/\r?\n/);
        const event = lines.find((line) => line.startsWith("event: "))?.slice(7).trim();
        const data = lines
          .filter((line) => line.startsWith("data: "))
          .map((line) => line.slice(6))
          .join("\n");
        if (!event || !data) return;
        const parsed = JSON.parse(data);
        if (event === "request") {
          setSteps((current) => [...current, { name: "Request", status: "started", detail: parsed }]);
        }
        if (event === "step") setSteps((current) => [...current, parsed]);
        if (event === "final") setFinal(JSON.stringify(parsed, null, 2));
        if (event === "done") {
          setSteps((current) => [...current, { name: "Trace saved", status: "finished", detail: parsed }]);
        }
      };

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const chunks = buffer.split(/\r?\n\r?\n/);
        buffer = chunks.pop() ?? "";
        chunks.forEach(consumeBlock);
      }
      if (buffer.trim()) consumeBlock(buffer);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Concierge failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <aside className="fixed bottom-5 right-5 z-20 w-[420px] max-w-[calc(100vw-2rem)] rounded-3xl border border-black/10 bg-white p-4 shadow-2xl">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="font-black">AI concierge</h2>
        <span className="text-xs text-black/50">SSE agent steps</span>
      </div>
      <textarea
        className="h-24 w-full rounded-2xl border border-black/10 p-3 text-sm"
        value={message}
        onChange={(event) => setMessage(event.target.value)}
      />
      <button className="button mt-2 relative overflow-hidden" onClick={ask} disabled={loading}>
        {loading ? "Thinking..." : "Ask concierge"}
        {loading ? <span className="absolute inset-x-0 bottom-0 h-1 animate-pulse bg-white/70" /> : null}
      </button>
      {error ? <div className="mt-2 rounded-2xl bg-red-50 p-3 text-xs text-red-700">{error}</div> : null}
      <div className="mt-3 max-h-48 space-y-2 overflow-auto text-xs">
        {steps.map((step, index) => (
          <div key={`${step.name}-${index}`} className="rounded-2xl bg-sand p-2">
            <b>{step.name}</b> · {step.status}
            <pre className="mt-1 whitespace-pre-wrap text-[10px] text-black/60">{JSON.stringify(step.detail, null, 2)}</pre>
          </div>
        ))}
      </div>
      {final ? <pre className="mt-3 max-h-40 overflow-auto rounded-2xl bg-ink p-3 text-[10px] text-white">{final}</pre> : null}
    </aside>
  );
}
