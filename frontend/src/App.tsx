import { useState, useEffect, useRef } from "react";
import {
  Phone,
  Shield,
  ShieldAlert,
  Mic,
  MicOff,
  Send,
  QrCode,
  Sparkles,
  CheckCircle,
  XCircle,
  HelpCircle,
  ChevronRight,
  Volume2,
  VolumeX
} from "lucide-react";
import VirtualAssistantCanvas from "./components/VirtualAssistantCanvas";
import { motion, AnimatePresence } from "motion/react";
const BUILDING_NAME = import.meta.env.VITE_BUILDING_NAME;

interface Message {
  role: "user" | "assistant";
  text: string;
}

export default function App() {
  // Keypad & Apartment Selection States
  const [apartmentInput, setApartmentInput] = useState<string>("");

  // Conversational Interface States
  const [visitorMessage, setVisitorMessage] = useState<string>("");
  const [chatHistory, setChatHistory] = useState<Message[]>([
    {
      role: "assistant",
      text: `¡Bienvenido a ${BUILDING_NAME || "Edificio XYZ"}! Por favor, marque el número de apartamento en el teclado o dígame a quién viene a visitar.`,
    },
  ]);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [animationState, setAnimationState] = useState<"idle" | "talking" | "scanning" | "success" | "denied">("idle");

  // Audio Feedback (Text-to-Speech & Speech-to-Text)
  const [voiceEnabled, setVoiceEnabled] = useState<boolean>(true);
  const [isListening, setIsListening] = useState<boolean>(false);

  // Simulated Hardware States
  const [gateOpen, setGateOpen] = useState<boolean>(false);
  const [gateTimer, setGateTimer] = useState<number>(0);
  const [intercomCalling, setIntercomCalling] = useState<boolean>(false);
  const [intercomStatus, setIntercomStatus] = useState<string>("");
  const [alertActive, setAlertActive] = useState<boolean>(false);
  const [scannedQR, setScannedQR] = useState<boolean>(false);
  const [identifiedOwner, setIdentifiedOwner] = useState<string | null>(null);
  const [identifiedApt, setIdentifiedApt] = useState<string | null>(null);

  const chatEndRef = useRef<HTMLDivElement>(null);
  // STT local: grabación de audio con MediaRecorder (Whisper corre en el backend)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  // Auto-stop de seguridad para no dejar el micrófono grabando indefinidamente
  const recordTimeoutRef = useRef<any>(null);

  // Scroll to bottom of chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory]);

  // Gate automatic closing countdown
  useEffect(() => {
    if (gateOpen) {
      setGateTimer(10);
      const interval = setInterval(() => {
        setGateTimer((prev) => {
          if (prev <= 1) {
            setGateOpen(false);
            clearInterval(interval);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [gateOpen]);

  // Speech Synthesis Helper
  const speakText = (text: string) => {
    if (!voiceEnabled) return;
    try {
      // Cancel any ongoing speech
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "es-VE"; // Spanish (Venezuela) for mood!
      utterance.pitch = 1.0;
      utterance.rate = 1.05;

      utterance.onstart = () => {
        setAnimationState("talking");
      };
      utterance.onend = () => {
        setAnimationState("idle");
      };
      utterance.onerror = () => {
        setAnimationState("idle");
      };
      window.speechSynthesis.speak(utterance);
    } catch (error) {
      console.error("Text-to-speech error:", error);
    }
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

  // Envía el clip grabado al backend (Whisper local) y usa la transcripción.
  const transcribeAndSend = async (blob: Blob) => {
    if (blob.size === 0) {
      setAnimationState("idle");
      return;
    }
    try {
      setAnimationState("scanning");
      const formData = new FormData();
      formData.append("file", blob, "audio.webm");
      const res = await fetch("/api/transcribe", { method: "POST", body: formData });
      if (!res.ok) throw new Error(`STT HTTP ${res.status}`);
      const data = await res.json();
      const text = (data.text || "").trim();
      if (text) {
        setVisitorMessage(text);
        handleSendRequest(text);
      } else {
        setAnimationState("idle");
      }
    } catch (e) {
      console.error("Transcription failed:", e);
      setAnimationState("idle");
    }
  };

  const startListening = async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      console.error("getUserMedia no disponible (¿contexto seguro? usa localhost o HTTPS)");
      return;
    }
    try {
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
      setAnimationState("scanning");

      // Red de seguridad: corta la grabación a los 10s
      clearRecordTimeout();
      recordTimeoutRef.current = setTimeout(() => stopListening(), 10000);
    } catch (e) {
      console.error("No se pudo acceder al micrófono:", e);
      releaseMicrophone();
      setIsListening(false);
      setAnimationState("idle");
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
      } catch { /* noop */ }
      releaseMicrophone();
    };
  }, []);

  // Dial Pad clicks
  const handleKeypadPress = (val: string) => {
    if (val === "DELETE") {
      setApartmentInput((prev) => prev.slice(0, -1));
    } else if (val === "CLEAR") {
      setApartmentInput("");
    } else {
      if (apartmentInput.length < 4) {
        setApartmentInput((prev) => prev + val);
      }
    }
  };

  // Standard keyboard hooks for Dial Pad
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Focus checking: only register keypad if not typing in the text input box
      if (document.activeElement?.tagName === "INPUT") return;

      const key = e.key.toUpperCase();
      if (/^[0-9A-Z]$/.test(key)) {
        if (apartmentInput.length < 4) {
          setApartmentInput((prev) => prev + key);
        }
      } else if (key === "BACKSPACE") {
        setApartmentInput((prev) => prev.slice(0, -1));
      } else if (key === "ENTER") {
        handleConfirmApartment();
      } else if (key === "ESCAPE") {
        setApartmentInput("");
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [apartmentInput]);

  // Main API query logic for verification
  const handleSendRequest = async (userMsg: string) => {
    if (!userMsg.trim()) return;

    const updatedHistory = [...chatHistory, { role: "user" as const, text: userMsg }];
    setChatHistory(updatedHistory);
    setVisitorMessage("");
    setIsProcessing(true);
    setAnimationState("scanning");

    try {
      const response = await fetch("/api/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userMsg,
          history: chatHistory.slice(-6), // Keep context size reasonable
          currentAptInput: apartmentInput,
        }),
      });

      const data = await response.json();

      setChatHistory((prev) => [
        ...prev,
        { role: "assistant", text: data.reply },
      ]);

      setAnimationState(data.assistant_animation || "talking");
      speakText(data.reply);

      // Apply dynamic actions from Gemini response
      if (data.apartment) {
        setIdentifiedApt(data.apartment);
      }
      if (data.owner) {
        setIdentifiedOwner(data.owner);
      }

      handleTotemAction(data.action, data.apartment, data.owner);

    } catch (error) {
      console.error("Verification failed:", error);
      const errorMsg = "Disculpe, la red del edificio experimenta problemas. Por favor presione el intercomunicador físico.";
      setChatHistory((prev) => [
        ...prev,
        { role: "assistant", text: errorMsg },
      ]);
      setAnimationState("denied");
      speakText(errorMsg);
    } finally {
      setIsProcessing(false);
    }
  };

  // Action Executor based on state
  const handleTotemAction = (action: string, apt: string | null, owner: string | null) => {
    if (action === "open_gate") {
      setGateOpen(true);
      setIntercomCalling(false);
      // Brief confetti or success cue can be added here
    } else if (action === "ring_bell" && apt) {
      setIntercomCalling(true);
      setIntercomStatus(`Llamando al Apartamento ${apt} (${owner || "Residente"})...`);
      // Simulate resident picking up in 4 seconds
      setTimeout(() => {
        setIntercomStatus(`¡Llamada respondida! El residente ha presionado la apertura remota.`);
        speakText(`Acceso autorizado por la residencia ${apt}. Abriendo portón.`);
        setTimeout(() => {
          setGateOpen(true);
          setIntercomCalling(false);
        }, 1500);
      }, 4000);
    } else if (action === "show_qr_scanner") {
      setAnimationState("scanning");
      speakText("Coloque su código QR frente a la cámara superior.");
    } else if (action === "show_error") {
      setAnimationState("denied");
    }
  };

  // Green Confirm Button Click Handler (from Teclado Numérico)
  const handleConfirmApartment = () => {
    if (!apartmentInput) {
      speakText("Por favor marque un número de apartamento primero.");
      return;
    }
    const aptMsg = `Quiero visitar el apartamento ${apartmentInput}`;
    handleSendRequest(aptMsg);
  };

  // Simulate scanning of pre-approved QR code (Matches original image scenario)
  const handleSimulateQRScan = () => {
    setScannedQR(true);
    setAnimationState("scanning");
    speakText("Código QR detectado. Leyendo credenciales.");

    setTimeout(() => {
      // Direct call simulating 4B Pre-approved QR
      const mockMsg = "He escaneado su Código QR de invitación de Elena Rivas para el Apartamento 4B.";
      handleSendRequest(mockMsg);
    }, 1500);
  };

  // Red Panic Button Click Handler
  const handlePanicButton = () => {
    setAlertActive(true);
    setAnimationState("denied");
    const alertMsg = "¡ALERTA DE EMERGENCIA ACTIVADA! Transmitiendo señal directa al centro de control y contactando patrulla de zona. Mantenga la calma.";
    setChatHistory((prev) => [
      ...prev,
      { role: "assistant", text: alertMsg },
    ]);
    speakText(alertMsg);

    // Auto turn off panic after 8 seconds
    setTimeout(() => {
      setAlertActive(false);
    }, 8000);
  };



  return (
    <div className="min-h-screen bg-[#0A0A0A] text-white flex flex-col font-sans overflow-x-hidden antialiased selection:bg-emerald-500/30 selection:text-emerald-200">

      {/* Top Header */}
      <header className="h-16 border-b border-white/10 px-6 md:px-8 flex items-center justify-between bg-[#111111] shrink-0 z-20 shadow-md">
        <div className="flex items-center gap-3">
          <div className={`w-3 h-3 rounded-full transition-all duration-500 ${gateOpen
              ? "bg-emerald-500 shadow-[0_0_12px_rgba(16,185,129,0.8)]"
              : alertActive
                ? "bg-rose-500 shadow-[0_0_12px_rgba(239,68,68,0.8)] animate-pulse"
                : "bg-cyan-500 shadow-[0_0_12px_rgba(6,182,212,0.8)]"
            }`}></div>
          <span className="text-xs md:text-sm font-display font-medium tracking-widest uppercase text-white/70">
            {BUILDING_NAME || "Edificio XYZ"} | Asistente de Vigilancia Soft-IA
          </span>
        </div>
        <div className="flex items-center gap-6 text-xs md:text-sm text-white/50 font-mono">
          <span className="hidden sm:inline">Guatire, VZLA</span>
          <span>24.5°C</span>
          <span>{new Date().toLocaleTimeString('es-VE', { hour: '2-digit', minute: '2-digit', hour12: false })}</span>
        </div>
      </header>

      <div className="flex-1 flex flex-col md:flex-row items-stretch overflow-hidden relative">



        {/* Core Layout Grid */}
        <div className="flex-1 flex flex-col lg:flex-row p-6 md:p-8 gap-8 items-stretch overflow-y-auto">

          {/* 2. Left Section: Virtual Assistant Avatar & Status */}
          <div className="flex-1 flex flex-col gap-6 min-h-[440px]">
            <div className="flex-1 relative bg-gradient-to-b from-[#151515] to-[#0A0A0A] rounded-3xl border border-white/5 overflow-hidden flex flex-col items-center justify-center p-6 min-h-[300px]">

              {/* Status Banner */}
              <div className="absolute top-6 left-6 px-3 py-1.5 rounded-full text-[10px] font-mono bg-black/60 border border-white/10 text-emerald-400 uppercase tracking-widest flex items-center gap-2 backdrop-blur-md z-10 shadow-lg">
                <span className={`w-2 h-2 rounded-full shadow-[0_0_8px_rgba(16,185,129,0.5)] ${animationState === "idle" ? "bg-cyan-500 shadow-[0_0_8px_rgba(6,182,212,0.5)]" :
                    animationState === "talking" ? "bg-amber-400 animate-pulse shadow-[0_0_8px_rgba(251,191,36,0.5)]" :
                      animationState === "scanning" ? "bg-blue-500 animate-spin" :
                        animationState === "success" ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" : "bg-rose-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]"
                  }`} />
                {animationState === "idle" ? "En Espera" :
                  animationState === "talking" ? "Transmitiendo" :
                    animationState === "scanning" ? "Analizando" :
                      animationState === "success" ? "Aprobado" : "Denegado"}
              </div>

              {/* Quick Simulate QR Action on top right of screen */}
              <button
                onClick={handleSimulateQRScan}
                title="Simular Escaneo Código QR"
                className="absolute top-6 right-6 p-2 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 text-white/70 hover:text-white transition-all backdrop-blur-md z-10 cursor-pointer"
              >
                <QrCode className="w-5 h-5" />
              </button>

              {/* ThreeJS Rendering Area */}
              <div className="absolute inset-0 w-full h-full">
                <VirtualAssistantCanvas animationState={animationState} />
              </div>

              {/* Float dialog at the bottom center of Avatar Screen */}
              <div className="absolute bottom-6 left-6 right-6 bg-black/60 border border-white/10 rounded-2xl p-4 backdrop-blur-md z-10 max-w-xl mx-auto shadow-2xl">
                <p className="text-emerald-400 text-[10px] font-mono tracking-widest uppercase mb-1.5">Asistente Virtual</p>
                <p className="text-sm sm:text-base leading-relaxed text-slate-100 font-sans font-medium">
                  "{chatHistory[chatHistory.length - 1]?.text}"
                </p>
              </div>
            </div>

            {/* Voice status bar & Microphone control */}
            <div className="h-24 bg-[#1A1A1A] rounded-2xl border border-white/5 p-4 flex items-center gap-4 shrink-0 shadow-lg">
              <div className="flex-1">
                <div className="text-[10px] text-white/30 uppercase tracking-widest mb-1.5 font-mono">Entrada de voz detectada</div>
                <div className="flex items-end gap-1.5 h-6">
                  {isListening ? (
                    <>
                      <div className="w-1 h-3 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: "0s" }}></div>
                      <div className="w-1 h-5 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: "0.15s" }}></div>
                      <div className="w-1 h-2 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: "0.3s" }}></div>
                      <div className="w-1 h-6 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: "0.45s" }}></div>
                      <div className="w-1 h-4 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: "0.6s" }}></div>
                      <div className="w-1 h-5 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: "0.75s" }}></div>
                      <span className="ml-2 text-emerald-400 font-mono text-xs animate-pulse">Escuchando... Hable ahora</span>
                    </>
                  ) : (
                    <>
                      <div className="w-1 h-2 bg-white/10 rounded-full"></div>
                      <div className="w-1 h-2 bg-white/10 rounded-full"></div>
                      <div className="w-1 h-2 bg-white/10 rounded-full"></div>
                      <div className="w-1 h-2 bg-white/10 rounded-full"></div>
                      <div className="w-1 h-2 bg-white/10 rounded-full"></div>
                      <span className="ml-2 text-white/40 italic text-xs">Presione el micrófono para hablar</span>
                    </>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2">
                {/* Voice feedback switch */}
                <button
                  onClick={() => setVoiceEnabled(!voiceEnabled)}
                  title={voiceEnabled ? "Silenciar Voz" : "Activar Voz (TTS)"}
                  className={`p-3 rounded-full border transition-all cursor-pointer ${voiceEnabled ? "bg-emerald-950/40 border-emerald-500/30 text-emerald-400" : "bg-white/5 border-white/10 text-white/40"
                    }`}
                >
                  {voiceEnabled ? <Volume2 className="w-5 h-5" /> : <VolumeX className="w-5 h-5" />}
                </button>

                {/* Microphone trigger button */}
                <button
                  onClick={toggleListening}
                  className={`p-3.5 rounded-full transition-all cursor-pointer shadow-md ${isListening
                      ? "bg-rose-600 hover:bg-rose-500 text-white shadow-[0_0_15px_rgba(239,68,68,0.4)]"
                      : "bg-white/5 hover:bg-white/10 border border-white/10 text-white/90"
                    }`}
                  title={isListening ? "Detener Grabación" : "Hablar con el Vigilante"}
                >
                  <Mic className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>

          {/* 3. Center-Right Section: Numeric Keypad */}
          <div className="w-full lg:w-80 flex flex-col gap-6 shrink-0">
            <div className="flex-1 bg-[#151515] rounded-3xl border border-white/5 p-6 flex flex-col justify-between shadow-xl">
              <div>
                <label className="block text-[10px] font-mono tracking-widest text-center text-white/40 mb-3 uppercase font-bold">
                  MARQUE NÚMERO DE APARTAMENTO
                </label>
                <div className="bg-black/60 rounded-xl p-4 mb-6 border border-white/5 flex items-center justify-center relative shadow-inner">
                  <span className="text-[10px] uppercase tracking-widest text-white/30 absolute left-4 font-mono">APT</span>
                  <span className="text-4xl font-light tracking-[0.2em] text-emerald-500 font-display">
                    {apartmentInput || "----"}
                  </span>
                  <span className="text-[9px] font-mono text-white/20 absolute right-4">[{apartmentInput.length}/4]</span>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  {/* Keypad Buttons matching exact styling */}
                  {["1", "2", "3", "4", "5", "6", "7", "8", "9"].map((num) => (
                    <button
                      key={num}
                      onClick={() => handleKeypadPress(num)}
                      className="bg-white/5 border border-white/5 rounded-2xl h-14 flex items-center justify-center text-xl font-light hover:bg-white/10 active:scale-95 transition-all text-white/90 cursor-pointer"
                    >
                      {num}
                    </button>
                  ))}
                  <button
                    onClick={() => handleKeypadPress("CLEAR")}
                    className="bg-white/5 border border-white/5 rounded-2xl h-14 flex items-center justify-center hover:bg-white/10 active:scale-95 transition-all text-white/40 font-mono text-[10px] uppercase tracking-widest cursor-pointer"
                  >
                    CLR
                  </button>
                  <button
                    onClick={() => handleKeypadPress("0")}
                    className="bg-white/5 border border-white/5 rounded-2xl h-14 flex items-center justify-center text-xl font-light hover:bg-white/10 active:scale-95 transition-all text-white/90 cursor-pointer"
                  >
                    0
                  </button>
                  <button
                    onClick={() => handleKeypadPress("DELETE")}
                    className="bg-white/5 border border-white/5 rounded-2xl h-14 flex items-center justify-center hover:bg-white/10 active:scale-95 transition-all text-rose-500/70 cursor-pointer"
                    title="Borrar dígito"
                  >
                    <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M12 9.75L14.25 12m0 0l2.25 2.25M14.25 12l2.25-2.25M14.25 12L12 14.25m-2.58 4.92l-6.375-6.375a1.125 1.125 0 010-1.59L9.42 4.83c.211-.211.498-.33.795-.33H19.5a2.25 2.25 0 012.25 2.25v10.5a2.25 2.25 0 01-2.25 2.25h-9.284c-.297 0-.584-.119-.795-.33z" />
                    </svg>
                  </button>
                </div>
              </div>

              <div className="space-y-4 pt-6 mt-6 border-t border-white/5">
                <button
                  onClick={handleConfirmApartment}
                  className="h-16 w-full bg-emerald-600 hover:bg-emerald-500 rounded-2xl shadow-[0_4px_20px_rgba(16,185,129,0.4)] flex items-center justify-center gap-3 transition-colors text-white font-bold uppercase tracking-[0.1em] cursor-pointer"
                >
                  <span>Confirmar</span>
                  <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="3">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                  </svg>
                </button>

                {/* Red Panic Trigger */}
                <button
                  onClick={handlePanicButton}
                  className="w-full py-2.5 bg-rose-950/30 hover:bg-rose-900/40 text-rose-400 hover:text-white font-mono text-[10px] uppercase tracking-wider rounded-xl border border-rose-900/30 hover:border-rose-700/50 transition-all flex items-center justify-center gap-2 cursor-pointer"
                >
                  <ShieldAlert className="w-3.5 h-3.5 animate-pulse" />
                  BOTÓN DE PÁNICO
                </button>

              </div>

              {/* Simulaciones */}
              <div className="space-y-4 pt-6 mt-6 border-t border-white/5">
                <button
                  onClick={handleSimulateQRScan}
                  className="px-2.5 py-1 rounded-lg bg-emerald-950/20 border border-emerald-500/20 hover:border-emerald-500/50 text-emerald-400 hover:text-emerald-300 transition-all cursor-pointer font-mono text-[10px]"
                >
                  [Escanear QR]
                </button>
                <button
                  onClick={() => {
                    setApartmentInput("3A");
                    handleSendRequest("Quiero ir al apartamento 3A");
                  }}
                  className="px-2.5 py-1 rounded-lg bg-rose-950/20 border border-rose-500/20 hover:border-rose-500/50 text-rose-400 hover:text-rose-300 transition-all cursor-pointer font-mono text-[10px]"
                >
                  [Probar 3A]
                </button>
                <button
                  onClick={() => {
                    setApartmentInput("1B");
                    handleSendRequest("Quiero ver a Carlos Rodríguez");
                  }}
                  className="px-2.5 py-1 rounded-lg bg-amber-950/20 border border-amber-500/20 hover:border-amber-500/50 text-amber-400 hover:text-amber-300 transition-all cursor-pointer font-mono text-[10px]"
                >
                  [Probar 1B]
                </button>
              </div>
            </div>
          </div>

          {/* 4. Far Right Section: Interactive Chat Box & Device Status */}
          <div className="w-full lg:w-96 flex flex-col gap-6 shrink-0">

            {/* Active Gate Access Indicator Section */}
            <div className="p-5 rounded-3xl bg-[#111111] border border-white/5 shadow-xl flex flex-col gap-4">
              <h3 className="text-xs font-mono tracking-widest text-white/40 uppercase font-bold flex items-center gap-2">
                <Shield className="w-4 h-4 text-emerald-400" />
                Estado de Acceso
              </h3>

              <div className="flex items-center gap-4 py-1">
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center border transition-all duration-300 ${gateOpen
                    ? "bg-emerald-950/40 border-emerald-500 text-emerald-400 shadow-lg shadow-emerald-500/20"
                    : "bg-[#151515] border-white/5 text-white/30"
                  }`}>
                  <CheckCircle className={`w-6 h-6 ${gateOpen ? "animate-pulse" : ""}`} />
                </div>
                <div className="flex-1">
                  <p className="text-[10px] font-mono text-white/30 tracking-wider">PORTÓN VEHICULAR</p>
                  <p className={`text-sm font-display font-bold ${gateOpen ? "text-emerald-400" : "text-white/60"}`}>
                    {gateOpen ? `ABIERTO - Cierra en ${gateTimer}s` : "BLOQUEADO / SEGURIDAD"}
                  </p>
                </div>
                {gateOpen && (
                  <div className="text-emerald-400 bg-emerald-950/40 text-[10px] font-bold px-2.5 py-1.5 rounded-lg border border-emerald-500/20 animate-pulse font-mono uppercase tracking-wider">
                    Pase
                  </div>
                )}
              </div>

              {/* Intercom Ringing Simulation Screen */}
              {intercomCalling && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-emerald-950/20 border border-emerald-500/30 p-3 rounded-xl flex items-center gap-3 animate-pulse"
                >
                  <Phone className="w-4 h-4 text-emerald-400 shrink-0" />
                  <div className="flex-1">
                    <p className="text-[9px] font-mono text-emerald-400 uppercase tracking-widest font-bold">Intercomunicador</p>
                    <p className="text-xs text-white/80 font-medium">{intercomStatus}</p>
                  </div>
                </motion.div>
              )}

              {/* Emergency Alarm Banner */}
              {alertActive && (
                <motion.div
                  initial={{ scale: 0.95 }}
                  animate={{ scale: [0.95, 1.02, 0.95] }}
                  transition={{ repeat: Infinity, duration: 1.5 }}
                  className="bg-rose-950/40 border border-rose-500/40 p-3 rounded-xl flex items-center gap-3 text-rose-300"
                >
                  <ShieldAlert className="w-5 h-5 shrink-0 text-rose-400 animate-bounce" />
                  <div>
                    <p className="text-xs font-bold uppercase font-display tracking-wide text-rose-400">ALARMA ACTIVA</p>
                    <p className="text-[10px] text-rose-300/70">Señal de emergencia transmitida al centro de control.</p>
                  </div>
                </motion.div>
              )}
            </div>

            {/* Interactive Chat interface to type custom messages */}
            <div className="p-5 rounded-3xl bg-[#111111] border border-white/5 shadow-xl flex flex-col gap-4 flex-1 min-h-[220px] max-h-[340px]">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-mono tracking-widest text-white/40 uppercase font-bold flex items-center gap-1.5">
                  <Sparkles className="w-4 h-4 text-emerald-400" />
                  Bitácora de Conversación
                </h3>
                <button
                  onClick={() => setChatHistory([
                    { role: "assistant", text: "¡Bienvenido a Residencias El Ávila! ¿Cómo puedo ayudarle hoy?" }
                  ])}
                  className="text-[9px] text-white/30 hover:text-white/60 font-bold uppercase tracking-wider transition-colors"
                >
                  Limpiar
                </button>
              </div>

              {/* Chat message list */}
              <div className="flex-1 overflow-y-auto space-y-3.5 pr-1 text-xs">
                {chatHistory.map((chat, idx) => (
                  <div
                    key={idx}
                    className={`flex flex-col ${chat.role === "user" ? "items-end" : "items-start"}`}
                  >
                    <span className="text-[9px] font-mono text-white/30 mb-1 uppercase tracking-wider">
                      {chat.role === "user" ? "Visitante" : "Asistente Virtual"}
                    </span>
                    <div className={`p-3 rounded-2xl max-w-[85%] leading-relaxed ${chat.role === "user"
                        ? "bg-[#10b981]/95 text-white rounded-tr-none shadow-md shadow-emerald-900/10"
                        : "bg-[#151515] border border-white/5 text-white/90 rounded-tl-none"
                      }`}>
                      {chat.text}
                    </div>
                  </div>
                ))}
                <div ref={chatEndRef} />
              </div>

              {/* Input form & Send button */}
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendRequest(visitorMessage);
                }}
                className="flex gap-2 pt-3 border-t border-white/5 shrink-0"
              >
                <input
                  type="text"
                  value={visitorMessage}
                  onChange={(e) => setVisitorMessage(e.target.value)}
                  placeholder="Escriba aquí (ej. Vengo al 2B...)"
                  className="flex-1 px-4 py-2.5 rounded-xl bg-[#151515] border border-white/5 text-white/90 placeholder-white/20 focus:outline-none focus:border-emerald-500/40 text-xs transition-all"
                  disabled={isProcessing}
                />
                <button
                  type="submit"
                  disabled={isProcessing || !visitorMessage.trim()}
                  className="p-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white disabled:opacity-40 disabled:hover:bg-emerald-600 cursor-pointer active:scale-95 transition-all shadow-lg shadow-emerald-900/20"
                >
                  <Send className="w-3.5 h-3.5" />
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>

      {/* Footer matching Design HTML */}
      <footer className="h-12 px-6 md:px-8 border-t border-white/5 flex items-center justify-between bg-black/40 text-[10px] text-white/30 uppercase tracking-widest shrink-0">
        <span>VERSION: V0.3</span>
        <span>Ubicación: {BUILDING_NAME || "Edificio XYZ"}</span>
        <div className="flex gap-4">
          <span>Ayuda</span>
          <span>Privacidad</span>
        </div>
      </footer>

    </div>
  );
}
