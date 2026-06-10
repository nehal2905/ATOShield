import { Link } from "react-router-dom";

const FEATURES = [
  ["Unsupervised ML", "A real Isolation Forest learns each user's normal and flags deviations — no attack labels needed."],
  ["Behavioral baselines", "Per-user IP/device/geo/frequency state in Redis turns crude flags into meaningful signals."],
  ["Impossible travel", "Continuous geo-velocity (haversine ÷ Δt) catches physically impossible logins, not mere location changes."],
  ["Explainable alerts", "SHAP attributions show analysts WHY a login was flagged, on a behavior radar."],
];

export default function Landing() {
  return (
    <div className="min-h-screen">
      <div className="mx-auto max-w-5xl px-4 py-20 text-center">
        <div className="mb-4 text-6xl">🛡️</div>
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
          ATO<span className="text-accent">Shield</span>
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-slate-400">
          Real-time account takeover detection using unsupervised machine learning and
          behavioral analytics.
        </p>
        <div className="mt-8 flex justify-center gap-3">
          <Link
            to="/dashboard"
            className="rounded-xl bg-accent px-5 py-3 text-sm font-semibold text-ink hover:brightness-110"
          >
            Open Dashboard
          </Link>
          <Link
            to="/about"
            className="rounded-xl border border-edge px-5 py-3 text-sm font-semibold text-slate-200 hover:bg-white/5"
          >
            How it works
          </Link>
        </div>

        <div className="mt-16 grid gap-4 text-left sm:grid-cols-2">
          {FEATURES.map(([title, body]) => (
            <div key={title} className="rounded-2xl border border-edge bg-panel/60 p-5">
              <h3 className="font-semibold text-accent">{title}</h3>
              <p className="mt-1 text-sm text-slate-400">{body}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
