"use client";

import { useState } from "react";
import { API_URL } from "@/lib/api";

type Step = { name: string; status: string; detail: Record<string, unknown> };

export function Concierge() {
  const [message, setMessage] = useState("Plan a 4-night London trip for a couple: one mid-range stay near the tube and one splurge night somewhere with a river view. Budget £900 total.");
  const [steps, setSteps] = useState<Step[]>([]);
  const [final, setFinal] = useState<string>("");
  const [loading, setLoading] = useState(false);

  async function ask() {
    setLoading(true);
    setSteps([]);
    setFinal("");
    const response = await fetch(`${API_URL}/api/concierge`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ message, session_id: "demo" })
    });
    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    if (!reader) return;
    let buffer = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const chunks = buffer.split("\n\n");
      buffer = chunks.pop() ?? "";
      for (const chunk of chunks) {
        const event = chunk.match(/^event: (.+)$/m)?.[1];
        const data = chunk.match(/^data: (.+)$/m)?.[1];
        if (!event || !data) continue;
        const parsed = JSON.parse(data);
        if (event === "step") setSteps((current) => [...current, parsed]);
        if (event === "final") setFinal(JSON.stringify(parsed, null, 2));
      }
    }
    setLoading(false);
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
      <button className="button mt-2" onClick={ask} disabled={loading}>{loading ? "Thinking..." : "Ask concierge"}</button>
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
