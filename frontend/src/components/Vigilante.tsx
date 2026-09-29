import { motion, useReducedMotion } from "motion/react";

export type Mood = "idle" | "listening" | "thinking" | "talking" | "happy" | "sad" | "sorry" | "waiting";

const moodLabel: Record<Mood, string> = {
  idle: "atento",
  listening: "escuchando",
  thinking: "pensando",
  talking: "hablando",
  happy: "contento",
  sad: "apenado",
  sorry: "disculpándose",
  waiting: "esperando",
};

// El Vigilante Virtual, dibujado con el trazo lineal del logo de Soft-IA:
// líneas de grosor constante, puntas redondas, barras de acento celeste y naranja y un trazo de circuito.
// fit="slice": primer plano que llena una ventana alta; fit="meet": figura completa en una ventana ancha
export default function Vigilante({ mood, className = "", fit = "slice" }: { mood: Mood; className?: string; fit?: "slice" | "meet" }) {
  const reduced = useReducedMotion();
  const stroke = { stroke: "var(--line)", strokeWidth: 9, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, fill: "none" };
  const tilt = mood === "listening" ? -5 : mood === "thinking" ? 4 : 0;

  return (
    <svg viewBox={fit === "slice" ? "30 64 340 330" : "70 78 260 292"} preserveAspectRatio={`xMidYMid ${fit}`} className={className} role="img" aria-label={`Vigilante Virtual, ${moodLabel[mood]}`}>
      {/* Barras de acento del logo */}
      <g strokeLinecap="round" strokeWidth={9}>
        <line x1="22" y1="296" x2="86" y2="296" stroke="var(--sky)" />
        <line x1="10" y1="324" x2="104" y2="324" stroke="var(--orange)" />
        <line x1="316" y1="296" x2="388" y2="296" stroke="var(--sky)" />
        <line x1="300" y1="324" x2="378" y2="324" stroke="var(--blue)" />
      </g>

      {/* Trazo de circuito con nodos; al pensar, los nodos se encienden en secuencia */}
      <line x1="34" y1="382" x2="366" y2="382" {...stroke} strokeWidth={7} />
      <circle cx="24" cy="382" r="10" {...stroke} strokeWidth={7} />
      <circle cx="376" cy="382" r="10" {...stroke} strokeWidth={7} />
      {[140, 200, 260].map((x, i) => (
        <motion.circle
          key={x}
          cx={x}
          cy={382}
          r={8}
          fill={mood === "happy" ? "var(--ok)" : mood === "sad" ? "var(--no)" : "var(--sky)"}
          initial={false}
          animate={
            mood === "thinking" && !reduced
              ? { opacity: [0.15, 1, 0.15] }
              : { opacity: mood === "happy" || mood === "sad" || mood === "waiting" ? 1 : 0 }
          }
          transition={mood === "thinking" ? { duration: 1.2, repeat: Infinity, delay: i * 0.25 } : { duration: 0.3, delay: i * 0.08 }}
        />
      ))}

      {/* Uniforme: hombros, cuello en V, corbata y placa */}
      <path d="M72 372 C 78 316, 128 290, 200 290 C 272 290, 322 316, 328 372" {...stroke} />
      <path d="M168 292 L200 332 L232 292" {...stroke} />
      <path d="M200 332 L200 372" {...stroke} />
      <path d="M238 326 l16 -6 l16 6 l0 14 c0 10 -8 16 -16 20 c-8 -4 -16 -10 -16 -20 z" stroke="var(--orange)" strokeWidth={7} strokeLinejoin="round" fill="none" />

      <motion.g animate={{ rotate: tilt }} transition={{ type: "spring", stiffness: 120, damping: 14 }} style={{ originX: "200px", originY: "270px" }}>
        {/* Cuello y cabeza */}
        <path d="M180 262 L180 290 M220 262 L220 290" {...stroke} />
        <ellipse cx="200" cy="196" rx="70" ry="76" {...stroke} fill="var(--screen)" />
        {/* Orejas */}
        <path d="M130 184 c-14 0 -18 26 0 28" {...stroke} />
        <path d="M270 184 c14 0 18 26 0 28" {...stroke} />

        {/* Gorra con visera y distintivo */}
        <path d="M126 146 C 124 92, 276 92, 274 146 Z" {...stroke} fill="var(--screen)" />
        <path d="M112 148 L288 148" {...stroke} />
        <path d="M150 150 C 176 166, 224 166, 250 150" {...stroke} strokeWidth={7} />
        <path d="M200 106 l9 6 l-3 11 h-12 l-3 -11 z" fill="var(--orange)" stroke="var(--orange)" strokeWidth={4} strokeLinejoin="round" />

        {/* Ojos */}
        {mood === "happy" ? (
          <g {...stroke}>
            <path d="M160 200 Q174 186 188 200" />
            <path d="M212 200 Q226 186 240 200" />
          </g>
        ) : mood === "sad" || mood === "sorry" ? (
          <g {...stroke}>
            <path d="M160 184 L186 174" strokeWidth={7} />
            <path d="M240 184 L214 174" strokeWidth={7} />
            <path d="M174 196 L174 210 M226 196 L226 210" />
          </g>
        ) : (
          <g className={reduced ? "" : "vig-eyes"} {...stroke}>
            {mood === "thinking" || mood === "waiting" ? (
              <path d="M182 188 L182 202 M234 188 L234 202" />
            ) : mood === "listening" ? (
              <path d="M174 184 L174 206 M226 184 L226 206" strokeWidth={11} />
            ) : (
              <path d="M174 190 L174 206 M226 190 L226 206" />
            )}
          </g>
        )}

        {/* Boca */}
        {mood === "talking" ? (
          <motion.ellipse
            cx="200"
            cy="238"
            rx="16"
            {...stroke}
            strokeWidth={8}
            initial={{ ry: 4 }}
            animate={reduced ? { ry: 8 } : { ry: [4, 11, 6, 12, 4] }}
            transition={{ duration: 0.9, repeat: Infinity }}
          />
        ) : mood === "happy" ? (
          <path d="M170 228 Q200 262 230 228" {...stroke} />
        ) : mood === "sad" ? (
          <path d="M184 240 Q200 234 216 240" {...stroke} />
        ) : mood === "sorry" ? (
          <path d="M184 236 L216 236" {...stroke} />
        ) : mood === "thinking" || mood === "waiting" ? (
          <path d="M186 238 L214 238" {...stroke} />
        ) : (
          <path d="M178 232 Q200 248 222 232" {...stroke} />
        )}
      </motion.g>

      {/* Ondas de escucha junto a la oreja */}
      {mood === "listening" &&
        [0, 1].map((i) => (
          <motion.path
            key={i}
            d={i === 0 ? "M298 170 Q314 198 298 226" : "M318 156 Q344 198 318 240"}
            stroke="var(--sky)"
            strokeWidth={8}
            strokeLinecap="round"
            fill="none"
            initial={{ opacity: 0.2 }}
            animate={reduced ? { opacity: 1 } : { opacity: [0.2, 1, 0.2] }}
            transition={{ duration: 1.1, repeat: Infinity, delay: i * 0.3 }}
          />
        ))}
    </svg>
  );
}
