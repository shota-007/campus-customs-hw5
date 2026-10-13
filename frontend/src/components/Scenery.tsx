// The island behind the desk: sky, breathing sun, drifting clouds, palms, and rolling waves.
// Pure CSS/SVG, sits behind everything, and goes still for prefers-reduced-motion.

function Palm({ flip = false }: { flip?: boolean }) {
  return (
    <svg className={`palm ${flip ? "palm-right" : "palm-left"}`} viewBox="0 0 220 320" aria-hidden="true">
      <path d="M118 320 C 112 250, 104 190, 120 120" stroke="#0f5c63" strokeWidth="11" fill="none" strokeLinecap="round" />
      <path d="M118 320 C 112 250, 104 190, 120 120" stroke="#1a7a80" strokeWidth="4" strokeDasharray="3 13" fill="none" />
      <g className="fronds" fill="#137076">
        <path d="M120 120 C 80 90, 40 96, 8 126 C 46 108, 82 110, 120 124 Z" />
        <path d="M120 120 C 92 70, 60 52, 22 58 C 62 70, 92 92, 120 124 Z" />
        <path d="M120 120 C 124 72, 146 42, 182 30 C 156 58, 136 88, 122 124 Z" />
        <path d="M120 120 C 160 96, 196 104, 218 132 C 184 116, 152 116, 122 126 Z" />
        <path d="M120 120 C 150 130, 172 158, 176 192 C 158 162, 138 142, 118 128 Z" />
        <path d="M120 120 C 92 132, 74 160, 72 190 C 88 160, 104 142, 122 128 Z" />
      </g>
      <circle cx="114" cy="128" r="6" fill="#7a4b22" />
      <circle cx="125" cy="131" r="5.5" fill="#8a5a2b" />
    </svg>
  );
}

function Waves() {
  const wave = "M0 40 C 150 10, 300 70, 450 40 C 600 10, 750 70, 900 40 C 1050 10, 1200 70, 1350 40 C 1500 10, 1650 70, 1800 40 V120 H0 Z";
  return (
    <div className="waves" aria-hidden="true">
      <svg className="wave wave-back" viewBox="0 0 1800 120" preserveAspectRatio="none"><path d={wave} /></svg>
      <svg className="wave wave-mid" viewBox="0 0 1800 120" preserveAspectRatio="none"><path d={wave} /></svg>
      <svg className="wave wave-front" viewBox="0 0 1800 120" preserveAspectRatio="none"><path d={wave} /></svg>
    </div>
  );
}

export function Scenery() {
  return (
    <div className="scenery" aria-hidden="true">
      <div className="sun" />
      <div className="cloud cloud-1" />
      <div className="cloud cloud-2" />
      <div className="cloud cloud-3" />
      <svg className="gulls" viewBox="0 0 120 40">
        <path d="M10 20 q6 -7 12 0 q6 -7 12 0" />
        <path d="M52 10 q5 -6 10 0 q5 -6 10 0" />
        <path d="M88 24 q4 -5 8 0 q4 -5 8 0" />
      </svg>
      <Palm />
      <Palm flip />
      <div className="sand" />
      <Waves />
    </div>
  );
}
