// Identidad y comportamiento del tótem, configurables por despliegue (multi-condominio, RNF-10).
const env = import.meta.env;

const flag = (value: string | undefined, fallback: boolean) =>
  value === undefined || value === "" ? fallback : value.toLowerCase() === "true";

const hour = (value: string | undefined, fallback: number) => {
  const n = Number(value);
  return Number.isInteger(n) && n >= 0 && n <= 23 ? n : fallback;
};

export const config = {
  buildingName: env.VITE_BUILDING_NAME || "Condominio",
  buildingLocation: env.VITE_BUILDING_LOCATION || "",
  unitName: env.VITE_UNIT_NAME || "Unidad 01",
  // Portón, intercomunicador, alerta y aviso al residente aún no están conectados a hardware real
  simulation: flag(env.VITE_SIMULATION, true),
  nightFrom: hour(env.VITE_NIGHT_FROM, 18),
  nightTo: hour(env.VITE_NIGHT_TO, 6),
};

const params = new URLSearchParams(window.location.search);

// ?demo muestra los controles de simulación; nunca se muestran al visitante por defecto
export const demoMode = params.has("demo");

// ?tema=dia|noche fuerza una iluminación; si no, se decide por la hora
const forcedTheme = params.get("tema");

export function themeForNow(date = new Date()): "day" | "night" {
  if (forcedTheme === "dia") return "day";
  if (forcedTheme === "noche") return "night";
  const h = date.getHours();
  const { nightFrom, nightTo } = config;
  const isNight = nightFrom > nightTo ? h >= nightFrom || h < nightTo : h >= nightFrom && h < nightTo;
  return isNight ? "night" : "day";
}

export function greetingForNow(date = new Date()) {
  const h = date.getHours();
  if (h < 5) return "Buenas noches";
  if (h < 12) return "Buenos días";
  if (h < 19) return "Buenas tardes";
  return "Buenas noches";
}
