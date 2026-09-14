import { useEffect, useRef, useState } from "react";
import jsQR from "jsqr";
import { X } from "lucide-react";

interface QrScannerProps {
  onResult: (code: string) => void;
  onClose: () => void;
}

export default function QrScanner({ onResult, onClose }: QrScannerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number>(0);
  const resolvedRef = useRef<boolean>(false);
  // Referencia siempre-actual al callback para no reiniciar la cámara si cambia
  const onResultRef = useRef(onResult);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    onResultRef.current = onResult;
  });

  useEffect(() => {
    let cancelled = false;

    const stopCamera = () => {
      cancelAnimationFrame(rafRef.current);
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    };

    const scanFrame = () => {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (!video || !canvas || video.readyState !== video.HAVE_ENOUGH_DATA) {
        rafRef.current = requestAnimationFrame(scanFrame);
        return;
      }
      const width = video.videoWidth;
      const height = video.videoHeight;
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext("2d", { willReadFrequently: true });
      if (!ctx) {
        rafRef.current = requestAnimationFrame(scanFrame);
        return;
      }
      ctx.drawImage(video, 0, 0, width, height);
      const imageData = ctx.getImageData(0, 0, width, height);
      const code = jsQR(imageData.data, width, height, { inversionAttempts: "dontInvert" });
      if (code && code.data && !resolvedRef.current) {
        resolvedRef.current = true;
        stopCamera();
        onResultRef.current(code.data.trim());
        return;
      }
      rafRef.current = requestAnimationFrame(scanFrame);
    };

    (async () => {
      if (!navigator.mediaDevices?.getUserMedia) {
        setError("Este navegador no permite el acceso a la cámara.");
        return;
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment" },
        });
        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }
        streamRef.current = stream;
        const video = videoRef.current;
        if (!video) return;
        video.srcObject = stream;
        video.setAttribute("playsinline", "true");
        await video.play();
        rafRef.current = requestAnimationFrame(scanFrame);
      } catch (e) {
        console.error("No se pudo acceder a la cámara:", e);
        if (!cancelled) {
          setError(
            "No se pudo acceder a la cámara. Verifique los permisos y que la página use HTTPS o localhost."
          );
        }
      }
    })();

    return () => {
      cancelled = true;
      stopCamera();
    };
  }, []);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-md bg-[#0f0f0f] border border-cyan-500/20 rounded-2xl overflow-hidden shadow-2xl">
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
          <span className="text-sm font-mono text-cyan-300 tracking-wider">Escanear código QR</span>
          <button
            onClick={onClose}
            title="Cerrar"
            className="p-1.5 rounded-lg text-white/60 hover:text-white hover:bg-white/10 transition-all cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="relative aspect-square bg-black">
          {error ? (
            <div className="absolute inset-0 flex items-center justify-center p-6 text-center text-rose-300 text-sm">
              {error}
            </div>
          ) : (
            <>
              <video ref={videoRef} className="w-full h-full object-cover" muted playsInline />
              <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
                <div className="w-2/3 aspect-square border-2 border-cyan-400/70 rounded-xl shadow-[0_0_0_9999px_rgba(0,0,0,0.35)]" />
              </div>
            </>
          )}
          <canvas ref={canvasRef} className="hidden" />
        </div>

        <div className="px-4 py-3 text-center text-xs text-white/50">
          {error ? "Cierre e intente de nuevo" : "Coloque el código QR dentro del recuadro"}
        </div>
      </div>
    </div>
  );
}
