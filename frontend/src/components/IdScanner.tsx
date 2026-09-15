import { useEffect, useRef, useState } from "react";
import { Camera, X } from "lucide-react";

interface IdScannerProps {
  onCapture: (image: Blob) => void;
  onClose: () => void;
}

// Cámara para mostrar la cédula: captura un fotograma fijo y lo entrega como imagen (JPEG).
export default function IdScanner({ onCapture, onClose }: IdScannerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const onCaptureRef = useRef(onCapture);
  const [error, setError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    onCaptureRef.current = onCapture;
  });

  useEffect(() => {
    let cancelled = false;
    const stop = () => {
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    };
    (async () => {
      if (!navigator.mediaDevices?.getUserMedia) {
        setError("Este navegador no permite el acceso a la cámara.");
        return;
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        const video = videoRef.current;
        if (!video) return;
        video.srcObject = stream;
        video.setAttribute("playsinline", "true");
        await video.play();
        setReady(true);
      } catch (e) {
        console.error("No se pudo acceder a la cámara:", e);
        if (!cancelled) setError("No se pudo acceder a la cámara. Verifique los permisos y que la página use HTTPS o localhost.");
      }
    })();
    return () => {
      cancelled = true;
      stop();
    };
  }, []);

  const capture = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || !ready) return;
    const w = video.videoWidth;
    const h = video.videoHeight;
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, w, h);
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    canvas.toBlob((blob) => {
      if (blob) onCaptureRef.current(blob);
    }, "image/jpeg", 0.92);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-md bg-[#0f0f0f] border border-cyan-500/20 rounded-2xl overflow-hidden shadow-2xl">
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
          <span className="text-sm font-mono text-cyan-300 tracking-wider">Mostrar cédula de identidad</span>
          <button
            onClick={onClose}
            title="Cerrar"
            className="p-1.5 rounded-lg text-white/60 hover:text-white hover:bg-white/10 transition-all cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="relative aspect-[4/3] bg-black">
          {error ? (
            <div className="absolute inset-0 flex items-center justify-center p-6 text-center text-rose-300 text-sm">
              {error}
            </div>
          ) : (
            <>
              <video ref={videoRef} className="w-full h-full object-cover" muted playsInline />
              <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
                <div className="w-4/5 h-3/5 border-2 border-cyan-400/70 rounded-xl" />
              </div>
            </>
          )}
          <canvas ref={canvasRef} className="hidden" />
        </div>

        <div className="px-4 py-3 flex items-center justify-between gap-3">
          <span className="text-xs text-white/50">
            {error ? "Cierre e intente de nuevo" : "Encuadre la cédula y capture"}
          </span>
          <button
            onClick={capture}
            disabled={!ready || !!error}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-sm disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition-all"
          >
            <Camera className="w-4 h-4" /> Capturar
          </button>
        </div>
      </div>
    </div>
  );
}
