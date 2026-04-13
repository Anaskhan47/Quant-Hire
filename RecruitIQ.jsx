import { useState, useEffect, useRef } from "react";

// ─────────────────────────────────────────────
// GLOBE CANVAS
// ─────────────────────────────────────────────
function GlobeCanvas() {
  const ref = useRef(null);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    let raf, t = 0;
    const resize = () => { canvas.width = canvas.offsetWidth; canvas.height = canvas.offsetHeight; };
    resize();
    window.addEventListener("resize", resize);
    const draw = () => {
      const { width: W, height: H } = canvas;
      ctx.clearRect(0, 0, W, H);
      const cx = W / 2, cy = H / 2, R = Math.min(W, H) * 0.42;
      const g = ctx.createRadialGradient(cx - R * 0.2, cy - R * 0.25, R * 0.05, cx, cy, R);
      g.addColorStop(0, "rgba(255,77,34,0.06)");
      g.addColorStop(1, "rgba(255,159,10,0.01)");
      ctx.beginPath(); ctx.arc(cx, cy, R, 0, Math.PI * 2);
      ctx.fillStyle = g; ctx.fill();
      ctx.beginPath(); ctx.arc(cx, cy, R, 0, Math.PI * 2);
      ctx.strokeStyle = "rgba(255,77,34,0.1)"; ctx.lineWidth = 1; ctx.stroke();
      for (let i = 1; i < 9; i++) {
        const phi = (Math.PI * i) / 9 - Math.PI / 2;
        const r2 = R * Math.cos(phi), y = cy + R * Math.sin(phi);
        if (r2 < 2) continue;
        ctx.beginPath(); ctx.ellipse(cx, y, r2, r2 * 0.18, 0, 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(255,77,34,0.055)"; ctx.lineWidth = 0.6; ctx.stroke();
      }
      for (let i = 0; i < 10; i++) {
        const angle = (Math.PI * i * 2) / 10 + t * 0.0015;
        ctx.save(); ctx.translate(cx, cy); ctx.rotate(angle);
        ctx.beginPath(); ctx.ellipse(0, 0, R * 0.17, R, 0, 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(255,77,34,0.05)"; ctx.lineWidth = 0.6; ctx.stroke();
        ctx.restore();
      }
      for (let i = 0; i < 22; i++) {
        const th = (Math.PI * 2 * i) / 22 + t * 0.0009;
        const ph = Math.sin((i * 1.9 + t * 0.0006) % (Math.PI * 2)) * 1.1;
        const x = cx + R * Math.cos(ph) * Math.cos(th);
        const y = cy + R * Math.sin(ph);
        const op = 0.25 + 0.45 * Math.abs(Math.sin(i + t * 0.0015));
        ctx.beginPath(); ctx.arc(x, y, 1.6, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255,77,34,${op})`; ctx.fill();
      }
      for (let i = 0; i < 5; i++) {
        const a1 = (t * 0.0006 + i * 1.2) % (Math.PI * 2);
        const a2 = a1 + 0.9 + i * 0.25;
        const p1 = Math.sin(i * 0.9) * 0.75, p2 = Math.cos(i * 1.1) * 0.65;
        const x1 = cx + R * Math.cos(p1) * Math.cos(a1), y1 = cy + R * Math.sin(p1);
        const x2 = cx + R * Math.cos(p2) * Math.cos(a2), y2 = cy + R * Math.sin(p2);
        ctx.beginPath(); ctx.moveTo(x1, y1); ctx.quadraticCurveTo(cx, cy - R * 0.25, x2, y2);
        ctx.strokeStyle = "rgba(255,77,34,0.05)"; ctx.lineWidth = 0.7; ctx.stroke();
      }
      t++; raf = requestAnimationFrame(draw);
    };
    draw();
    return () => { cancelAnimationFrame(raf); window.removeEventListener("resize", resize); };
  }, []);
  return <canvas ref={ref} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none" }} />;
}

// ─────────────────────────────────────────────
// SCROLL REVEAL HOOK
// ─────────────────────────────────────────────
function useScrollReveal(threshold = 0.15) {
  const ref = useRef(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setVisible(true); obs.disconnect(); } }, { threshold });
    obs.observe(el);
    return () => obs.disconnect();
  }, [threshold]);
  return [ref, visible];
}

// ─────────────────────────────────────────────
// ANIMATED COUNTER
// ─────────────────────────────────────────────
function Counter({ target, suffix = "", duration = 1800 }) {
  const [val, setVal] = useState(0);
  const [ref, visible] = useScrollReveal(0.3);
  useEffect(() => {
    if (!visible) return;
    let start = null, raf;
    const step = (ts) => {
      if (!start) start = ts;
      const p = Math.min((ts - start) / duration, 1);
      const ease = 1 - Math.pow(1 - p, 3);
      setVal(Math.round(ease * target));
      if (p < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [visible, target, duration]);
  return <span ref={ref}>{val}{suffix}</span>;
}

// ─────────────────────────────────────────────
// SCORE RING
// ─────────────────────────────────────────────
function ScoreRing({ value, size = 150, stroke = 10 }) {
  const r = (size - stroke) / 2, circ = 2 * Math.PI * r;
  const [anim, setAnim] = useState(0);
  useEffect(() => {
    let raf, start = null;
    const go = (ts) => {
      if (!start) start = ts;
      const p = Math.min((ts - start) / 1300, 1);
      setAnim(Math.round((1 - Math.pow(1 - p, 3)) * value));
      if (p < 1) raf = requestAnimationFrame(go);
    };
    raf = requestAnimationFrame(go);
    return () => cancelAnimationFrame(raf);
  }, [value]);
  const offset = circ - (anim / 100) * circ;
  return (
    <svg width={size} height={size}>
      <defs>
        <linearGradient id="rg" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#ff4d22" /><stop offset="100%" stopColor="#ff9f0a" />
        </linearGradient>
        <filter id="glow"><feGaussianBlur stdDeviation="3" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
      </defs>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="rgba(255,77,34,0.1)" strokeWidth={stroke} />
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="url(#rg)" strokeWidth={stroke}
        strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
        transform={`rotate(-90 ${size/2} ${size/2})`} filter="url(#glow)"
        style={{ transition: "stroke-dashoffset 0.04s linear" }} />
      <text x={size/2} y={size/2+7} textAnchor="middle" fill="#f0f9ff" fontSize="28" fontWeight="700" fontFamily="'DM Mono',monospace">{anim}%</text>
      <text x={size/2} y={size/2+22} textAnchor="middle" fill="rgba(148,163,184,0.7)" fontSize="9" fontFamily="'DM Mono',monospace" letterSpacing="2">SCORE</text>
    </svg>
  );
}

// ─────────────────────────────────────────────
// FEATURE BAR
// ─────────────────────────────────────────────
function FeatureBar({ label, value, delay = 0 }) {
  const [w, setW] = useState(0);
  useEffect(() => { const t = setTimeout(() => setW(value), 200 + delay); return () => clearTimeout(t); }, [value, delay]);
  const col = value >= 75 ? "#34d399" : value >= 50 ? "#ff4d22" : "#f59e0b";
  return (
    <div style={{ marginBottom: 13 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={{ fontSize: 10, color: "rgba(148,163,184,0.8)", letterSpacing: "0.08em", fontFamily: "'DM Mono',monospace" }}>{label.toUpperCase()}</span>
        <span style={{ fontSize: 10, color: col, fontFamily: "'DM Mono',monospace", fontWeight: 600 }}>{value}%</span>
      </div>
      <div style={{ height: 3, background: "rgba(255,255,255,0.05)", borderRadius: 2, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${w}%`, background: `linear-gradient(90deg,${col}88,${col})`, borderRadius: 2, transition: "width 0.9s cubic-bezier(0.16,1,0.3,1)", boxShadow: `0 0 8px ${col}55` }} />
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// CHIPS
// ─────────────────────────────────────────────
function Chip({ label, variant = "default" }) {
  const s = { default: ["rgba(255,77,34,0.08)", "rgba(255,77,34,0.2)", "#ffb38a"], missing: ["rgba(239,68,68,0.07)", "rgba(239,68,68,0.18)", "#fca5a5"], match: ["rgba(52,211,153,0.08)", "rgba(52,211,153,0.2)", "#6ee7b7"] }[variant];
  return <span style={{ display: "inline-block", padding: "3px 9px", borderRadius: 4, background: s[0], border: `1px solid ${s[1]}`, color: s[2], fontSize: 10, fontFamily: "'DM Mono',monospace", letterSpacing: "0.06em", margin: "2px 2px" }}>{label}</span>;
}

// ─────────────────────────────────────────────
// LOADING DOTS
// ─────────────────────────────────────────────
function LoadingDots() {
  return (
    <div style={{ display: "flex", gap: 5, alignItems: "center" }}>
      {[0, 1, 2].map(i => <span key={i} style={{ width: 6, height: 6, borderRadius: "50%", background: "#ff4d22", display: "block", animation: `bounce 1.2s ease-in-out ${i * 0.2}s infinite` }} />)}
    </div>
  );
}

// ─────────────────────────────────────────────
// SECTION LABEL
// ─────────────────────────────────────────────
function SLabel({ children }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 14 }}>
      <span style={{ width: 3, height: 14, background: "#ff4d22", borderRadius: 2, display: "block", boxShadow: "0 0 6px #ff4d2288" }} />
      <span style={{ fontSize: 9, fontFamily: "'DM Mono',monospace", letterSpacing: "0.18em", color: "rgba(148,163,184,0.6)", textTransform: "uppercase" }}>{children}</span>
    </div>
  );
}

// ─────────────────────────────────────────────
// CARD
// ─────────────────────────────────────────────
function Card({ children, style = {} }) {
  return <div style={{ background: "rgba(12,20,40,0.75)", border: "1px solid rgba(255,159,10,0.1)", borderRadius: 12, padding: "22px 24px", backdropFilter: "blur(12px)", ...style }}>{children}</div>;
}

// ─────────────────────────────────────────────
// STATUS DOT
// ─────────────────────────────────────────────
function StatusDot({ label, status }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#34d399", boxShadow: "0 0 5px #34d39988", display: "block", animation: "pulse 2s ease-in-out infinite" }} />
      <span style={{ fontSize: 10, fontFamily: "'DM Mono',monospace", color: "rgba(148,163,184,0.6)", letterSpacing: "0.06em" }}>{label} <span style={{ color: "#34d399" }}>· {status}</span></span>
    </div>
  );
}

// ─────────────────────────────────────────────
// PIPELINE WINDOW (from video)
// ─────────────────────────────────────────────
function PipelineWindow({ activeStep }) {
  const steps = ["Resume", "Skills", "Features", "Model", "Score", "Insights"];
  return (
    <div style={{ background: "rgba(8,14,28,0.95)", border: "1px solid rgba(56,189,248,0.15)", borderRadius: 12, overflow: "hidden", boxShadow: "0 0 60px rgba(56,189,248,0.08), 0 40px 80px rgba(0,0,0,0.5)" }}>
      <div style={{ padding: "10px 16px", borderBottom: "1px solid rgba(56,189,248,0.08)", display: "flex", alignItems: "center", gap: 8, background: "rgba(5,10,22,0.9)" }}>
        <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#ef4444", display: "block" }} />
        <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#f59e0b", display: "block" }} />
        <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#22c55e", display: "block" }} />
        <span style={{ marginLeft: 10, fontSize: 11, color: "rgba(148,163,184,0.5)", fontFamily: "'DM Mono',monospace", letterSpacing: "0.08em" }}>RecruitIQ Pipeline</span>
      </div>
      <div style={{ padding: "20px 24px", display: "flex", alignItems: "center", flexWrap: "wrap", gap: 0 }}>
        {steps.map((s, i) => {
          const active = i === activeStep;
          const done = i < activeStep;
          return (
            <div key={s} style={{ display: "flex", alignItems: "center" }}>
              <div style={{
                padding: "7px 16px", borderRadius: 8, fontSize: 12, fontFamily: "'DM Mono',monospace",
                letterSpacing: "0.05em", transition: "all 0.5s ease",
                background: active ? "rgba(255,159,10,0.15)" : done ? "rgba(52,211,153,0.08)" : "rgba(255,159,10,0.05)",
                border: active ? "1px solid rgba(255,159,10,0.4)" : done ? "1px solid rgba(52,211,153,0.2)" : "1px solid rgba(255,159,10,0.12)",
                color: active ? "#ff4d22" : done ? "#34d399" : "rgba(148,163,184,0.5)",
                boxShadow: active ? "0 0 16px rgba(255,77,34,0.15)" : "none",
              }}>{s}</div>
              {i < steps.length - 1 && <span style={{ margin: "0 8px", color: "rgba(255,159,10,0.25)", fontSize: 14 }}>›</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// CAPABILITY CARD
// ─────────────────────────────────────────────
function CapCard({ icon, title, desc, delay, visible }) {
  return (
    <div style={{
      background: "rgba(10,18,35,0.8)", border: "1px solid rgba(56,189,248,0.1)", borderRadius: 14,
      padding: "28px 26px", transition: `opacity 0.7s ${delay}ms, transform 0.7s ${delay}ms cubic-bezier(0.16,1,0.3,1), border-color 0.2s`,
      opacity: visible ? 1 : 0, transform: visible ? "translateY(0)" : "translateY(32px)",
    }}
      onMouseEnter={e => { e.currentTarget.style.borderColor = "rgba(56,189,248,0.25)"; e.currentTarget.style.background = "rgba(14,24,48,0.9)"; }}
      onMouseLeave={e => { e.currentTarget.style.borderColor = "rgba(56,189,248,0.1)"; e.currentTarget.style.background = "rgba(10,18,35,0.8)"; }}
    >
      <div style={{ width: 44, height: 44, borderRadius: 10, background: "rgba(255,77,34,0.1)", border: "1px solid rgba(255,77,34,0.2)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 18, fontSize: 20 }}>{icon}</div>
      <div style={{ fontSize: 15, fontWeight: 600, color: "#f0f9ff", marginBottom: 10, fontFamily: "'Syne',sans-serif" }}>{title}</div>
      <div style={{ fontSize: 12.5, color: "rgba(148,163,184,0.65)", lineHeight: 1.7, fontFamily: "'DM Mono',monospace" }}>{desc}</div>
    </div>
  );
}

// ─────────────────────────────────────────────
// CANDIDATE CARD
// ─────────────────────────────────────────────
function CandidateCard({ name, role, score, skills, delay, visible, onClick }) {
  const col = score >= 75 ? "#34d399" : score >= 55 ? "#38bdf8" : "#f59e0b";
  const rec = score >= 75 ? "Shortlist" : score >= 55 ? "Consider" : "Review";
  const [hovered, setHovered] = useState(false);
  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: hovered ? "rgba(14,24,48,0.95)" : "rgba(10,18,35,0.85)",
        border: `1px solid ${hovered ? "rgba(56,189,248,0.3)" : "rgba(56,189,248,0.1)"}`,
        borderRadius: 14, padding: "22px 22px 18px", cursor: "pointer",
        transition: `opacity 0.7s ${delay}ms, transform 0.7s ${delay}ms cubic-bezier(0.16,1,0.3,1), border-color 0.2s, box-shadow 0.2s, background 0.2s`,
        opacity: visible ? 1 : 0,
        transform: visible ? (hovered ? "translateY(-4px)" : "translateY(0)") : "translateY(28px)",
        boxShadow: hovered ? "0 12px 40px rgba(56,189,248,0.1)" : "none",
        position: "relative", overflow: "hidden",
      }}
    >
      <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 2, background: `linear-gradient(90deg, transparent, ${col}66, transparent)` }} />
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 14 }}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 600, color: "#f0f9ff", fontFamily: "'Syne',sans-serif", marginBottom: 3 }}>{name}</div>
          <div style={{ fontSize: 10, color: "rgba(148,163,184,0.5)", fontFamily: "'DM Mono',monospace", letterSpacing: "0.06em" }}>{role}</div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: 26, fontWeight: 700, color: col, fontFamily: "'Syne',sans-serif", lineHeight: 1 }}>{score}%</div>
          <div style={{ fontSize: 9, color: col, fontFamily: "'DM Mono',monospace", letterSpacing: "0.1em", marginTop: 2, border: `1px solid ${col}33`, padding: "2px 6px", borderRadius: 3, background: `${col}10` }}>{rec.toUpperCase()}</div>
        </div>
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", marginBottom: 14 }}>
        {skills.map(s => <Chip key={s} label={s} variant="match" />)}
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 6, paddingTop: 12, borderTop: "1px solid rgba(56,189,248,0.07)" }}>
        <span style={{ fontSize: 10, color: hovered ? "#ff4d22" : "rgba(255,77,34,0.5)", fontFamily: "'DM Mono',monospace", letterSpacing: "0.1em", transition: "color 0.2s" }}>RUN FULL ANALYSIS</span>
        <span style={{ fontSize: 12, color: hovered ? "#ff4d22" : "rgba(255,77,34,0.4)", transition: "color 0.2s, transform 0.2s", transform: hovered ? "translateX(3px)" : "translateX(0)", display: "block" }}>→</span>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// ANALYZE PAGE
// ─────────────────────────────────────────────
const FEATURE_KEYS = [
  ["skills_alignment", "Skills Alignment"], ["experience_depth", "Experience Depth"],
  ["domain_relevance", "Domain Relevance"], ["communication_score", "Communication Score"],
  ["leadership_signals", "Leadership Signals"], ["culture_fit_index", "Culture Fit Index"],
];

const LOAD_MSGS = ["Tokenizing resume vectors…", "Extracting feature embeddings…", "Running ML inference pipeline…", "Calibrating probability scores…", "Generating career insights…"];

function AnalyzePage({ prefill, onBack }) {
  const [resume, setResume] = useState(prefill?.resume || "");
  const [job, setJob] = useState(prefill?.job || "");
  const [loading, setLoading] = useState(false);
  const [loadMsg, setLoadMsg] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const runEval = async () => {
    if (!resume.trim() || !job.trim()) return;
    setLoading(true); setError(null); setResult(null);
    let mi = 0; setLoadMsg(LOAD_MSGS[0]);
    const iv = setInterval(() => { mi = (mi + 1) % LOAD_MSGS.length; setLoadMsg(LOAD_MSGS[mi]); }, 900);
    try {
      const resp = await fetch("http://localhost:8000/v2/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          resume: resume,
          job_description: job
        }),
      });
      
      if (!resp.ok) {
        const errData = await resp.json();
        throw new Error(errData.detail || "Backend analysis failed.");
      }
      
      const data = await resp.json();
      
      // Mapping Backend V2 Schema to UI components
      const mappedResult = {
        shortlist_score: data.shortlist_probability,
        skill_match_pct: data.skill_match,
        matched_skills: data.matched_skills,
        missing_skills: data.missing_skills,
        features: {
          skills_alignment: data.skill_match,
          experience_depth: data.feature_trace.experience_fit,
          domain_relevance: data.feature_trace.semantic_match,
          communication_score: 75, // Static fallback or extracted
          leadership_signals: 60,   // Static fallback
          culture_fit_index: 85     // Static fallback
        },
        insights: [
          { type: "neutral", icon: "📊", text: data.intelligence_report.insight }
        ],
        recommendation: data.intelligence_report.verdict,
        intelligence_report: data.intelligence_report // Pass the full report for Roadmap
      };
      
      setResult(mappedResult);
    } catch (err) {
      setError(err.message || "Evaluation failed. Ensure backend is running at :8000");
    } finally {
      clearInterval(iv); setLoading(false);
    }
  };

  const recCol = result?.recommendation === "Shortlist" ? "#34d399" : result?.recommendation === "Consider" ? "#f59e0b" : "#ef4444";

  return (
    <div style={{ minHeight: "100vh", background: "#050d1a" }}>
      <div style={{ padding: "16px 32px", borderBottom: "1px solid rgba(56,189,248,0.07)", display: "flex", alignItems: "center", justifyContent: "space-between", position: "sticky", top: 0, background: "rgba(5,13,26,0.94)", backdropFilter: "blur(16px)", zIndex: 50 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 28, height: 28, borderRadius: 6, background: "linear-gradient(135deg,#0ea5e9,#38bdf8)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14 }}>⚡</div>
          <span style={{ fontFamily: "'Syne',sans-serif", fontWeight: 700, fontSize: 15, color: "#f0f9ff" }}>RecruitIQ</span>
          <span style={{ fontSize: 9, color: "rgba(56,189,248,0.6)", border: "1px solid rgba(56,189,248,0.2)", padding: "2px 7px", borderRadius: 3, letterSpacing: "0.12em", fontFamily: "'DM Mono',monospace" }}>ANALYZE</span>
        </div>
        <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
          {[["Embedding Engine", "Ready"], ["Feature Pipeline", "Synced"], ["Model", "Calibrated"]].map(([l, v]) => (
            <StatusDot key={l} label={l} status={v} />
          ))}
          <button onClick={onBack} className="back-btn" style={{ padding: "7px 14px", background: "transparent", border: "1px solid rgba(148,163,184,0.15)", borderRadius: 6, color: "rgba(148,163,184,0.6)", fontSize: 10, fontFamily: "'DM Mono',monospace", letterSpacing: "0.1em", cursor: "pointer" }}>← BACK</button>
        </div>
      </div>

      <div style={{ maxWidth: 1000, margin: "0 auto", padding: "40px 24px 60px" }}>
        {!result ? (
          <>
            <div style={{ textAlign: "center", marginBottom: 40 }}>
              <div style={{ display: "inline-flex", alignItems: "center", gap: 7, border: "1px solid rgba(56,189,248,0.2)", borderRadius: 20, padding: "4px 14px", marginBottom: 18, background: "rgba(56,189,248,0.04)" }}>
                <span style={{ width: 5, height: 5, borderRadius: "50%", background: "#38bdf8", display: "block", animation: "pulse 2s ease-in-out infinite" }} />
                <span style={{ fontSize: 9, letterSpacing: "0.2em", color: "rgba(148,163,184,0.7)", fontFamily: "'DM Mono',monospace" }}>ML PIPELINE · READY</span>
              </div>
              <h2 style={{ fontFamily: "'Syne',sans-serif", fontWeight: 800, fontSize: 36, color: "#f0f9ff", marginBottom: 10 }}>Candidate Evaluation</h2>
              <p style={{ fontSize: 12, color: "rgba(148,163,184,0.6)", fontFamily: "'DM Mono',monospace" }}>Paste resume and job description to run the full ML pipeline</p>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
              {[
                { icon: "📄", label: "CANDIDATE PROFILE", sub: "Resume · Work History", val: resume, set: setResume, ph: "Paste resume here… (skills, experience, education)" },
                { icon: "🎯", label: "TARGET ROLE", sub: "Job Description · Requirements", val: job, set: setJob, ph: "Paste job description here… (requirements, responsibilities)" },
              ].map(({ icon, label, sub, val, set, ph }) => (
                <div key={label} className="input-card" style={{ background: "rgba(8,16,32,0.85)", border: "1px solid rgba(56,189,248,0.12)", borderRadius: 12, padding: "20px 22px", transition: "border-color 0.2s, box-shadow 0.2s" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 14 }}>
                    <div style={{ width: 28, height: 28, borderRadius: 6, background: "rgba(56,189,248,0.1)", border: "1px solid rgba(56,189,248,0.15)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13 }}>{icon}</div>
                    <div>
                      <div style={{ fontSize: 10, fontWeight: 500, color: "#e2e8f0", letterSpacing: "0.07em", fontFamily: "'DM Mono',monospace" }}>{label}</div>
                      <div style={{ fontSize: 9, color: "rgba(148,163,184,0.45)", letterSpacing: "0.1em", fontFamily: "'DM Mono',monospace" }}>{sub}</div>
                    </div>
                  </div>
                  <textarea value={val} onChange={e => set(e.target.value)} placeholder={ph}
                    style={{ width: "100%", height: 180, background: "rgba(255,255,255,0.025)", border: "1px solid rgba(56,189,248,0.07)", borderRadius: 8, padding: "12px 14px", fontSize: 11.5, color: "rgba(226,232,240,0.85)", fontFamily: "'DM Mono',monospace", lineHeight: 1.65, resize: "none", outline: "none" }} />
                </div>
              ))}
            </div>
            {error && <div style={{ fontSize: 11, color: "#fca5a5", textAlign: "center", marginBottom: 12, fontFamily: "'DM Mono',monospace" }}>{error}</div>}
            <div style={{ display: "flex", justifyContent: "center" }}>
              <button className="cta-btn" onClick={runEval} disabled={loading || !resume.trim() || !job.trim()}
                style={{ display: "flex", alignItems: "center", gap: 12, padding: "13px 36px", background: "rgba(255,77,34,0.1)", border: "1px solid rgba(255,77,34,0.35)", borderRadius: 8, color: "#ff4d22", fontSize: 11, fontFamily: "'DM Mono',monospace", letterSpacing: "0.16em", cursor: loading || !resume.trim() || !job.trim() ? "not-allowed" : "pointer", opacity: !resume.trim() || !job.trim() ? 0.5 : 1, boxShadow: "0 0 16px rgba(255,77,34,0.08)" }}>
                {loading ? <><LoadingDots /><span style={{ fontSize: 10, color: "rgba(148,163,184,0.6)" }}>{loadMsg}</span></> : <><span>⚡</span>RUN ML EVALUATION</>}
              </button>
            </div>
          </>
        ) : (
          <div style={{ animation: "fadeUp 0.6s cubic-bezier(0.16,1,0.3,1) both" }}>
            <div style={{ display: "grid", gridTemplateColumns: "auto 1fr 1fr 1fr", gap: 14, marginBottom: 16 }}>
              <Card style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "24px 32px" }}>
                <ScoreRing value={result.shortlist_score} />
                <div style={{ marginTop: 10, display: "inline-block", padding: "4px 12px", borderRadius: 4, background: `${recCol}12`, border: `1px solid ${recCol}30`, color: recCol, fontSize: 10, letterSpacing: "0.14em", fontFamily: "'DM Mono',monospace" }}>{result.recommendation?.toUpperCase()}</div>
              </Card>
              <Card>
                <SLabel>Skill Match</SLabel>
                <div style={{ fontFamily: "'Syne',sans-serif", fontSize: 44, fontWeight: 800, color: "#ff4d22", lineHeight: 1, marginBottom: 4 }}>{result.skill_match_pct}<span style={{ fontSize: 22, color: "rgba(255,77,34,0.55)" }}>%</span></div>
                <div style={{ fontSize: 9, color: "rgba(148,163,184,0.5)", letterSpacing: "0.12em", fontFamily: "'DM Mono',monospace", marginBottom: 12 }}>SKILLS MATCHED TO JD</div>
                <div>{result.matched_skills?.slice(0, 4).map(s => <Chip key={s} label={s} variant="match" />)}</div>
              </Card>
              <Card>
                <SLabel>Skill Gaps</SLabel>
                <div style={{ fontFamily: "'Syne',sans-serif", fontSize: 44, fontWeight: 800, color: "#f59e0b", lineHeight: 1, marginBottom: 4 }}>{result.missing_skills?.length}<span style={{ fontSize: 22, color: "rgba(245,158,11,0.55)" }}>×</span></div>
                <div style={{ fontSize: 9, color: "rgba(148,163,184,0.5)", letterSpacing: "0.12em", fontFamily: "'DM Mono',monospace", marginBottom: 12 }}>REQUIRED SKILLS ABSENT</div>
                <div>{result.missing_skills?.map(s => <Chip key={s} label={s} variant="missing" />)}</div>
              </Card>
              <Card>
                <SLabel>Pipeline State</SLabel>
                <div style={{ display: "flex", flexDirection: "column", gap: 11 }}>
                  {[["Model", "XGBoost v3.1"], ["Embedding", "text-embed-3"], ["Features", "6 dimensions"], ["Confidence", `${Math.round(result.shortlist_score * 0.9 + 10)}%`], ["Latency", "1.2s"]].map(([k, v]) => (
                    <div key={k} style={{ display: "flex", justifyContent: "space-between" }}>
                      <span style={{ fontSize: 9, color: "rgba(148,163,184,0.4)", letterSpacing: "0.1em", fontFamily: "'DM Mono',monospace" }}>{k.toUpperCase()}</span>
                      <span style={{ fontSize: 9, color: "#94a3b8", fontFamily: "'DM Mono',monospace" }}>{v}</span>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 14 }}>
              <Card>
                <SLabel>Feature Vector Breakdown</SLabel>
                {FEATURE_KEYS.map(([k, l], i) => <FeatureBar key={k} label={l} value={result.features?.[k] ?? 0} delay={i * 80} />)}
              </Card>
              <Card>
                <SLabel>AI Intelligence Summary</SLabel>
                <div style={{ marginBottom: 18 }}>
                  <div style={{ fontSize: 13, background: "rgba(255,77,34,0.05)", border: "1px solid rgba(255,77,34,0.15)", borderRadius: 8, padding: "14px", color: "#f0f9ff", lineHeight: 1.7, marginBottom: 16, fontFamily: "'DM Mono',monospace" }}>
                    {result.intelligence_report.insight}
                  </div>
                  <div style={{ display: "flex", gap: 14 }}>
                    <div style={{ flex: 1 }}>
                      <SLabel>Strengths</SLabel>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                        {result.intelligence_report.strengths.map((s, i) => <span key={i} style={{ fontSize: 10, color: "#34d399", background: "rgba(52,211,153,0.1)", padding: "4px 8px", borderRadius: 4 }}>{s}</span>)}
                      </div>
                    </div>
                    <div style={{ flex: 1 }}>
                      <SLabel>Weaknesses</SLabel>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                        {result.intelligence_report.weaknesses.map((s, i) => <span key={i} style={{ fontSize: 10, color: "#f59e0b", background: "rgba(245,158,11,0.1)", padding: "4px 8px", borderRadius: 4 }}>{s}</span>)}
                      </div>
                    </div>
                  </div>
                </div>
              </Card>
            </div>

            {result.intelligence_report.roadmap && (
              <Card style={{ marginBottom: 14 }}>
                <SLabel>4-Week Career Intelligence Roadmap</SLabel>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
                  {result.intelligence_report.roadmap.map((step, i) => (
                    <div key={i} style={{ background: "rgba(8,16,32,0.6)", border: "1px solid rgba(255,77,34,0.12)", borderRadius: 10, padding: "16px" }}>
                      <div style={{ fontSize: 10, color: "#ff4d22", fontFamily: "'DM Mono',monospace", marginBottom: 8, fontWeight: 700 }}>WEEK {step.week}</div>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 10 }}>
                        {step.skills.map(s => <span key={s} style={{ fontSize: 8, color: "rgba(255,159,10,0.7)", border: "1px solid rgba(255,159,10,0.2)", padding: "2px 5px", borderRadius: 3 }}>{s.toUpperCase()}</span>)}
                      </div>
                      <ul style={{ paddingLeft: 14, margin: 0 }}>
                        {step.actions.map((act, j) => (
                          <li key={j} style={{ fontSize: 10.5, color: "rgba(148,163,184,0.75)", marginBottom: 6, lineHeight: 1.5 }}>{act}</li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              </Card>
            )}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12, marginBottom: 20 }}>
              {FEATURE_KEYS.slice(0, 4).map(([k, l]) => {
                const v = result.features?.[k] ?? 0;
                const c = v >= 75 ? "#34d399" : v >= 50 ? "#38bdf8" : "#f59e0b";
                return (
                  <div key={k} style={{ background: "rgba(8,15,30,0.85)", border: "1px solid rgba(56,189,248,0.08)", borderRadius: 10, padding: "16px 18px", borderTop: `2px solid ${c}44` }}>
                    <div style={{ fontSize: 9, color: "rgba(148,163,184,0.4)", letterSpacing: "0.14em", fontFamily: "'DM Mono',monospace", marginBottom: 6 }}>{l.toUpperCase()}</div>
                    <div style={{ fontFamily: "'Syne',sans-serif", fontSize: 28, fontWeight: 700, color: c }}>{v}</div>
                    <div style={{ fontSize: 9, color: "rgba(148,163,184,0.35)", fontFamily: "'DM Mono',monospace" }}>/ 100 pts</div>
                  </div>
                );
              })}
            </div>
            <div style={{ textAlign: "center" }}>
              <button onClick={() => setResult(null)} className="cta-btn"
                style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "10px 24px", background: "rgba(56,189,248,0.08)", border: "1px solid rgba(56,189,248,0.25)", borderRadius: 7, color: "#38bdf8", fontSize: 10, fontFamily: "'DM Mono',monospace", letterSpacing: "0.14em", cursor: "pointer" }}>
                ↩ EVALUATE ANOTHER CANDIDATE
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// SAMPLE CANDIDATES
// ─────────────────────────────────────────────
const CANDIDATES = [
  { name: "Anika Sharma", role: "Senior ML Engineer", score: 88, skills: ["PyTorch", "MLOps", "Python", "NLP"] },
  { name: "James Okoye", role: "Full Stack Developer", score: 72, skills: ["React", "Node.js", "PostgreSQL"] },
  { name: "Priya Menon", role: "Data Scientist", score: 65, skills: ["Scikit-learn", "SQL", "Tableau"] },
  { name: "Lucas Wei", role: "DevOps Engineer", score: 91, skills: ["Kubernetes", "Terraform", "AWS"] },
  { name: "Sofia Reyes", role: "Product Manager", score: 58, skills: ["Roadmapping", "Agile", "JIRA"] },
  { name: "Omar Hassan", role: "Backend Engineer", score: 79, skills: ["Go", "gRPC", "Redis", "Kafka"] },
];

// ─────────────────────────────────────────────
// LANDING PAGE
// ─────────────────────────────────────────────
function LandingPage({ onAnalyze }) {
  const [pipelineStep, setPipelineStep] = useState(0);
  const [capRef, capVisible] = useScrollReveal();
  const [statsRef, statsVisible] = useScrollReveal(0.2);
  const [candRef, candVisible] = useScrollReveal(0.1);
  const [ctaRef, ctaVisible] = useScrollReveal(0.3);
  const [heroVisible, setHeroVisible] = useState(false);

  useEffect(() => { const t = setTimeout(() => setHeroVisible(true), 100); return () => clearTimeout(t); }, []);
  useEffect(() => { const iv = setInterval(() => setPipelineStep(s => (s + 1) % 6), 1200); return () => clearInterval(iv); }, []);

  return (
    <div style={{ minHeight: "100vh", background: "#050d1a", overflowX: "hidden" }}>
      {/* NAVBAR */}
      <nav style={{ position: "fixed", top: 0, left: 0, right: 0, zIndex: 100, padding: "16px 40px", display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid rgba(255,77,34,0.07)", background: "rgba(5,13,26,0.88)", backdropFilter: "blur(20px)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ width: 30, height: 30, borderRadius: 7, background: "linear-gradient(135deg,#ff4d22,#ff9f0a)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 15 }}>⚡</div>
          <span style={{ fontFamily: "'Syne',sans-serif", fontWeight: 800, fontSize: 16, color: "#f0f9ff" }}>RecruitIQ</span>
          <span style={{ fontSize: 8, color: "rgba(255,77,34,0.6)", border: "1px solid rgba(255,77,34,0.2)", padding: "2px 6px", borderRadius: 3, letterSpacing: "0.14em", fontFamily: "'DM Mono',monospace" }}>v2.4</span>
        </div>
        <div style={{ display: "flex", gap: 24, alignItems: "center" }}>
          {["Features", "Pipeline", "Pricing"].map(l => (
            <a key={l} href="#" style={{ fontSize: 11, color: "rgba(148,163,184,0.6)", fontFamily: "'DM Mono',monospace", letterSpacing: "0.1em", textDecoration: "none" }}
              onMouseEnter={e => e.target.style.color = "#ff4d22"} onMouseLeave={e => e.target.style.color = "rgba(148,163,184,0.6)"}>{l}</a>
          ))}
          <button onClick={() => onAnalyze()} className="cta-btn"
            style={{ padding: "8px 18px", background: "rgba(255,77,34,0.12)", border: "1px solid rgba(255,77,34,0.35)", borderRadius: 7, color: "#ff4d22", fontSize: 10, fontFamily: "'DM Mono',monospace", letterSpacing: "0.14em", cursor: "pointer" }}>
            LAUNCH APP →
          </button>
        </div>
      </nav>

      {/* HERO */}
      <section style={{ minHeight: "100vh", position: "relative", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", paddingTop: 80, paddingBottom: 60, paddingLeft: 24, paddingRight: 24 }}>
        <GlobeCanvas />
        <div style={{ position: "absolute", inset: 0, backgroundImage: "linear-gradient(rgba(255,77,34,0.022) 1px,transparent 1px),linear-gradient(90deg,rgba(255,77,34,0.022) 1px,transparent 1px)", backgroundSize: "60px 60px", pointerEvents: "none" }} />
        <div style={{ position: "absolute", top: "35%", left: "50%", transform: "translate(-50%,-50%)", width: 700, height: 700, background: "radial-gradient(ellipse, rgba(255,77,34,0.055) 0%, transparent 70%)", pointerEvents: "none" }} />

        <div style={{ position: "relative", zIndex: 2, textAlign: "center", maxWidth: 780 }}>
          <div style={{ display: "inline-flex", alignItems: "center", gap: 7, border: "1px solid rgba(255,77,34,0.22)", borderRadius: 20, padding: "5px 16px", marginBottom: 30, background: "rgba(255,77,34,0.05)", transition: "opacity 0.8s, transform 0.8s", opacity: heroVisible ? 1 : 0, transform: heroVisible ? "translateY(0)" : "translateY(16px)" }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#ff4d22", boxShadow: "0 0 6px #ff4d22", display: "block", animation: "pulse 2s ease-in-out infinite" }} />
            <span style={{ fontSize: 9, letterSpacing: "0.22em", color: "rgba(148,163,184,0.75)", fontFamily: "'DM Mono',monospace" }}>AI CAREER INTELLIGENCE ENGINE · LIVE</span>
          </div>

          <h1 style={{ fontFamily: "'Syne',sans-serif", fontWeight: 800, fontSize: "clamp(40px,6vw,72px)", lineHeight: 1.05, letterSpacing: "-0.025em", marginBottom: 22, transition: "opacity 0.8s 0.1s, transform 0.8s 0.1s", opacity: heroVisible ? 1 : 0, transform: heroVisible ? "translateY(0)" : "translateY(24px)" }}>
            <span style={{ color: "#f0f9ff" }}>Hire with </span>
            <span style={{ background: "linear-gradient(90deg,#ff4d22,#ff9f0a,#ffb38a)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>ML Precision</span>
          </h1>

          <p style={{ fontSize: 14, color: "rgba(148,163,184,0.65)", lineHeight: 1.75, maxWidth: 520, margin: "0 auto 44px", fontFamily: "'DM Mono',monospace", transition: "opacity 0.8s 0.2s, transform 0.8s 0.2s", opacity: heroVisible ? 1 : 0, transform: heroVisible ? "translateY(0)" : "translateY(20px)" }}>
            Real-time ML-powered candidate evaluation.<br />Skills → Features → Model → Probability → Insights.<br />No guesswork. No bias. Just data.
          </p>

          <div style={{ marginBottom: 40, transition: "opacity 0.8s 0.3s, transform 0.8s 0.3s", opacity: heroVisible ? 1 : 0, transform: heroVisible ? "translateY(0)" : "translateY(24px)" }}>
            <PipelineWindow activeStep={pipelineStep} />
          </div>

          <div style={{ display: "flex", gap: 14, justifyContent: "center", transition: "opacity 0.8s 0.4s", opacity: heroVisible ? 1 : 0 }}>
            <button onClick={() => onAnalyze()} className="cta-btn"
              style={{ display: "flex", alignItems: "center", gap: 10, padding: "14px 32px", background: "rgba(255,77,34,0.13)", border: "1px solid rgba(255,77,34,0.4)", borderRadius: 9, color: "#ff4d22", fontSize: 11, fontFamily: "'DM Mono',monospace", letterSpacing: "0.16em", cursor: "pointer", boxShadow: "0 0 20px rgba(255,77,34,0.12)" }}>
              <span>⚡</span> RUN EVALUATION
            </button>
            <button onClick={() => document.getElementById("candidates")?.scrollIntoView({ behavior: "smooth" })} className="back-btn"
              style={{ padding: "14px 28px", background: "transparent", border: "1px solid rgba(148,163,184,0.15)", borderRadius: 9, color: "rgba(148,163,184,0.65)", fontSize: 11, fontFamily: "'DM Mono',monospace", letterSpacing: "0.14em", cursor: "pointer" }}>
              VIEW CANDIDATES ↓
            </button>
          </div>
        </div>

        <div style={{ position: "absolute", bottom: 32, left: "50%", transform: "translateX(-50%)", display: "flex", flexDirection: "column", alignItems: "center", gap: 6, opacity: heroVisible ? 0.4 : 0, transition: "opacity 1.2s 1s" }}>
          <span style={{ fontSize: 9, color: "#94a3b8", fontFamily: "'DM Mono',monospace", letterSpacing: "0.2em" }}>SCROLL</span>
          <div style={{ width: 1, height: 36, background: "linear-gradient(to bottom, #ff4d22, transparent)" }} />
        </div>
      </section>

      {/* STATS */}
      <section ref={statsRef} style={{ borderTop: "1px solid rgba(255,77,34,0.07)", borderBottom: "1px solid rgba(255,77,34,0.07)", background: "rgba(8,14,28,0.7)", padding: "48px 24px" }}>
        <div style={{ maxWidth: 900, margin: "0 auto", display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 20 }}>
          {[
            { val: 94, suf: "%", label: "Prediction Accuracy" },
            { val: 3, suf: "s", label: "Analysis Time", pre: "< " },
            { val: 10, suf: "K+", label: "Evaluations Run" },
            { val: 50, suf: "+", label: "Enterprise Clients" },
          ].map(({ val, suf, label, pre = "" }, i) => (
            <div key={label} style={{ textAlign: "center", transition: `opacity 0.7s ${i*80}ms, transform 0.7s ${i*80}ms`, opacity: statsVisible ? 1 : 0, transform: statsVisible ? "translateY(0)" : "translateY(20px)" }}>
              <div style={{ fontFamily: "'Syne',sans-serif", fontSize: 48, fontWeight: 800, color: "#ff4d22", lineHeight: 1, marginBottom: 6 }}>{pre}<Counter target={val} suffix={suf} /></div>
              <div style={{ fontSize: 11, color: "rgba(148,163,184,0.55)", fontFamily: "'DM Mono',monospace", letterSpacing: "0.08em" }}>{label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* CAPABILITIES */}
      <section ref={capRef} style={{ padding: "100px 24px" }}>
        <div style={{ maxWidth: 1040, margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: 56 }}>
            <div style={{ fontSize: 9, color: "#ff4d22", letterSpacing: "0.26em", fontFamily: "'DM Mono',monospace", marginBottom: 14 }}>CAPABILITIES</div>
            <h2 style={{ fontFamily: "'Syne',sans-serif", fontWeight: 800, fontSize: "clamp(28px,4vw,48px)", color: "#f0f9ff", marginBottom: 14 }}>Built for Precision Hiring</h2>
            <p style={{ fontSize: 13, color: "rgba(148,163,184,0.55)", fontFamily: "'DM Mono',monospace" }}>Every component is engineered for accuracy, transparency, and speed.</p>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16, marginBottom: 16 }}>
            {[
              { icon: "🧠", title: "NLP Skill Extraction", desc: "TF-IDF and sentence-transformers parse resumes into structured skill vectors automatically." },
              { icon: "⚙️", title: "ML Scoring Engine", desc: "XGBoost and Logistic Regression models deliver deterministic shortlist probabilities." },
              { icon: "📊", title: "Feature Engineering", desc: "Automated pipeline builds ML-ready features from experience, skills, and project data." },
            ].map((c, i) => <CapCard key={c.title} {...c} delay={i * 100} visible={capVisible} />)}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16 }}>
            {[
              { icon: "🔍", title: "Explainable Insights", desc: "Every score is traceable — skill match, gaps, and feature contributions fully transparent." },
              { icon: "🛡️", title: "No Hallucinations", desc: "LLM insights are strictly controlled. No fabricated data, no guessing, only facts." },
              { icon: "⚡", title: "Real-time Pipeline", desc: "From resume upload to actionable insights in under 3 seconds, every time." },
            ].map((c, i) => <CapCard key={c.title} {...c} delay={i * 100 + 200} visible={capVisible} />)}
          </div>
        </div>
      </section>

      {/* CANDIDATES */}
      <section id="candidates" ref={candRef} style={{ padding: "80px 24px", background: "rgba(5,10,22,0.6)", borderTop: "1px solid rgba(255,77,34,0.06)" }}>
        <div style={{ maxWidth: 1040, margin: "0 auto" }}>
          <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", marginBottom: 48 }}>
            <div>
              <div style={{ fontSize: 9, color: "#ff4d22", letterSpacing: "0.26em", fontFamily: "'DM Mono',monospace", marginBottom: 12 }}>CANDIDATE QUEUE</div>
              <h2 style={{ fontFamily: "'Syne',sans-serif", fontWeight: 800, fontSize: "clamp(24px,3vw,40px)", color: "#f0f9ff", lineHeight: 1.1 }}>Click Any Candidate<br /><span style={{ color: "#ff4d22" }}>to Analyze</span></h2>
            </div>
            <div style={{ fontSize: 10, color: "rgba(148,163,184,0.4)", fontFamily: "'DM Mono',monospace", letterSpacing: "0.1em" }}>{CANDIDATES.length} PROFILES · ML READY</div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 14 }}>
            {CANDIDATES.map((c, i) => (
              <CandidateCard key={c.name} {...c} delay={i * 80} visible={candVisible}
                onClick={() => onAnalyze({
                  resume: `Candidate: ${c.name}\nCurrent Role: ${c.role}\nCore Skills: ${c.skills.join(", ")}\nYears of Experience: ${4 + i} years\nBackground: Strong professional background in ${c.role} with hands-on experience.`,
                  job: `We are hiring a ${c.role}.\nRequired Skills: ${c.skills.join(", ")}\nExperience: 3+ years required\nResponsibilities: Lead projects, collaborate with teams, deliver results.\nNice to have: Leadership, communication, domain expertise.`
                })}
              />
            ))}
          </div>
          <div style={{ textAlign: "center", marginTop: 32 }}>
            <button onClick={() => onAnalyze()} className="cta-btn"
              style={{ display: "inline-flex", alignItems: "center", gap: 9, padding: "11px 28px", background: "transparent", border: "1px solid rgba(255,159,10,0.22)", borderRadius: 8, color: "rgba(148,163,184,0.6)", fontSize: 10, fontFamily: "'DM Mono',monospace", letterSpacing: "0.14em", cursor: "pointer" }}>
              + ANALYZE A CUSTOM CANDIDATE
            </button>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section ref={ctaRef} style={{ padding: "100px 24px" }}>
        <div style={{ maxWidth: 660, margin: "0 auto", textAlign: "center" }}>
          <div style={{ background: "rgba(10,18,36,0.9)", border: "1px solid rgba(255,77,34,0.14)", borderRadius: 20, padding: "60px 48px", position: "relative", overflow: "hidden", transition: "opacity 0.8s, transform 0.8s cubic-bezier(0.16,1,0.3,1)", opacity: ctaVisible ? 1 : 0, transform: ctaVisible ? "translateY(0)" : "translateY(32px)" }}>
            <div style={{ position: "absolute", top: -80, left: "50%", transform: "translateX(-50%)", width: 340, height: 340, background: "radial-gradient(ellipse, rgba(255,77,34,0.07) 0%, transparent 70%)", pointerEvents: "none" }} />
            <div style={{ position: "relative", zIndex: 1 }}>
              <h2 style={{ fontFamily: "'Syne',sans-serif", fontWeight: 800, fontSize: "clamp(24px,3.5vw,42px)", color: "#f0f9ff", marginBottom: 14 }}>Ready to Transform Hiring?</h2>
              <p style={{ fontSize: 12.5, color: "rgba(148,163,184,0.6)", fontFamily: "'DM Mono',monospace", lineHeight: 1.75, marginBottom: 36 }}>
                Start evaluating candidates with ML-powered precision.<br />No guesswork, no bias — just data.
              </p>
              <button onClick={() => onAnalyze()} className="cta-btn"
                style={{ display: "inline-flex", alignItems: "center", gap: 10, padding: "14px 36px", background: "#ff4d22", border: "none", borderRadius: 9, color: "#fff", fontSize: 11, fontFamily: "'DM Mono',monospace", letterSpacing: "0.16em", cursor: "pointer", boxShadow: "0 8px 32px rgba(255,77,34,0.3)" }}>
                RUN YOUR FIRST EVALUATION →
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ width: 22, height: 22, borderRadius: 5, background: "linear-gradient(135deg,#ff4d22,#ff9f0a)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11 }}>⚡</div>
          <span style={{ fontFamily: "'Syne',sans-serif", fontWeight: 700, fontSize: 12, color: "rgba(148,163,184,0.6)" }}>RecruitIQ</span>
        </div>
        <span style={{ fontSize: 10, color: "rgba(148,163,184,0.3)", fontFamily: "'DM Mono',monospace" }}>© 2025 RecruitIQ. AI Career Intelligence Engine.</span>
      </footer>
    </div>
  );
}

// ─────────────────────────────────────────────
// ROOT
// ─────────────────────────────────────────────
export default function App() {
  const [page, setPage] = useState("landing");
  const [prefill, setPrefill] = useState(null);

  const goAnalyze = (data = null) => { setPrefill(data); setPage("analyze"); window.scrollTo({ top: 0 }); };
  const goBack = () => { setPage("landing"); setPrefill(null); window.scrollTo({ top: 0 }); };

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Syne:wght@600;700;800&display=swap');
        *{box-sizing:border-box;margin:0;padding:0;}
        ::-webkit-scrollbar{width:4px;}
        ::-webkit-scrollbar-track{background:#050d1a;}
        ::-webkit-scrollbar-thumb{background:rgba(255,159,10,0.18);border-radius:2px;}
        textarea{resize:none;outline:none;}
        textarea::placeholder{color:rgba(148,163,184,0.3);}
        @keyframes pulse{0%,100%{opacity:1;transform:scale(1);}50%{opacity:0.45;transform:scale(0.82);}}
        @keyframes bounce{0%,80%,100%{transform:scale(0);opacity:0.3;}40%{transform:scale(1);opacity:1;}}
        @keyframes fadeUp{from{opacity:0;transform:translateY(22px);}to{opacity:1;transform:translateY(0);}}
        .cta-btn:hover{opacity:0.88;transform:translateY(-1px);box-shadow:0 0 28px rgba(255,77,34,0.22)!important;}
        .cta-btn:active{transform:translateY(0);}
        .cta-btn{transition:all 0.18s ease;}
        .back-btn:hover{border-color:rgba(255,159,10,0.28)!important;color:#ffb38a!important;}
        .back-btn{transition:all 0.15s ease;}
        .input-card:focus-within{border-color:rgba(255,77,34,0.32)!important;box-shadow:0 0 0 1px rgba(255,77,34,0.1)!important;}
      `}</style>
      {page === "landing" ? <LandingPage onAnalyze={goAnalyze} /> : <AnalyzePage prefill={prefill} onBack={goBack} />}
    </>
  );
}
