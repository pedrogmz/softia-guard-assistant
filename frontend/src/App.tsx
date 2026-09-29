import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { ArrowLeft, Check, CheckCircle2, CircleHelp, Clock, Hash, Mic, QrCode, RotateCcw, Siren, SkipForward, Square, UserCheck, WifiOff, X, XCircle } from "lucide-react";
import QrScanner from "./components/QrScanner";
import IdScanner from "./components/IdScanner";
import Vigilante, { type Mood } from "./components/Vigilante";
import { AlphaKeyboard, AptKeypad, FocusBrackets, NumberPad, PanelKey, SimTag, VisitCard, fieldLabel, type LedgerField } from "./components/panel";
import { config, demoMode, greetingForNow, themeForNow } from "./config";

interface Message {
  role: "user" | "assistant";
  text: string;
  // false: registro del sistema (dato tecleado, QR, cédula por cámara), nunca se cita como palabras del visitante
  quote?: boolean;
}

// Diálogo de recolección de datos faltantes antes de autorizar
// requestMode: sin autorización vigente -> se recogen datos para pedirla al propietario (WhatsApp)
interface Identity {
  auth_id: string | null;
  nombre?: string;
  cedula?: string;
  telefono?: string;
  apartment?: string;
  motivo?: string;
  requestMode?: boolean;
  awaiting: LedgerField | null;
}

// Espera de la respuesta del propietario a la solicitud por WhatsApp (vía Soft-IA)
interface OwnerWait {
  id: string;
  remaining: number;
  apt: string | null;
  offline: boolean;
}

type Outcome = { kind: "ok" | "no" | "error" | "info" };
type Screen = "none" | "apartment" | "help" | "panic-confirm" | "panic";
type View = "home" | "apartment" | "step" | "wait" | "calling" | "result" | "help" | "panic-confirm" | "panic";

const FIELD_ORDER: LedgerField[] = ["apartment", "nombre", "cedula", "telefono", "motivo"];
const RESULT_RESET_S = 15;
const IDLE_RESET_MS = 60000;
const RECORD_LIMIT_MS = 10000;
const APT_MAX = 10;

const welcomeLine = () => `${greetingForNow()}. ¿A qué apartamento viene?`;

// Validación mínima antes de enviar cada dato (prevención de errores)
function draftProblem(field: LedgerField, draft: string): string | null {
  const v = draft.trim();
  if (field === "motivo") return null;
  if (!v) return "Falta este dato.";
  if (field === "nombre" && v.split(/\s+/).length < 2) return "Escriba nombre y apellido.";
  if (field === "cedula" && v.replace(/\D/g, "").length < 6) return "La cédula tiene al menos 6 números.";
  if (field === "telefono" && v.replace(/\D/g, "").length < 10) return "Escriba el número completo, con el código (0414…).";
  return null;
}

const stepPrompt: Record<LedgerField, string> = {
  apartment: "¿A qué apartamento va?",
  nombre: "¿Cuál es su nombre completo?",
  cedula: "¿Cuál es su número de cédula?",
  telefono: "¿Cuál es su número de teléfono?",
  motivo: "¿Cuál es el motivo de su visita?",
};

export default function App() {
  const reduced = useReducedMotion();

  // Cada visitante empieza una visita nueva (la pantalla se reinicia)
  const [visitId, setVisitId] = useState(0);
  const [screen, setScreen] = useState<Screen>("none");
  const [now, setNow] = useState(() => new Date());
  const [theme, setTheme] = useState(() => themeForNow());
  // La orientación del tótem aún no está decidida: el layout se recompone en vertical
  const [portrait, setPortrait] = useState(() => window.matchMedia("(orientation: portrait)").matches);
  useEffect(() => {
    const mq = window.matchMedia("(orientation: portrait)");
    const on = () => setPortrait(mq.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);

  // Apartamento marcado en el teclado
  const [apartmentInput, setApartmentInput] = useState<string>("");
  const [aptLetters, setAptLetters] = useState(false);

  // Conversación (el historial alimenta /api/verify; en pantalla solo la última frase)
  const [chatHistory, setChatHistory] = useState<Message[]>([{ role: "assistant", text: welcomeLine() }]);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  // Transcribiendo el audio de voz en el backend (feedback tras hablar)
  const [isTranscribing, setIsTranscribing] = useState<boolean>(false);
  const [isListening, setIsListening] = useState<boolean>(false);
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false);
  // Fallos seguidos de voz: a partir de dos se sugiere continuar por toque
  const [voiceMisses, setVoiceMisses] = useState(0);
  const [micUnavailable, setMicUnavailable] = useState(false);

  // Escáneres de cámara
  const [qrScannerOpen, setQrScannerOpen] = useState<boolean>(false);
  const [idScannerOpen, setIdScannerOpen] = useState<boolean>(false);

  // Datos de la visita (la fila de hoy) y diálogo de datos faltantes
  const [ledger, setLedger] = useState<Partial<Record<LedgerField, string>>>({});
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [askedFields, setAskedFields] = useState<LedgerField[]>([]);
  const [stepDraft, setStepDraft] = useState("");
  // La cédula se lee por cámara; si el visitante prefiere, la escribe en el teclado
  const [cedulaTyping, setCedulaTyping] = useState(false);

  const [ownerWait, setOwnerWait] = useState<OwnerWait | null>(null);
  const ownerPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const ownerWaitIdRef = useRef<string | null>(null);

  // Resultado de la visita y acciones simuladas
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [calling, setCalling] = useState<string | null>(null);
  const [resetIn, setResetIn] = useState(0);
  const callingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // STT local: grabación de audio con MediaRecorder (Whisper corre en el backend)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  // Auto-stop de seguridad para no dejar el micrófono grabando indefinidamente
  const recordTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastActivityRef = useRef(Date.now());

  const busy = isProcessing || isTranscribing;
  const voiceTrouble = micUnavailable || voiceMisses >= 2;

  const lastAssistant = [...chatHistory].reverse().find((m) => m.role === "assistant")?.text ?? welcomeLine();
  const lastUser = [...chatHistory].reverse().find((m) => m.role === "user" && m.quote !== false)?.text;

  const view: View =
    screen === "panic" ? "panic"
    : screen === "panic-confirm" ? "panic-confirm"
    : screen === "help" ? "help"
    : ownerWait ? "wait"
    : calling ? "calling"
    : identity?.awaiting && (identity.awaiting !== "cedula" || cedulaTyping) ? "step"
    : screen === "apartment" ? "apartment"
    : outcome ? "result"
    : "home";


  // ---------- Reloj, iluminación día/noche y color del condominio ----------

  useEffect(() => {
    const t = setInterval(() => {
      const d = new Date();
      setNow(d);
      setTheme(themeForNow(d));
    }, 20000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  useEffect(() => {
    document.title = `SoftiaGuard · ${config.buildingName}`;
  }, []);

  // ---------- Voz ----------

  // Speech Synthesis Helper
  const speakText = (text: string) => {
    try {
      // Cancel any ongoing speech
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "es-VE";
      utterance.pitch = 1.0;
      utterance.rate = 1.05;
      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);
      window.speechSynthesis.speak(utterance);
    } catch (error) {
      console.error("Text-to-speech error:", error);
    }
  };

  const say = (text: string) => {
    setChatHistory((prev) => [...prev, { role: "assistant", text }]);
    speakText(text);
  };

  // Libera el micrófono del sistema deteniendo todas las pistas de audio.
  const releaseMicrophone = () => {
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    mediaStreamRef.current = null;
  };

  const clearRecordTimeout = () => {
    if (recordTimeoutRef.current) {
      clearTimeout(recordTimeoutRef.current);
      recordTimeoutRef.current = null;
    }
  };

  // La grabación termina en un callback antiguo: el contador vive en una referencia
  const voiceMissesRef = useRef(0);
  voiceMissesRef.current = voiceMisses;
  const missVoice = (text: string) => {
    const next = voiceMissesRef.current + 1;
    voiceMissesRef.current = next;
    setVoiceMisses(next);
    say(next >= 2 ? "Disculpe, no logro escucharle bien. Puede continuar tocando la pantalla: marque el apartamento o muestre su código QR." : text);
  };

  // Envía el clip grabado al backend (Whisper local) y usa la transcripción.
  const transcribeAndSend = async (blob: Blob) => {
    if (blob.size === 0) return;
    setIsTranscribing(true);
    try {
      const formData = new FormData();
      formData.append("file", blob, "audio.webm");
      const res = await fetch("/api/transcribe", { method: "POST", body: formData });
      if (!res.ok) throw new Error(`STT HTTP ${res.status}`);
      const data = await res.json();
      const text = (data.text || "").trim();
      if (text) {
        setVoiceMisses(0);
        setIsTranscribing(false);
        userInputRef.current(text); // toma el relevo del feedback con isProcessing
        return;
      }
      // No se entendió el audio: dar feedback explícito (visual + hablado)
      missVoice("Disculpe, no le entendí bien. ¿Podría repetirlo, por favor?");
    } catch (e) {
      console.error("Transcription failed:", e);
      missVoice("Disculpe, tuve un problema al escucharle. Por favor, intente de nuevo.");
    } finally {
      setIsTranscribing(false);
    }
  };

  const startListening = async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      console.error("getUserMedia no disponible (¿contexto seguro? usa localhost o HTTPS)");
      setMicUnavailable(true);
      say("El micrófono no está disponible en este momento. Use los botones de la pantalla.");
      return;
    }
    try {
      window.speechSynthesis.cancel();
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      audioChunksRef.current = [];

      const recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        clearRecordTimeout();
        releaseMicrophone(); // suelta el micrófono en cuanto termina la grabación
        setIsListening(false);
        const blob = new Blob(audioChunksRef.current, { type: recorder.mimeType || "audio/webm" });
        audioChunksRef.current = [];
        transcribeAndSend(blob);
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      setIsListening(true);

      // Red de seguridad: corta la grabación a los 10s
      clearRecordTimeout();
      recordTimeoutRef.current = setTimeout(() => stopListening(), RECORD_LIMIT_MS);
    } catch (e) {
      console.error("No se pudo acceder al micrófono:", e);
      releaseMicrophone();
      setIsListening(false);
      setMicUnavailable(true);
      say("El micrófono no está disponible en este momento. Use los botones de la pantalla.");
    }
  };

  const stopListening = () => {
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      recorder.stop(); // dispara onstop -> libera micrófono + transcribe
    } else {
      clearRecordTimeout();
      releaseMicrophone();
      setIsListening(false);
    }
  };

  const toggleListening = () => {
    if (isListening) stopListening();
    else startListening();
  };

  // Liberar el micrófono si el componente se desmonta mientras graba
  useEffect(() => {
    return () => {
      clearRecordTimeout();
      try {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
          mediaRecorderRef.current.stop();
        }
      } catch {
        /* noop */
      }
      releaseMicrophone();
    };
  }, []);

  // ---------- Respuestas del asistente ----------

  // ¿Qué dato pide el backend? (cédula por cámara; el resto por voz/teclado)
  const pickAwaiting = (data: any): LedgerField => {
    if (data.action === "show_id_scanner") return "cedula";
    const missing: LedgerField[] = data.missing || [];
    // En modo solicitud el backend ya los ordena (destino -> nombre -> cédula -> teléfono -> motivo)
    if (data.request_mode && missing.length) return missing[0];
    return (["telefono", "apartment", "nombre", "cedula"] as LedgerField[]).find((f) => missing.includes(f)) || "nombre";
  };

  // Aplica una respuesta del asistente a la UI (compartida por verify/verify-qr/identify)
  const applyAssistantResponse = (data: any, opts: { cancelled?: boolean } = {}) => {
    if (data.reply) say(data.reply);
    if (data.apartment) setLedger((prev) => ({ ...prev, apartment: data.apartment }));

    // Diálogo de datos faltantes: NO se ejecuta ninguna acción de hardware todavía
    const needsInfo = data.status === "NEED_INFO" || data.action === "collect_info" || data.action === "show_id_scanner";
    if (needsInfo) {
      const awaiting = pickAwaiting(data);
      // Orden de los pasos: primero lo ya preguntado, luego lo que falta en el orden del libro
      setAskedFields((prev) => [...prev, ...FIELD_ORDER.filter((f) => !prev.includes(f) && (f === awaiting || (data.missing || []).includes(f)))]);
      // Un dato que se vuelve a pedir no quedó aceptado: se borra de la fila
      setLedger((prev) => {
        if (!prev[awaiting]) return prev;
        const next = { ...prev };
        delete next[awaiting];
        return next;
      });
      setIdentity((prev) => ({
        ...(prev || { auth_id: null }),
        auth_id: data.auth_id ?? prev?.auth_id ?? null,
        requestMode: prev?.requestMode || !!data.request_mode,
        awaiting,
      }));
      setStepDraft("");
      setScreen("none");
      if (awaiting === "cedula" && !cedulaTyping) setIdScannerOpen(true);
      if (awaiting !== "cedula") setCedulaTyping(false);
      return;
    }

    // Fin del diálogo de identidad -> ejecutar la acción del tótem
    setIdentity(null);
    setIdScannerOpen(false);
    setScreen("none");
    if (data.action === "await_owner" && data.request_id) {
      startOwnerWait(data.request_id, data.expires_in, data.apartment);
      return;
    }
    if (opts.cancelled) {
      setOutcome({ kind: "info" });
      return;
    }
    handleTotemAction(data);
  };
  // El polling llama siempre a la versión más reciente (evita closures obsoletos)
  const applyRef = useRef(applyAssistantResponse);
  applyRef.current = applyAssistantResponse;

  // Ejecuta la acción del tótem según la decisión
  const handleTotemAction = (data: any) => {
    if (data.action === "open_gate") {
      setOutcome({ kind: "ok" });
    } else if (data.action === "ring_bell" && data.apartment) {
      // Intercomunicador simulado: el residente "contesta" a los 4 s
      setCalling(data.apartment);
      callingTimerRef.current = setTimeout(() => {
        setCalling(null);
        setOutcome({ kind: "ok" });
        say(`El residente del ${data.apartment} autorizó su visita. Pase adelante.`);
      }, 4000);
    } else if (data.action === "show_qr_scanner") {
      setQrScannerOpen(true);
    } else if (data.status === "DENIED") {
      setOutcome({ kind: "no" });
    } else if (data.status === "ERROR" || data.action === "show_error") {
      setOutcome({ kind: "error" });
    }
  };

  const stopOwnerWait = () => {
    if (ownerPollRef.current) clearInterval(ownerPollRef.current);
    ownerPollRef.current = null;
    ownerWaitIdRef.current = null;
    setOwnerWait(null);
  };

  // Espera la respuesta del propietario: cuenta regresiva local + consulta cada 3 s
  const startOwnerWait = (id: string, expiresIn: number | undefined, apt: string | null) => {
    stopOwnerWait();
    ownerWaitIdRef.current = id;
    setOwnerWait({ id, remaining: expiresIn ?? 120, apt, offline: false });
    let ticks = 0;
    let inFlight = false;
    ownerPollRef.current = setInterval(async () => {
      setOwnerWait((prev) => prev && { ...prev, remaining: Math.max(0, prev.remaining - 1) });
      if (++ticks % 3 !== 0 || inFlight) return;
      inFlight = true;
      try {
        const res = await fetch(`/api/access-request/${id}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (ownerWaitIdRef.current !== id) return; // cancelada mientras tanto
        if (data.status === "PENDING_CONFIRMATION") {
          setOwnerWait((prev) => prev && { ...prev, offline: false, remaining: typeof data.expires_in === "number" ? data.expires_in : prev.remaining });
        } else {
          stopOwnerWait();
          applyRef.current(data);
        }
      } catch (e) {
        console.warn("Access request poll failed (reintentando):", e);
        setOwnerWait((prev) => prev && { ...prev, offline: true });
      } finally {
        inFlight = false;
      }
    }, 1000);
  };

  // El visitante cancela la espera
  const handleCancelOwnerWait = async () => {
    const id = ownerWaitIdRef.current;
    if (!id) return;
    stopOwnerWait();
    try {
      const res = await fetch(`/api/access-request/${id}`, { method: "DELETE" });
      applyAssistantResponse(await res.json(), { cancelled: true });
    } catch (e) {
      console.error("Cancel access request failed:", e);
      say("Solicitud cancelada.");
      setOutcome({ kind: "info" });
    }
  };

  // Solo modo demo: el propietario pulsa Aprobar/Rechazar en el WhatsApp
  const simulateOwnerDecision = (decision: "aprobada" | "rechazada") => {
    const id = ownerWaitIdRef.current;
    if (!id) return;
    fetch(`/api/dev/access-request/${id}/respond`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision }),
    }).catch((e) => console.error("Simulated owner decision failed:", e));
  };

  useEffect(
    () => () => {
      if (ownerPollRef.current) clearInterval(ownerPollRef.current);
      if (callingTimerRef.current) clearTimeout(callingTimerRef.current);
    },
    []
  );

  // Cuerpo de /api/identify con los datos acumulados (motivo: undefined = aún no preguntado)
  const identityBody = (next: Identity) =>
    JSON.stringify({
      nombre: next.nombre,
      cedula: next.cedula,
      telefono: next.telefono,
      apartment: next.apartment,
      auth_id: next.auth_id,
      motivo: next.motivo,
      request_mode: !!next.requestMode,
    });

  // Enruta la entrada del visitante: si estamos recogiendo un dato, va a /api/identify
  const handleUserInput = (text: string) => {
    if (!text.trim() || busy) return;
    if (identity?.awaiting && (identity.awaiting !== "cedula" || cedulaTyping)) {
      submitIdentity(identity.awaiting, text);
    } else {
      handleSendRequest(text);
    }
  };
  const userInputRef = useRef(handleUserInput);
  userInputRef.current = handleUserInput;

  // Envía los datos acumulados a /api/identify (identificación + recolección)
  const submitIdentity = async (field: LedgerField, value: string) => {
    const clean = value.trim();
    const next: Identity = { ...(identity || { auth_id: null }), [field]: clean, awaiting: null };
    setIdentity(next);
    setLedger((prev) => ({ ...prev, [field]: clean || undefined }));
    // Omitir el motivo no es algo que el visitante haya dicho: no se cita
    // Cédula y teléfono ya se ven (enmascarados) en la fila: no se citan
    if (clean) setChatHistory((prev) => [...prev, { role: "user", text: clean, quote: field !== "cedula" && field !== "telefono" }]);
    setIsProcessing(true);
    try {
      const res = await fetch("/api/identify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: identityBody(next),
      });
      applyAssistantResponse(await res.json());
    } catch (e) {
      console.error("Identify failed:", e);
      say("Disculpe, no pude verificar sus datos en este momento. Intente de nuevo.");
      setIdentity({ ...next, awaiting: field });
    } finally {
      setIsProcessing(false);
    }
  };

  // Inicia la identificación de un invitado por nombre (sin QR)
  const handleStartGuest = () => {
    setIdentity({ auth_id: null, awaiting: "nombre" });
    setAskedFields(["nombre"]);
    setStepDraft("");
    say("Con gusto. Dígame o escriba su nombre completo para buscar su autorización.");
  };

  // Resultado del IdScanner: envía la foto de la cédula a OCR y continúa la identificación
  const handleCedulaCapture = async (blob: Blob) => {
    setIdScannerOpen(false);
    setIsProcessing(true);
    setChatHistory((prev) => [...prev, { role: "user", text: "Cédula presentada a la cámara", quote: false }]);
    try {
      const fd = new FormData();
      fd.append("file", blob, "cedula.jpg");
      fd.append("auth_id", identity?.auth_id || "");
      const res = await fetch("/api/verify-cedula", { method: "POST", body: fd });
      const data = await res.json();

      if (data.error || !data.cedula) {
        say("No pude leer su cédula con claridad. Muéstrela de nuevo a la cámara o escriba el número.");
        setIdScannerOpen(true);
        return;
      }
      if (data.match === false) {
        say("El nombre en la cédula no coincide con la autorización. Por favor, pida ayuda al vigilante de turno.");
        setIdentity(null);
        setOutcome({ kind: "no" });
        return;
      }
      const next: Identity = { ...(identity || { auth_id: null }), cedula: String(data.cedula), awaiting: null };
      setIdentity(next);
      setLedger((prev) => ({ ...prev, cedula: String(data.cedula) }));
      const res2 = await fetch("/api/identify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: identityBody(next),
      });
      applyAssistantResponse(await res2.json());
    } catch (e) {
      console.error("Cedula OCR failed:", e);
      say("Disculpe, hubo un problema al leer la cédula. Intente de nuevo o escriba el número.");
      setIdScannerOpen(true);
    } finally {
      setIsProcessing(false);
    }
  };

  // Consulta principal de acceso (voz, texto o apartamento marcado)
  // quote=false: la frase la compuso el tótem (apartamento marcado), no el visitante
  const handleSendRequest = async (userMsg: string, aptOverride?: string, quote = true) => {
    if (!userMsg.trim()) return;
    const history = chatHistory.slice(-6); // Keep context size reasonable
    setChatHistory((prev) => [...prev, { role: "user", text: userMsg, quote }]);
    setOutcome(null);
    setIsProcessing(true);

    try {
      const response = await fetch("/api/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMsg, history, currentAptInput: aptOverride ?? apartmentInput }),
      });
      applyAssistantResponse(await response.json());
    } catch (error) {
      console.error("Verification failed:", error);
      say("Disculpe, no puedo contactar con el sistema en este momento. Intente de nuevo en un momento o pida ayuda al vigilante de turno.");
      setOutcome({ kind: "error" });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleConfirmApartment = () => {
    const apt = apartmentInput.trim();
    if (!apt || busy) return;
    setLedger((prev) => ({ ...prev, apartment: apt }));
    setScreen("none");
    handleSendRequest(`Quiero visitar el apartamento ${apt}`, apt, false);
  };

  // Resultado del escáner: valida el código contra el backend (/api/verify-qr)
  const handleQrResult = async (code: string) => {
    setQrScannerOpen(false);
    setChatHistory((prev) => [...prev, { role: "user", text: "Código QR presentado", quote: false }]);
    setOutcome(null);
    setIsProcessing(true);
    speakText("Código QR detectado. Verificando.");
    try {
      const response = await fetch("/api/verify-qr", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code }),
      });
      applyAssistantResponse(await response.json());
    } catch (error) {
      console.error("QR verification failed:", error);
      say("Disculpe, no pude verificar el código en este momento. Intente de nuevo o marque el apartamento.");
      setOutcome({ kind: "error" });
    } finally {
      setIsProcessing(false);
    }
  };

  // ---------- Pasos de datos faltantes ----------

  const stepField = view === "step" ? (identity!.awaiting as LedgerField) : null;
  const stepIndex = stepField ? Math.max(0, askedFields.indexOf(stepField)) : 0;
  const stepProblem = stepField ? draftProblem(stepField, stepDraft) : null;

  const typeIntoStep = (k: string) => {
    if (!stepField) return;
    const max = stepField === "cedula" ? 10 : stepField === "telefono" ? 11 : stepField === "apartment" ? APT_MAX : 60;
    setStepDraft((d) => (d.length >= max ? d : d + k));
  };

  const submitStep = () => {
    if (!stepField || stepProblem || busy) return;
    submitIdentity(stepField, stepDraft);
  };

  // «Volver» desanda el camino exacto: el dato anterior se puede corregir
  const stepBack = () => {
    if (!stepField) return;
    const prev = askedFields[stepIndex - 1];
    if (prev) {
      setIdentity((id) => id && { ...id, awaiting: prev });
      setStepDraft((identity as any)?.[prev] || "");
    } else {
      setIdentity(null);
      setAskedFields([]);
      say(welcomeLine());
    }
  };

  const typeCedulaInstead = () => {
    setIdScannerOpen(false);
    setIdentity((id) => ({ ...(id || { auth_id: null }), awaiting: "cedula" }));
    setCedulaTyping(true);
    setStepDraft("");
    say("Escriba el número de su cédula y toque «Continuar».");
  };

  // ---------- Hoja nueva para el siguiente visitante ----------

  const resetVisit = () => {
    window.speechSynthesis.cancel();
    stopOwnerWait();
    if (callingTimerRef.current) clearTimeout(callingTimerRef.current);
    if (isListening) stopListening();
    setCalling(null);
    setOutcome(null);
    setIdentity(null);
    setAskedFields([]);
    setStepDraft("");
    setCedulaTyping(false);
    setLedger({});
    setApartmentInput("");
    setAptLetters(false);
    setQrScannerOpen(false);
    setIdScannerOpen(false);
    setScreen("none");
    setVoiceMisses(0);
    setMicUnavailable(false);
    setIsSpeaking(false);
    setChatHistory([{ role: "assistant", text: welcomeLine() }]);
    setVisitId((v) => v + 1);
  };
  const resetRef = useRef(resetVisit);
  resetRef.current = resetVisit;

  // Tras un resultado, la página pasa sola
  useEffect(() => {
    if (view !== "result") return;
    setResetIn(RESULT_RESET_S);
    const t = setInterval(() => {
      setResetIn((s) => {
        if (s <= 1) {
          clearInterval(t);
          resetRef.current();
          return 0;
        }
        return s - 1;
      });
    }, 1000);
    return () => clearInterval(t);
  }, [view, outcome]);

  // Inactividad: si nadie toca la pantalla, se vuelve al inicio
  useEffect(() => {
    const mark = () => (lastActivityRef.current = Date.now());
    window.addEventListener("pointerdown", mark);
    window.addEventListener("keydown", mark);
    return () => {
      window.removeEventListener("pointerdown", mark);
      window.removeEventListener("keydown", mark);
    };
  }, []);

  const idleGuardRef = useRef({ view, busy, isListening, dirty: false });
  idleGuardRef.current = { view, busy, isListening, dirty: chatHistory.length > 1 || Object.keys(ledger).length > 0 || qrScannerOpen || idScannerOpen };
  useEffect(() => {
    const t = setInterval(() => {
      const g = idleGuardRef.current;
      const held = g.busy || g.isListening || g.view === "wait" || g.view === "calling" || g.view === "panic" || g.view === "result";
      if (!held && (g.view !== "home" || g.dirty) && Date.now() - lastActivityRef.current > IDLE_RESET_MS) {
        lastActivityRef.current = Date.now();
        resetRef.current();
      }
    }, 5000);
    return () => clearInterval(t);
  }, []);

  // ---------- Teclado físico (mantenimiento y pruebas; el visitante usa la pantalla) ----------

  const keyHandlerRef = useRef<(e: KeyboardEvent) => void>(() => {});
  keyHandlerRef.current = (e: KeyboardEvent) => {
    const key = e.key;
    if (view === "apartment") {
      if (/^[0-9a-zA-Z -]$/.test(key)) setApartmentInput((v) => (v.length < APT_MAX ? v + key.toUpperCase() : v));
      else if (key === "Backspace") setApartmentInput((v) => v.slice(0, -1));
      else if (key === "Enter") handleConfirmApartment();
      else if (key === "Escape") setScreen("none");
    } else if (view === "step") {
      if (key.length === 1) typeIntoStep(stepField === "nombre" || stepField === "motivo" ? key.toUpperCase() : key);
      else if (key === "Backspace") setStepDraft((d) => d.slice(0, -1));
      else if (key === "Enter") submitStep();
      else if (key === "Escape") stepBack();
    }
  };
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => keyHandlerRef.current(e);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // ---------- Panel de emergencia ----------

  const confirmPanic = () => {
    setScreen("panic");
    speakText(
      config.simulation
        ? "Alerta de emergencia registrada. Este tótem todavía no está conectado a la central. Si es una emergencia real, llame al 9 1 1."
        : "Alerta de emergencia enviada al personal de seguridad. Mantenga la calma."
    );
  };

  // ---------- Presentación ----------

  const timeText = now.toLocaleTimeString("es-VE", { hour: "2-digit", minute: "2-digit", hour12: false });

  const phrase =
    view === "panic" ? "Alerta de emergencia"
    : view === "panic-confirm" ? "¿Necesita ayuda urgente?"
    : view === "help" ? "Así puede entrar"
    : isListening ? "Le escucho. Hable ahora."
    : isTranscribing ? "Un momento, estoy entendiendo lo que dijo…"
    : isProcessing ? "Un momento, estoy verificando…"
    : lastAssistant;

  // La franja de la pantalla nombra siempre el paso actual
  const stepName =
    view === "panic" || view === "panic-confirm" ? "Emergencia"
    : view === "help" ? "Ayuda"
    : isListening ? "Escuchando"
    : isTranscribing ? "Entendiendo"
    : isProcessing ? "Verificando"
    : view === "apartment" ? "Marcar apartamento"
    : view === "step" && stepField ? `Datos de la visita · ${fieldLabel[stepField]}`
    : view === "wait" ? "Esperando al residente"
    : view === "calling" ? "Llamando al residente"
    : view === "result" && outcome?.kind === "ok" ? "Acceso autorizado"
    : view === "result" && outcome?.kind === "no" ? "Acceso no autorizado"
    : view === "result" && outcome?.kind === "error" ? "Sin conexión"
    : view === "result" ? "Solicitud cancelada"
    : "Inicio";

  const mood: Mood =
    isListening ? "listening"
    : busy ? "thinking"
    : view === "result" && outcome?.kind === "ok" ? "happy"
    : view === "result" && outcome?.kind === "no" ? "sad"
    : view === "result" && outcome?.kind === "error" ? "sorry"
    : view === "panic" ? "sad"
    : view === "wait" || view === "calling" ? "waiting"
    : isSpeaking ? "talking"
    : "idle";

  const stateTone = view === "result" && outcome?.kind === "ok" ? "ok" : view === "result" && outcome?.kind === "no" ? "no" : view === "wait" || view === "calling" ? "wait" : null;
  const visitFields: LedgerField[] = ledger.nombre || view === "step" || view === "wait" ? ["apartment", "nombre", "cedula", "telefono", "motivo"] : ["apartment", "nombre"];

  const screenTurn = reduced
    ? {}
    : {
        initial: { opacity: 0, y: 24 },
        animate: { opacity: 1, y: 0 },
        exit: { opacity: 0, y: -24 },
        transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] as const },
      };

  return (
    <div className="brushed relative flex h-dvh w-full flex-col gap-[1.4rem] px-[1.4rem] pb-[2.4rem] pt-[2.2rem] landscape:flex-row">
      {/* Lente de la cámara del tótem, asentada en el marco */}
      <span aria-hidden className="absolute left-1/2 top-[0.55rem] h-[1rem] w-[1rem] -translate-x-1/2 rounded-full bg-[radial-gradient(circle_at_35%_35%,#6f90b0,#0b1522_62%)] shadow-[0_0_0_0.18rem_var(--bezel)]" />
      {/* Grabado del marco */}
      <p aria-hidden className="engraved absolute inset-x-0 bottom-[0.6rem] text-center text-[1rem] font-semibold uppercase tracking-[0.3em]">SoftiaGuard · Soft-IA</p>

      {/* Pantalla del Vigilante */}
      <main className="glass relative flex min-h-0 flex-col overflow-hidden rounded-[1.6rem] landscape:flex-[1.38] portrait:flex-[1.2]">
        <div className="flex items-center justify-between gap-[1rem] border-b-[0.12rem] border-screen-edge/60 px-[1.6rem] py-[0.7rem]">
          <p className="flex items-center gap-[0.6rem] text-[1.1rem] font-semibold text-ink">
            <span aria-hidden className={`inline-block h-[0.75rem] w-[0.75rem] rounded-full ${stateTone === "ok" ? "bg-ok" : stateTone === "no" ? "bg-no" : stateTone === "wait" || busy ? "bg-wait" : isListening ? "bg-call" : "bg-legend"}`} />
            {stepName}
          </p>
          <p className="text-[1.1rem] font-medium tabular-nums text-ink-soft">
            {[config.buildingName, timeText].join(" · ")}
          </p>
        </div>

        <AnimatePresence mode="wait" initial={false}>
          <motion.div key={visitId} {...screenTurn} className="flex min-h-0 flex-1 items-stretch gap-[1.4rem] px-[1.6rem] pb-[1.4rem] pt-[1rem] portrait:flex-col portrait:gap-[1rem]">
            {/* Ventana de video del Vigilante */}
            <div className={`relative flex shrink-0 flex-col overflow-hidden rounded-[1.2rem] shadow-[inset_0_0_0_0.12rem_var(--screen-edge)] landscape:w-[42%] portrait:h-[48%] portrait:w-full ${stateTone === "ok" ? "bg-ok-tint" : stateTone === "no" ? "bg-no-tint" : stateTone === "wait" ? "bg-wait-tint" : "bg-key"}`}>
              <div className="relative min-h-0 flex-1">
                {/* En el primer plano horizontal, las barras del logo de Soft-IA flanquean al Vigilante */}
                {!portrait && (
                  <span aria-hidden className="pointer-events-none absolute inset-x-0 top-[9%] z-10">
                    <span className="absolute left-[4%] top-0 h-[0.45rem] w-[9%] rounded-full bg-sky" />
                    <span className="absolute left-[2%] top-[1rem] h-[0.45rem] w-[12%] rounded-full bg-orange" />
                    <span className="absolute right-[4%] top-0 h-[0.45rem] w-[9%] rounded-full bg-sky" />
                    <span className="absolute right-[6%] top-[1rem] h-[0.45rem] w-[7%] rounded-full bg-blue" />
                  </span>
                )}
                <Vigilante mood={mood} fit={portrait ? "meet" : "slice"} className="absolute inset-0 h-full w-full p-[0.6rem]" />
              </div>
              <p className="flex items-center justify-between gap-[0.6rem] bg-[color-mix(in_oklab,var(--navy)_88%,transparent)] px-[0.9rem] py-[0.45rem] text-[1rem] font-medium text-white">
                <span className="flex items-center gap-[0.5rem] whitespace-nowrap">
                  <span aria-hidden className="inline-block h-[0.6rem] w-[0.6rem] rounded-full bg-sky" />
                  Vigilante Virtual
                </span>
              </p>
            </div>

            <div className="flex min-w-0 flex-1 flex-col overflow-y-auto">
              <div aria-live="polite" className="pt-[0.6rem]">
                <p className={`font-semibold leading-[1.15] text-ink [text-wrap:pretty] ${phrase.length > 80 ? "text-[2.35rem]" : "text-[2.6rem]"}`}>{phrase}</p>
                {view === "home" && !busy && !isListening && chatHistory.length === 1 && (
                  <p className="mt-[0.8rem] text-[1.3rem] leading-snug text-ink-soft">Toque «Hablar» y dígamelo, muestre su código QR o marque el apartamento.</p>
                )}
                {lastUser && view !== "help" && view !== "panic" && view !== "panic-confirm" && (
                  <p className="mt-[0.8rem] text-[1.2rem] text-ink-soft">
                    Usted: <span className="font-semibold text-ink">«{lastUser}»</span>
                  </p>
                )}
              </div>

              <div className="mt-auto flex flex-col gap-[0.8rem] pt-[0.8rem]">
                {view === "apartment" && <AptDisplay value={apartmentInput} />}
                {view === "step" && stepField && (
                  <StepDisplay field={stepField} index={stepIndex} total={askedFields.length} draft={stepDraft} problem={stepDraft ? stepProblem : null} />
                )}
                {(view === "result" || view === "wait" || view === "calling" || view === "step" || (view === "home" && Object.keys(ledger).length > 0)) && (
                  <VisitCard values={ledger} fields={visitFields} active={stepField} onlyFilled={view !== "step"} />
                )}
                {view === "help" && <HelpPanel />}
                {view === "panic-confirm" && (
                  <p className="text-[1.4rem] leading-snug text-ink-soft">Si alguien está en peligro, confirme la alerta. Si solo necesita orientación, toque «Ayuda».</p>
                )}
                {view === "panic" && <PanicPanel />}
              </div>
            </div>
          </motion.div>
        </AnimatePresence>

        {qrScannerOpen && (
          <QrScanner
            onResult={handleQrResult}
            onClose={() => setQrScannerOpen(false)}
            onFallback={() => {
              setQrScannerOpen(false);
              setApartmentInput("");
              setScreen("apartment");
            }}
          />
        )}
        {idScannerOpen && (
          <IdScanner
            onCapture={handleCedulaCapture}
            onType={typeCedulaInstead}
            onClose={() => {
              setIdScannerOpen(false);
              setIdentity(null);
              say("Muy bien. Si desea continuar, toque «Hablar» o marque el apartamento.");
            }}
          />
        )}
      </main>

      {/* Panel de teclas */}
      <aside className="relative z-10 flex min-h-0 flex-col gap-[0.9rem] rounded-[1.6rem] bg-panel p-[1.2rem] shadow-[inset_0_0_0_0.12rem_var(--key-edge),0_0.4rem_1.2rem_rgb(0_0_0/0.1)] landscape:flex-1 portrait:flex-1">
        <div className="flex items-center gap-[0.9rem]">
          <span className="flex h-[3.4rem] w-[3.6rem] shrink-0 items-center justify-center rounded-[0.7rem] bg-white p-[0.3rem] shadow-[inset_0_0_0_0.1rem_var(--key-edge)]">
            <img src="/brand/soft-ia-logo.png" alt="Soft-IA" className="h-full w-auto object-contain" />
          </span>
          <div className="min-w-0">
            <p className="text-[1.7rem] font-bold leading-none tracking-[-0.01em] text-ink">SoftiaGuard</p>
            <p className="mt-[0.3rem] text-[1rem] font-medium text-ink-soft">Vigilante Virtual · {config.unitName} · por Soft-IA</p>
          </div>
        </div>
        {/* Altavoz: ocupa el espacio libre del panel, como en un videoportero */}
        <span aria-hidden className={`grille shrink-0 rounded-[0.8rem] ${view === "apartment" || view === "step" ? "h-[1.2rem]" : "h-[2.6rem]"}`} />

        {demoMode && (
          <DemoTray
            waiting={view === "wait"}
            onTry={(apt, msg) => {
              setLedger({ apartment: apt });
              setApartmentInput(apt);
              handleSendRequest(msg, apt, false);
            }}
            onOwner={simulateOwnerDecision}
          />
        )}

        <div className="flex min-h-0 flex-1 flex-col justify-end gap-[0.9rem]">
          {view === "home" && (
            <>
              <TalkKey listening={isListening} busy={busy} onPress={toggleListening} primary={!voiceTrouble} />
              <div className="relative">
                <PanelKey tone={voiceTrouble ? "call" : "key"} icon={<QrCode />} onClick={() => setQrScannerOpen(true)} disabled={busy || isListening} hint="Si el residente le envió un código" className="min-h-[4.2rem] w-full text-[1.5rem]">
                  Tengo código QR
                </PanelKey>
              </div>
              <PanelKey icon={<Hash />} onClick={() => { setApartmentInput(""); setAptLetters(false); setScreen("apartment"); }} disabled={busy || isListening} hint="Con el teclado de la pantalla" className="min-h-[4.2rem] w-full text-[1.5rem]">
                Marcar apartamento
              </PanelKey>
            </>
          )}

          {view === "apartment" && (
            <>
              <AptKeypad letters={aptLetters} onLetters={setAptLetters} onKey={(k) => setApartmentInput((v) => (v.length + k.length <= APT_MAX ? v + k : v))} onDelete={() => setApartmentInput((v) => v.slice(0, -1))} />
              <div className="grid grid-cols-[1fr_2fr] gap-[0.7rem]">
                <PanelKey tone="quiet" icon={<ArrowLeft />} onClick={() => { setApartmentInput(""); setScreen("none"); }}>
                  Volver
                </PanelKey>
                <PanelKey tone="call" icon={<Check />} onClick={handleConfirmApartment} disabled={!apartmentInput || busy} className="justify-center text-[1.4rem]">
                  Confirmar {apartmentInput && `apto ${apartmentInput}`}
                </PanelKey>
              </div>
            </>
          )}

          {view === "step" && stepField && (
            <>
              {stepField === "cedula" || stepField === "telefono" ? (
                <NumberPad onKey={typeIntoStep} onDelete={() => setStepDraft((d) => d.slice(0, -1))} prefixKeys={stepField === "cedula" && !stepDraft ? ["V", "E"] : undefined} />
              ) : stepField === "apartment" ? (
                <AptKeypad letters={aptLetters} onLetters={setAptLetters} onKey={typeIntoStep} onDelete={() => setStepDraft((d) => d.slice(0, -1))} />
              ) : (
                <AlphaKeyboard onKey={typeIntoStep} onDelete={() => setStepDraft((d) => d.slice(0, -1))} />
              )}
              <div className="grid grid-cols-3 gap-[0.7rem]">
                <PanelKey tone="quiet" icon={<ArrowLeft />} onClick={stepBack} disabled={busy}>
                  Volver
                </PanelKey>
                {stepField === "motivo" ? (
                  <PanelKey icon={<SkipForward />} onClick={() => submitIdentity("motivo", "")} disabled={busy}>
                    Omitir
                  </PanelKey>
                ) : (
                  <TalkKey listening={isListening} busy={busy} onPress={toggleListening} primary={false} compact />
                )}
                <PanelKey tone="call" icon={<Check />} onClick={submitStep} disabled={!!stepProblem || busy}>
                  Continuar
                </PanelKey>
              </div>
            </>
          )}

          {(view === "wait" || view === "calling") && (
            <>
              <StateTile tone="wait" icon={<Clock />} title={view === "wait" ? "En espera" : "Llamando"} sub={view === "wait" ? "Residente notificado" : `Apto ${calling}`}>
                {view === "wait" && ownerWait && <Countdown seconds={ownerWait.remaining} />}
                {config.simulation && <SimTag>{view === "wait" ? "Aviso simulado" : "Llamada simulada"}</SimTag>}
                {ownerWait?.offline && <p aria-live="polite" className="text-[1.1rem] font-semibold text-no">Sin conexión con el sistema. Seguimos intentando…</p>}
              </StateTile>
              {view === "wait" && (
                <PanelKey tone="quiet" icon={<X />} onClick={handleCancelOwnerWait} className="min-h-[3.6rem] w-full justify-center text-[1.4rem]">
                  Cancelar solicitud
                </PanelKey>
              )}
            </>
          )}

          {view === "result" && outcome && (
            <>
              {outcome.kind === "ok" && (
                <StateTile tone="ok" icon={<CheckCircle2 />} title="Autorizado" sub="Pase adelante">
                  <p className="flex flex-wrap items-center gap-[0.6rem] text-[1.3rem] font-semibold text-ink">
                    El portón se abre.
                    {config.simulation && <span className="text-ok"><SimTag>Portón simulado</SimTag></span>}
                  </p>
                </StateTile>
              )}
              {outcome.kind === "no" && (
                <StateTile tone="no" icon={<XCircle />} title="No autorizado" sub="Acceso denegado">
                  <p className="text-[1.3rem] font-semibold leading-snug text-ink">Si cree que es un error, pida ayuda al vigilante de turno.</p>
                </StateTile>
              )}
              {outcome.kind === "error" && (
                <StateTile tone="off" icon={<WifiOff />} title="Sin conexión" sub="El sistema no respondió">
                  <p className="text-[1.3rem] font-semibold leading-snug text-ink">Puede intentar de nuevo en un momento.</p>
                </StateTile>
              )}
              {outcome.kind === "info" && (
                <StateTile tone="wait" icon={<Check />} title="Cancelada" sub="Solicitud cancelada" />
              )}
              <PanelKey tone="call" icon={outcome.kind === "ok" || outcome.kind === "info" ? <Check /> : <RotateCcw />} onClick={resetVisit} hint={<span className="tabular-nums">Nueva visita en {resetIn} s</span>} className="min-h-[4.2rem] w-full text-[1.5rem]">
                {outcome.kind === "ok" || outcome.kind === "info" ? "Terminar" : "Empezar de nuevo"}
              </PanelKey>
            </>
          )}

          {view === "help" && (
            <PanelKey tone="call" icon={<ArrowLeft />} onClick={() => setScreen("none")} className="min-h-[4.2rem] w-full justify-center text-[1.5rem]">
              Volver
            </PanelKey>
          )}

          {view === "panic-confirm" && (
            <>
              <PanelKey tone="alert" icon={<Siren />} onClick={confirmPanic} className="min-h-[4.6rem] w-full text-[1.6rem]">
                Sí, es una emergencia
              </PanelKey>
              <PanelKey tone="quiet" icon={<ArrowLeft />} onClick={() => setScreen("none")} className="min-h-[4rem] w-full text-[1.4rem]">
                No, volver
              </PanelKey>
            </>
          )}

          {view === "panic" && (
            <PanelKey tone="quiet" icon={<X />} onClick={() => { window.speechSynthesis.cancel(); setScreen("none"); }} className="min-h-[4.2rem] w-full justify-center text-[1.5rem]">
              Cerrar alerta
            </PanelKey>
          )}
        </div>

        {/* Fila del marco: invitado, ayuda y emergencia siempre al alcance */}
        {view !== "help" && view !== "panic" && view !== "panic-confirm" && (
          <div className={`grid gap-[0.6rem] border-t-[0.12rem] border-key-edge/70 pt-[0.9rem] ${view === "home" ? "grid-cols-3" : "grid-cols-2"}`}>
            {view === "home" && (
              <PanelKey tone="quiet" stacked icon={<UserCheck />} onClick={handleStartGuest} disabled={busy || isListening}>
                Soy invitado
              </PanelKey>
            )}
            <PanelKey tone="quiet" stacked icon={<CircleHelp />} onClick={() => setScreen("help")}>
              Ayuda
            </PanelKey>
            <PanelKey tone="alert" stacked icon={<Siren />} onClick={() => setScreen("panic-confirm")}>
              Emergencia
            </PanelKey>
          </div>
        )}
      </aside>
    </div>
  );
}

/* ---------- Piezas ---------- */

// La tecla de llamada: Hablar
function TalkKey({ listening, busy, onPress, primary, compact }: { listening: boolean; busy: boolean; onPress: () => void; primary: boolean; compact?: boolean }) {
  const reduced = useReducedMotion();
  if (listening) {
    return (
      <div className={`relative ${compact ? "" : "flex flex-1 flex-col"}`}>
        <button
          type="button"
          onClick={onPress}
          className={`keycap relative flex w-full items-center justify-center gap-[0.7rem] overflow-hidden rounded-[0.9rem] border-[0.2rem] border-call bg-key font-semibold text-call cursor-pointer ${compact ? "min-h-[3rem] text-[1.1rem]" : "h-full min-h-[6.2rem] text-[1.8rem]"}`}
        >
          <motion.span
            aria-hidden
            className="absolute inset-y-0 left-0 bg-call/15"
            initial={{ width: "0%" }}
            animate={{ width: "100%" }}
            transition={{ duration: reduced ? 0 : RECORD_LIMIT_MS / 1000, ease: "linear" }}
          />
          <Square className="relative h-[1em] w-[1em] fill-current" />
          <span className="relative">{compact ? "Terminar" : "Escuchando · toque para terminar"}</span>
        </button>
        {!compact && <FocusBrackets color="var(--call)" />}
      </div>
    );
  }
  return (
    <PanelKey
      tone={primary ? "call" : "key"}
      icon={<Mic />}
      onClick={onPress}
      disabled={busy}
      hint={compact ? undefined : busy ? "Un momento…" : "Dígame el apartamento o a quién visita"}
      className={compact ? "" : "min-h-[6.2rem] w-full flex-1 text-[2.2rem]"}
    >
      {compact ? "Dictar" : "Hablar"}
    </PanelKey>
  );
}

// Tecla-indicador del estado: se enciende con el color de la decisión
// «off»: el sistema no respondió; no es una negativa, así que no usa el rojo de denegado
function StateTile({ tone, icon, title, sub, children }: { tone: "ok" | "no" | "wait" | "off"; icon: React.ReactNode; title: string; sub: string; children?: React.ReactNode }) {
  const reduced = useReducedMotion();
  const toneClass =
    tone === "ok" ? "border-ok bg-ok-tint text-ok"
    : tone === "no" ? "border-no bg-no-tint text-no"
    : tone === "off" ? "border-ink-soft bg-key text-ink"
    : "border-wait bg-wait-tint text-wait";
  return (
    <div className="relative flex flex-1 flex-col">
      <motion.div
        initial={reduced ? false : { opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
        className={`flex flex-1 flex-col justify-center gap-[0.8rem] rounded-[1rem] border-[0.22rem] p-[1.2rem] ${toneClass}`}
      >
        <div className="flex items-center gap-[0.9rem]">
          <span className="[&>svg]:h-[3.2rem] [&>svg]:w-[3.2rem]">{icon}</span>
          <div>
            <p className="text-[2.6rem] font-bold uppercase leading-none tracking-[0.01em]">{title}</p>
            <p className="mt-[0.3rem] text-[1.2rem] font-semibold">{sub}</p>
          </div>
        </div>
        {children}
      </motion.div>
      <FocusBrackets color={tone === "off" ? "var(--ink-soft)" : `var(--${tone})`} />
    </div>
  );
}

function Countdown({ seconds }: { seconds: number }) {
  const m = Math.floor(seconds / 60);
  const s = String(seconds % 60).padStart(2, "0");
  return (
    <p aria-label={`Quedan ${m} minutos y ${s} segundos`} className="text-[5.6rem] font-bold leading-none tracking-[-0.03em] tabular-nums">
      {m}:{s}
    </p>
  );
}

function AptDisplay({ value }: { value: string }) {
  return (
    <div>
      <div className="flex min-h-[5.4rem] items-end border-b-[0.25rem] border-legend pb-[0.3rem]" aria-label={value ? `Apartamento ${value}` : "Sin marcar"}>
        <span className="text-[4rem] font-bold leading-none tracking-[0.02em] text-ink">{value}</span>
        <span aria-hidden className="mb-[0.4rem] ml-[0.2rem] inline-block h-[3.2rem] w-[0.22rem] animate-pulse bg-legend" />
      </div>
      <p className="mt-[0.5rem] text-[1.1rem] text-ink-soft">Como aparece en la puerta: por ejemplo 103, PH2 o D-1.</p>
    </div>
  );
}

function StepDisplay({ field, index, total, draft, problem }: { field: LedgerField; index: number; total: number; draft: string; problem: string | null }) {
  return (
    <div>
      <p className="text-[1.4rem] font-semibold text-ink">
        {stepPrompt[field]}
        {field === "motivo" && <span className="font-normal text-ink-soft"> Es opcional.</span>}
        {Math.max(total, index + 1) > 1 && (
          <span className="ml-[0.6rem] whitespace-nowrap font-normal tabular-nums text-ink-soft">
            Paso {index + 1} de {Math.max(total, index + 1)}
          </span>
        )}
      </p>
      <div className="mt-[0.5rem] flex min-h-[3.6rem] items-end border-b-[0.25rem] border-legend pb-[0.2rem]">
        <span className="break-all text-[2.2rem] font-semibold leading-tight text-ink">{draft}</span>
        <span aria-hidden className="mb-[0.35rem] ml-[0.15rem] inline-block h-[2rem] w-[0.2rem] animate-pulse bg-legend" />
      </div>
      <p aria-live="polite" className="mt-[0.4rem] min-h-[1.5rem] text-[1.1rem] font-semibold text-no">
        {problem}
      </p>
    </div>
  );
}

function HelpPanel() {
  const ways = [
    { icon: <Mic />, title: "Hable", text: "Toque «Hablar» y diga a qué apartamento va o a quién visita." },
    { icon: <QrCode />, title: "Muestre su código QR", text: "Si el residente le envió un código, acérquelo a la cámara." },
    { icon: <Hash />, title: "Marque el apartamento", text: "Use el teclado de la pantalla y toque «Confirmar»." },
  ];
  return (
    <div className="flex flex-col gap-[1rem]">
      {ways.map((w) => (
        <div key={w.title} className="flex gap-[0.9rem]">
          <span className="mt-[0.2rem] text-legend [&>svg]:h-[1.8rem] [&>svg]:w-[1.8rem]">{w.icon}</span>
          <div>
            <p className="text-[1.3rem] font-semibold text-ink">{w.title}</p>
            <p className="text-[1.1rem] leading-snug text-ink-soft">{w.text}</p>
          </div>
        </div>
      ))}
      <p className="text-[1.1rem] leading-snug text-ink">¿Algo no funciona? Pida ayuda al vigilante de turno. En una emergencia, toque «Emergencia».</p>
      <p className="text-[1rem] leading-snug text-ink-soft">
        Privacidad: su voz y la foto de su cédula se procesan en el equipo del condominio. Los datos de su visita quedan registrados en el sistema de administración del condominio.
      </p>
    </div>
  );
}

function PanicPanel() {
  return (
    <div className="relative">
      <div className="flex flex-col gap-[0.8rem] rounded-[1rem] border-[0.22rem] border-no bg-no-tint p-[1.2rem] text-no">
        <p className="flex items-center gap-[0.8rem] text-[2.2rem] font-bold uppercase leading-none">
          <Siren className="h-[2.6rem] w-[2.6rem]" /> Alerta {config.simulation ? "simulada" : "enviada"}
        </p>
        {config.simulation ? (
          <p className="text-[1.4rem] leading-snug text-ink">
            Este tótem todavía no está conectado a la central de seguridad. <strong>Si es una emergencia real, llame al 911.</strong>
          </p>
        ) : (
          <p className="text-[1.4rem] leading-snug text-ink">El personal de seguridad recibió la alerta. Mantenga la calma.</p>
        )}
      </div>
      <FocusBrackets color="var(--no)" />
    </div>
  );
}

// Solo con ?demo: pruebas y respuesta simulada del propietario
function DemoTray({ waiting, onTry, onOwner }: { waiting: boolean; onTry: (apt: string, msg: string) => void; onOwner: (d: "aprobada" | "rechazada") => void }) {
  const chip = "min-h-[2.2rem] rounded-[0.5rem] border-[0.1rem] border-dashed border-ink-soft px-[0.6rem] text-[1rem] font-semibold text-ink cursor-pointer";
  return (
    <div className="flex flex-wrap items-center gap-[0.5rem] rounded-[0.6rem] border-[0.1rem] border-dashed border-ink-soft p-[0.5rem]">
      <span className="px-[0.3rem] text-[1rem] font-bold uppercase tracking-[0.06em] text-ink-soft">Demo</span>
      <button type="button" className={chip} onClick={() => onTry("3A", "Quiero ir al apartamento 3A")}>
        Probar 3A
      </button>
      <button type="button" className={chip} onClick={() => onTry("1B", "Quiero ver a Carlos Rodríguez")}>
        Probar 1B
      </button>
      {waiting && (
        <>
          <button type="button" className={chip} onClick={() => onOwner("aprobada")}>
            Propietario aprueba
          </button>
          <button type="button" className={chip} onClick={() => onOwner("rechazada")}>
            Propietario rechaza
          </button>
        </>
      )}
    </div>
  );
}
