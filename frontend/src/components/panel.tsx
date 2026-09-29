import { type ReactNode } from "react";
import { motion, useReducedMotion } from "motion/react";
import { Delete } from "lucide-react";

/* ---------- Teclas del panel del videoportero ---------- */

type KeyTone = "call" | "key" | "quiet" | "alert";

const keyTone: Record<KeyTone, string> = {
  call: "keycap-call bg-call text-orange-ink",
  key: "keycap bg-key text-key-ink border-[0.125rem] border-key-edge",
  quiet: "keycap bg-panel text-key-ink border-[0.125rem] border-key-edge",
  alert: "keycap bg-panel text-no border-[0.125rem] border-no",
};

export function PanelKey({
  tone = "key",
  icon,
  children,
  hint,
  stacked,
  className = "",
  ...rest
}: {
  tone?: KeyTone;
  icon?: ReactNode;
  children: ReactNode;
  hint?: ReactNode;
  // Icono sobre la etiqueta: para las teclas pequeñas de la fila del marco
  stacked?: boolean;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      {...rest}
      className={`relative flex min-h-[3rem] rounded-[0.9rem] font-semibold leading-tight ${stacked ? "flex-col items-center justify-center gap-[0.25rem] px-[0.5rem] py-[0.5rem] text-center text-[1rem]" : "items-center gap-[0.8rem] px-[1.1rem] py-[0.6rem] text-left text-[1.2rem]"} disabled:cursor-not-allowed disabled:opacity-45 cursor-pointer ${keyTone[tone]} ${className}`}
    >
      {icon && <span className={`shrink-0 [&>svg]:h-[1.35em] [&>svg]:w-[1.35em] ${tone === "key" || tone === "quiet" ? "text-legend" : ""}`}>{icon}</span>}
      <span className="flex flex-col">
        <span>{children}</span>
        {hint && <span className="text-[1rem] font-normal">{hint}</span>}
      </span>
    </button>
  );
}

/* ---------- Corchetes de enfoque: se cierran sobre lo activo ---------- */

export function FocusBrackets({ color = "var(--legend)" }: { color?: string }) {
  const reduced = useReducedMotion();
  const corner = "absolute h-[1.4rem] w-[1.4rem]";
  const s = { borderColor: color };
  return (
    <motion.span
      aria-hidden
      className="pointer-events-none absolute inset-0"
      initial={reduced ? false : { opacity: 0, scale: 1.12 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
    >
      <span style={s} className={`${corner} -left-[0.55rem] -top-[0.55rem] rounded-tl-[0.5rem] border-l-[0.22rem] border-t-[0.22rem]`} />
      <span style={s} className={`${corner} -right-[0.55rem] -top-[0.55rem] rounded-tr-[0.5rem] border-r-[0.22rem] border-t-[0.22rem]`} />
      <span style={s} className={`${corner} -bottom-[0.55rem] -left-[0.55rem] rounded-bl-[0.5rem] border-b-[0.22rem] border-l-[0.22rem]`} />
      <span style={s} className={`${corner} -bottom-[0.55rem] -right-[0.55rem] rounded-br-[0.5rem] border-b-[0.22rem] border-r-[0.22rem]`} />
    </motion.span>
  );
}

/* ---------- Marca literal de lo simulado ---------- */

export function SimTag({ children = "Simulado" }: { children?: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-[0.4rem] rounded-[0.4rem] border-[0.1rem] border-dashed border-current px-[0.5rem] py-[0.1rem] text-[1rem] font-semibold uppercase tracking-[0.04em]">
      <span aria-hidden className="sim-tag inline-block h-[0.8rem] w-[1.2rem]" />
      {children}
    </span>
  );
}

/* ---------- Ficha de la visita: una sola rejilla de etiqueta ---------- */

export type LedgerField = "apartment" | "nombre" | "cedula" | "telefono" | "motivo";

export const fieldLabel: Record<LedgerField, string> = {
  apartment: "Destino",
  nombre: "Visitante",
  cedula: "Cédula",
  telefono: "Teléfono",
  motivo: "Motivo",
};

// En pantalla pública la cédula y el teléfono nunca se muestran completos
export function maskValue(field: LedgerField, value?: string) {
  if (!value) return value;
  if (field === "cedula") {
    const prefix = /^[VEve]/.test(value) ? `${value[0].toUpperCase()}-` : "";
    const digits = value.replace(/\D/g, "");
    return digits.length > 4 ? `${prefix}${digits.slice(0, 2)}•••${digits.slice(-2)}` : `${prefix}${digits}`;
  }
  if (field === "telefono") {
    const digits = value.replace(/\D/g, "");
    return digits.length > 6 ? `${digits.slice(0, 4)}•••${digits.slice(-2)}` : digits;
  }
  if (field === "apartment") return `Apto ${value}`;
  return value;
}

export function VisitCard({
  values,
  fields = ["apartment", "nombre", "cedula", "telefono", "motivo"],
  active,
  onlyFilled,
}: {
  values: Partial<Record<LedgerField, string>>;
  fields?: LedgerField[];
  active?: LedgerField | null;
  // En resultados solo se muestran los datos que existen: nada de casillas vacías
  onlyFilled?: boolean;
}) {
  const reduced = useReducedMotion();
  if (onlyFilled) fields = fields.filter((f) => values[f]);
  if (!fields.length) return null;
  return (
    <dl aria-label="Datos de la visita" className="grid grid-cols-[repeat(auto-fit,minmax(9rem,1fr))] gap-x-[1.4rem] gap-y-[0.6rem]">
      {fields.map((f) => {
        const shown = maskValue(f, values[f]);
        return (
          <div key={f} className={`border-b-[0.15rem] pb-[0.3rem] ${active === f ? "border-legend" : "border-key-edge"}`}>
            <dt className="text-[1rem] font-medium text-ink-soft">{fieldLabel[f]}</dt>
            <dd className="min-h-[2rem] truncate text-[1.5rem] font-semibold tabular-nums text-ink">
              {shown ? (
                <motion.span key={shown} initial={reduced ? false : { opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
                  {shown}
                </motion.span>
              ) : (
                <span aria-hidden className="text-ink-soft/60">—</span>
              )}
            </dd>
          </div>
        );
      })}
    </dl>
  );
}

/* ---------- Teclados en pantalla ---------- */

function Key({ label, onPress, wide, aria }: { label: ReactNode; onPress: () => void; wide?: boolean; aria?: string }) {
  const word = typeof label === "string" && label.length > 3;
  return (
    <button
      type="button"
      aria-label={aria}
      onClick={onPress}
      className={`keycap flex min-h-[3rem] items-center justify-center rounded-[0.7rem] border-[0.125rem] border-key-edge bg-key font-semibold text-key-ink cursor-pointer ${word ? "text-[1.05rem]" : "text-[1.5rem]"} ${wide ? "col-span-2" : ""}`}
    >
      {label}
    </button>
  );
}

const backspace = <Delete className="h-[1.4em] w-[1.4em]" />;

// Apartamento: dígitos, letras frecuentes, guion y PH; «Letras» abre el alfabeto completo
export function AptKeypad({ onKey, onDelete, letters, onLetters }: { onKey: (k: string) => void; onDelete: () => void; letters: boolean; onLetters: (v: boolean) => void }) {
  if (letters) {
    return (
      <div className="flex flex-col gap-[0.5rem]">
        <AlphaKeyboard onKey={onKey} onDelete={onDelete} />
        <Key label="123 · Números" onPress={() => onLetters(false)} />
      </div>
    );
  }
  const keys = ["1", "2", "3", "A", "B", "4", "5", "6", "C", "D", "7", "8", "9", "-", "PH"];
  return (
    <div className="grid grid-cols-5 gap-[0.6rem]">
      {keys.map((k) => (
        <Key key={k} label={k} aria={k === "-" ? "Guion" : k === "PH" ? "Pent-house" : undefined} onPress={() => onKey(k)} />
      ))}
      <Key label={backspace} aria="Borrar" onPress={onDelete} />
      <Key label="0" onPress={() => onKey("0")} />
      <Key label="Letras" wide onPress={() => onLetters(true)} />
      <Key label="Espacio" onPress={() => onKey(" ")} />
    </div>
  );
}

export function NumberPad({ onKey, onDelete, prefixKeys }: { onKey: (k: string) => void; onDelete: () => void; prefixKeys?: string[] }) {
  return (
    <div className="grid grid-cols-3 gap-[0.6rem]">
      {["1", "2", "3", "4", "5", "6", "7", "8", "9"].map((k) => (
        <Key key={k} label={k} onPress={() => onKey(k)} />
      ))}
      {prefixKeys?.length ? (
        <div className="grid grid-cols-2 gap-[0.6rem]">
          {prefixKeys.map((p) => (
            <Key key={p} label={p} onPress={() => onKey(p)} />
          ))}
        </div>
      ) : (
        <span />
      )}
      <Key label="0" onPress={() => onKey("0")} />
      <Key label={backspace} aria="Borrar" onPress={onDelete} />
    </div>
  );
}

export function AlphaKeyboard({ onKey, onDelete }: { onKey: (k: string) => void; onDelete: () => void }) {
  const rows = ["QWERTYUIOP", "ASDFGHJKLÑ", "ZXCVBNM"];
  return (
    <div className="flex flex-col gap-[0.5rem]">
      {rows.map((row, i) => (
        <div key={row} className="grid gap-[0.5rem]" style={{ gridTemplateColumns: `repeat(${i === 2 ? 9 : 10}, minmax(0, 1fr))` }}>
          {row.split("").map((k) => (
            <Key key={k} label={k} onPress={() => onKey(k)} />
          ))}
          {i === 2 && <Key label={backspace} aria="Borrar" wide onPress={onDelete} />}
        </div>
      ))}
      <Key label="Espacio" onPress={() => onKey(" ")} />
    </div>
  );
}
