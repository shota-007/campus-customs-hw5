// The crew: each agent has a beach-creature mascot (drawn in inline SVG), a color, and a voice.
import type { Role } from "./types";

export interface AgentMeta {
  role: Role;
  name: string;
  creature: string;
  blurb: string;
  color: string; // ink color for names, borders, chips
  tint: string; // soft background for bubbles and cards
}

export const ROLES: Role[] = ["boss", "inventory", "accounting", "facilities", "customer_service"];

export const AGENTS: Record<Role, AgentMeta> = {
  boss: {
    role: "boss",
    name: "Boss",
    creature: "Sea-turtle captain",
    blurb: "Reads every ticket, routes the crew, makes the final call.",
    color: "#1d4f91",
    tint: "#e4eefc",
  },
  inventory: {
    role: "inventory",
    name: "Inventory",
    creature: "Octopus",
    blurb: "Eight arms on the shelves: stock, holds, restock vendors.",
    color: "#0b8794",
    tint: "#ddf4f5",
  },
  accounting: {
    role: "accounting",
    name: "Accounting",
    creature: "Pelican",
    blurb: "Keeps the till in its pouch: cash, margins, payment requests.",
    color: "#b86a12",
    tint: "#fdf0dc",
  },
  facilities: {
    role: "facilities",
    name: "Facilities",
    creature: "Hermit crab",
    blurb: "Its shell is its lease: rent, landlord, the shop space.",
    color: "#2a7f55",
    tint: "#e1f3e8",
  },
  customer_service: {
    role: "customer_service",
    name: "Customer Service",
    creature: "Dolphin",
    blurb: "The friendly voice: drafts every customer message (never sent).",
    color: "#c6405c",
    tint: "#fde7ec",
  },
};

export function isRole(value: string): value is Role {
  return (ROLES as string[]).includes(value);
}

export function agentName(agent: string): string {
  return isRole(agent) ? AGENTS[agent].name : agent === "system" ? "Desk" : agent;
}

export function agentColor(agent: string): string {
  return isRole(agent) ? AGENTS[agent].color : agent === "system" ? "#5b6b85" : "#d9822b";
}

export function agentTint(agent: string): string {
  return isRole(agent) ? AGENTS[agent].tint : agent === "system" ? "#eef2f7" : "#fff4e5";
}

// --------------------------------------------------------------------------------------------
// Mascots
// --------------------------------------------------------------------------------------------

function Turtle() {
  return (
    <g>
      <ellipse cx="17" cy="45" rx="6" ry="3.4" fill="#7fcf9d" transform="rotate(-25 17 45)" />
      <ellipse cx="41" cy="46" rx="6" ry="3.4" fill="#7fcf9d" transform="rotate(25 41 46)" />
      <ellipse cx="17" cy="28" rx="6" ry="3.4" fill="#7fcf9d" transform="rotate(25 17 28)" />
      <ellipse cx="41" cy="27" rx="6" ry="3.4" fill="#7fcf9d" transform="rotate(-25 41 27)" />
      <ellipse cx="29" cy="37" rx="16" ry="12.5" fill="#2f8f63" />
      <path d="M29 28 l6.5 4.5 -2.4 7.6 h-8.2 l-2.4 -7.6z" fill="#58b884" />
      <path d="M29 28 v-3 M35.5 32.5 l5-2 M33 40 l3.5 4 M25 40 l-3.5 4 M22.5 32.5 l-5-2" stroke="#58b884" strokeWidth="2" strokeLinecap="round" />
      <circle cx="50" cy="31" r="7" fill="#7fcf9d" />
      <circle cx="52.4" cy="29.4" r="1.5" fill="#0a2e52" />
      <path d="M49 34.2 q2.4 1.6 4.6 0" stroke="#0a2e52" strokeWidth="1.3" fill="none" strokeLinecap="round" />
      {/* captain's hat */}
      <path d="M43.5 25.5 q6.5 -7 13 0 z" fill="#1d4f91" />
      <rect x="43" y="24.6" width="14" height="2.6" rx="1.3" fill="#ffffff" />
      <circle cx="50" cy="21.6" r="1.2" fill="#ffc861" />
    </g>
  );
}

function Octopus() {
  return (
    <g>
      {[14, 22, 30, 38, 46].map((x, i) => (
        <path
          key={x}
          d={`M${x + 2} 38 q${i % 2 ? 4 : -4} 6 0 11 q${i % 2 ? -4 : 4} 4 0 7`}
          stroke="#ff8a9e"
          strokeWidth="4.2"
          fill="none"
          strokeLinecap="round"
        />
      ))}
      <path d="M14 38 q0 -24 18 -24 q18 0 18 24 z" fill="#ff8a9e" />
      <circle cx="25.5" cy="29" r="4.3" fill="#fff" />
      <circle cx="38.5" cy="29" r="4.3" fill="#fff" />
      <circle cx="26.3" cy="29.6" r="2" fill="#0a2e52" />
      <circle cx="39.3" cy="29.6" r="2" fill="#0a2e52" />
      <path d="M28.5 35 q3.5 2.6 7 0" stroke="#0a2e52" strokeWidth="1.5" fill="none" strokeLinecap="round" />
      <circle cx="21" cy="21" r="2.2" fill="#ffb3c0" />
      <circle cx="43" cy="22" r="1.6" fill="#ffb3c0" />
    </g>
  );
}

function Pelican() {
  return (
    <g>
      <ellipse cx="24" cy="40" rx="14" ry="11" fill="#ffffff" stroke="#c9d6e3" strokeWidth="1.5" />
      <path d="M14 38 q8 -6 18 2 q-9 6 -18 -2z" fill="#dfe8f1" />
      <path d="M20 50 v6 M28 50 v6" stroke="#f0a43a" strokeWidth="2.4" strokeLinecap="round" />
      <circle cx="38" cy="22" r="8" fill="#ffffff" stroke="#c9d6e3" strokeWidth="1.5" />
      <path d="M44 20 L60 25 L44 26.5 z" fill="#ffb347" />
      <path d="M44 26.5 L60 25 q-4 9 -15 7 z" fill="#ffcf7a" />
      <circle cx="51" cy="29" r="2.6" fill="#f2c94c" stroke="#d9a520" strokeWidth="0.8" />
      <circle cx="39.5" cy="20" r="1.6" fill="#0a2e52" />
      <path d="M32 33 q-2 3 -2 7" stroke="#c9d6e3" strokeWidth="1.4" fill="none" />
    </g>
  );
}

function HermitCrab() {
  return (
    <g>
      <path d="M16 46 q-6 -2 -6 -7 M22 48 l-3 6 M28 49 l0 6 M34 48 l3 6" stroke="#e8613f" strokeWidth="2.6" fill="none" strokeLinecap="round" />
      <ellipse cx="25" cy="44" rx="11" ry="6.5" fill="#ff7a59" />
      <circle cx="11" cy="38" r="5" fill="#ff7a59" />
      <path d="M8.5 36 l5 4" stroke="#e8613f" strokeWidth="1.4" />
      <path d="M21 39 v-9 M28 39 v-10" stroke="#e8613f" strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="21" cy="29" r="3" fill="#fff" />
      <circle cx="28" cy="28" r="3" fill="#fff" />
      <circle cx="21.6" cy="29.3" r="1.4" fill="#0a2e52" />
      <circle cx="28.6" cy="28.3" r="1.4" fill="#0a2e52" />
      <circle cx="41" cy="33" r="15" fill="#f6c87e" />
      <path
        d="M41 33 m0 -2 a2 2 0 1 1 -0.1 4 a5 5 0 1 1 5 -6 a9 9 0 1 1 -12 -4 a13 13 0 0 1 14 -2"
        stroke="#c98a3a"
        strokeWidth="2"
        fill="none"
        strokeLinecap="round"
      />
    </g>
  );
}

function Dolphin() {
  return (
    <g>
      <path d="M9 41 C 14 25, 39 15, 54 26 C 50 27.5, 47 29.5, 45 33 C 37 41, 21 45, 9 41 Z" fill="#5aa9e6" />
      <path d="M14 40 C 24 42, 36 39, 44 33 C 36 36, 24 38, 14 40 Z" fill="#d6ecfb" />
      <path d="M30 22 q2 -8 9 -9 q-3 5 -2 9 z" fill="#4a95d0" />
      <path d="M11 40 q-6 -1 -8 -6 q5 1 8 3 q1 -5 5 -7 q-1 5 -2 9 z" fill="#4a95d0" />
      <circle cx="46.5" cy="26.5" r="1.7" fill="#0a2e52" />
      <path d="M49 31 q3 0.8 5 -1.6" stroke="#0a2e52" strokeWidth="1.3" fill="none" strokeLinecap="round" />
      <circle cx="56" cy="15" r="2.3" fill="none" stroke="#9fd0f3" strokeWidth="1.3" />
      <circle cx="59.5" cy="9" r="1.5" fill="none" stroke="#9fd0f3" strokeWidth="1.2" />
    </g>
  );
}

function Sunny() {
  // the human at the desk
  return (
    <g>
      {Array.from({ length: 8 }).map((_, i) => (
        <rect key={i} x="30.5" y="5" width="3" height="9" rx="1.5" fill="#ffb347" transform={`rotate(${i * 45} 32 32)`} />
      ))}
      <circle cx="32" cy="32" r="15" fill="#ffc861" />
      <circle cx="27" cy="30" r="1.8" fill="#0a2e52" />
      <circle cx="37" cy="30" r="1.8" fill="#0a2e52" />
      <path d="M26.5 36 q5.5 4.5 11 0" stroke="#0a2e52" strokeWidth="1.8" fill="none" strokeLinecap="round" />
    </g>
  );
}

function Sunrise() {
  return (
    <g>
      <circle cx="32" cy="40" r="13" fill="#ffc861" />
      <rect x="6" y="40" width="52" height="18" fill="#7cc4ef" />
      <path d="M6 44 q6.5 -4 13 0 t13 0 t13 0 t13 0" stroke="#fff" strokeWidth="2" fill="none" />
    </g>
  );
}

export function Avatar({ agent, size = 40, ring = true }: { agent: string; size?: number; ring?: boolean }) {
  const role = isRole(agent) ? agent : null;
  const art =
    role === "boss" ? <Turtle /> :
    role === "inventory" ? <Octopus /> :
    role === "accounting" ? <Pelican /> :
    role === "facilities" ? <HermitCrab /> :
    role === "customer_service" ? <Dolphin /> :
    agent === "system" ? <Sunrise /> : <Sunny />;
  return (
    <svg
      className="avatar"
      width={size}
      height={size}
      viewBox="0 0 64 64"
      role="img"
      aria-label={role ? `${AGENTS[role].name} (${AGENTS[role].creature})` : agentName(agent)}
      style={{ boxShadow: ring ? `0 0 0 2px #fff, 0 0 0 4px ${agentColor(agent)}33` : undefined }}
    >
      <circle cx="32" cy="32" r="32" fill={agentTint(agent)} />
      {art}
    </svg>
  );
}
