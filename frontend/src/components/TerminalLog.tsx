import { useEffect, useRef, useState } from "react";
import type { PipelineStep } from "../api/types";

interface Line {
  text: string;
  kind: "cmd" | "info" | "data";
}

function stepToLines(s: PipelineStep): Line[] {
  const lines: Line[] = [
    { text: `▶ ${s.step}`, kind: "cmd" },
    { text: `  ${s.detail}`, kind: "info" },
  ];
  if (s.data) {
    lines.push({ text: `  ${JSON.stringify(s.data)}`, kind: "data" });
  }
  return lines;
}

/** Streams the backend's pipeline trace line-by-line with small async delays. */
export function TerminalLog({ trace }: { trace: PipelineStep[] }) {
  const [lines, setLines] = useState<Line[]>([]);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setLines([]);
    if (!trace || trace.length === 0) return;
    const all = trace.flatMap(stepToLines);
    let i = 0;
    const timer = setInterval(() => {
      setLines((prev) => [...prev, all[i]]);
      i += 1;
      if (i >= all.length) clearInterval(timer);
    }, 140);
    return () => clearInterval(timer);
  }, [trace]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines]);

  return (
    <div className="rounded-2xl border border-edge bg-black/60 p-4 font-mono text-xs">
      <div className="mb-2 flex items-center gap-1.5">
        <span className="h-2.5 w-2.5 rounded-full bg-red-500/70" />
        <span className="h-2.5 w-2.5 rounded-full bg-yellow-500/70" />
        <span className="h-2.5 w-2.5 rounded-full bg-green-500/70" />
        <span className="ml-2 text-slate-500">atoshield — scoring pipeline</span>
      </div>
      <div className="h-72 overflow-y-auto">
        {lines.length === 0 && <div className="text-slate-600">$ awaiting input…</div>}
        {lines.map((l, idx) => (
          <div
            key={idx}
            className={
              l.kind === "cmd"
                ? "text-accent"
                : l.kind === "data"
                ? "text-slate-500"
                : "text-slate-300"
            }
          >
            {l.text}
          </div>
        ))}
        <div ref={endRef} />
      </div>
    </div>
  );
}
