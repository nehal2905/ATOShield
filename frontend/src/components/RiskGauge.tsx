import { riskColor } from "../lib/format";

interface Props {
  risk: number;
  tier?: string;
  size?: number;
}

/** Circular risk gauge drawn with an SVG stroke-dasharray arc. */
export function RiskGauge({ risk, tier, size = 200 }: Props) {
  const stroke = 14;
  const r = (size - stroke) / 2;
  const circumference = 2 * Math.PI * r;
  const pct = Math.min(100, Math.max(0, risk)) / 100;
  const dash = circumference * pct;
  const color = riskColor(risk);

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="#243049"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circumference - dash}`}
          style={{ transition: "stroke-dasharray 0.6s ease, stroke 0.4s ease" }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-4xl font-bold" style={{ color }}>
          {risk}
        </span>
        <span className="text-xs uppercase tracking-widest text-slate-400">risk</span>
        {tier && (
          <span className="mt-1 text-sm font-semibold" style={{ color }}>
            {tier}
          </span>
        )}
      </div>
    </div>
  );
}
