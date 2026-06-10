import type { ReactNode } from "react";

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-2xl border border-edge bg-panel/60 p-6">
      <h2 className="mb-3 text-lg font-semibold text-accent">{title}</h2>
      <div className="space-y-2 text-sm leading-relaxed text-slate-300">{children}</div>
    </section>
  );
}

export default function About() {
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-2xl font-semibold">How ATOShield works</h1>

      <Section title="The model is real">
        <p>
          An unsupervised <strong>Isolation Forest</strong> (200 trees, 5% contamination)
          is trained on benign login behavior only — it never sees attack labels. Its
          <code> decision_function</code> output is calibrated against percentiles of the
          normal-traffic anomaly-score distribution to produce a 0–100 risk. The additive
          per-feature view on the radar is an <em>explainability overlay</em> (SHAP), never
          the score itself.
        </p>
      </Section>

      <Section title="State is the hard part">
        <p>
          “New IP”, “new device”, “login frequency” and “geo-velocity” only mean something
          relative to a <strong>per-user baseline</strong> held in Redis (hot) and Postgres
          (durable). On each event we read the prior baseline, score against it, and only
          then update it — so the model judges the event against the user’s history, not a
          state already contaminated by the current login.
        </p>
      </Section>

      <Section title="Geo-velocity over “location changed”">
        <p>
          A user flying NYC→London is a legitimate location change; the discriminator is
          <em> speed</em>. We compute the haversine great-circle distance between consecutive
          logins divided by the elapsed time. Sustained implied travel above ~900 km/h is
          flagged as <strong>impossible travel</strong> — a real, defensible signal.
        </p>
      </Section>

      <Section title="Honest metrics">
        <p>
          We do not hardcode precision/recall. <code>ml/generate_dataset.py</code> builds a
          labeled synthetic test set, <code>ml/evaluate.py</code> runs a real evaluation, and
          the confusion matrix, precision, recall, F1 and ROC-AUC are written to
          <code> ml/artifacts/eval_report.md</code>. The “slow-burn” attack class (one
          anomalous signal at a time) is genuinely hard; its lower recall is reported, not
          hidden.
        </p>
      </Section>

      <Section title="Threat model (STRIDE-lite)">
        <p><strong>Defends against:</strong> credential stuffing, brute force, impossible-travel
          session hijacking, first-seen device/IP takeovers at odd hours.</p>
        <p><strong>Does not catch well:</strong> a patient attacker perfectly mimicking the user
          from the user’s own device and network; cold-start for brand-new users with no
          baseline; adversarial mimicry that drips one weak signal at a time.</p>
      </Section>

      <Section title="A security tool must be secure">
        <p>
          The dashboard is JWT-protected (httpOnly cookie), all inputs are validated with
          Pydantic v2, ingest/simulation endpoints are rate-limited, and no secrets live in
          the repo (config via <code>.env</code>). NGINX terminates TLS in production.
        </p>
      </Section>

      <Section title="Limitations">
        <ul className="list-disc space-y-1 pl-5">
          <li>Training data is synthetic; real deployment needs a baseline-building period.</li>
          <li>Cold-start: new users have no history, so early logins are under-discriminated.</li>
          <li>Adversarial mimicry from the legitimate device/network is out of scope.</li>
          <li>Geo lookups assume accurate coordinates; VPNs/proxies distort geo-velocity.</li>
        </ul>
      </Section>
    </div>
  );
}
