import { useEffect, useRef, useState } from "react";
import jsQR from "jsqr";
import { CameraOff, Hash, X } from "lucide-react";
import { PanelKey } from "./panel";

interface QrScannerProps {
  onResult: (code: string) => void;
  onClose: () => void;
  // Alternativa visible si el QR no funciona
  onFallback: () => void;
}

// Sin código detectado en este tiempo, se ofrece la alternativa
const NO_CODE_HINT_MS = 30000;

export default function QrScanner({ onResult, onClose, onFallback }: QrScannerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number>(0);
  const resolvedRef = useRef<boolean>(false);
  // Referencia siempre-actual al callback para no reiniciar la cámara si cambia
  const onResultRef = useRef(onResult);
  const [error, setError] = useState(false);
  const [slow, setSlow] = useState(false);

  useEffect(() => {
    onResultRef.current = onResult;
  });

  useEffect(() => {
    const t = setTimeout(() => setSlow(true), NO_CODE_HINT_MS);
    return () => clearTimeout(t);
  }, []);

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
      // attemptBoth: también lee QR invertidos (pantallas en modo oscuro)
      const code = jsQR(imageData.data, width, height, { inversionAttempts: "attemptBoth" });
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
        console.error("getUserMedia no disponible (¿contexto seguro? usa localhost o HTTPS)");
        setError(true);
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
        if (!cancelled) setError(true);
      }
    })();

    return () => {
      cancelled = true;
      stopCamera();
    };
  }, []);

  return (
    <CameraPage
      title="Muestre su código QR a la cámara"
      hint={
        error
          ? "La cámara no está disponible en este momento. Marque el apartamento para continuar."
          : slow
            ? "Todavía no veo el código. Suba el brillo del teléfono o marque el apartamento."
            : "Acerque la pantalla de su teléfono al recuadro."
      }
      frame="square"
      error={error}
      videoRef={videoRef}
      actions={
        <>
          <PanelKey tone={error || slow ? "call" : "key"} icon={<Hash />} onClick={onFallback} className="flex-1">
            Marcar apartamento
          </PanelKey>
          <PanelKey tone="quiet" icon={<X />} onClick={onClose} className="flex-1">
            Cancelar
          </PanelKey>
        </>
      }
    >
      <canvas ref={canvasRef} className="hidden" />
    </CameraPage>
  );
}

// Página de cámara compartida por el QR y la cédula: la cámara ocupa la hoja del libro
export function CameraPage({
  title,
  hint,
  frame,
  error,
  videoRef,
  actions,
  children,
}: {
  title: string;
  hint: string;
  frame: "square" | "card";
  error: boolean;
  videoRef: React.RefObject<HTMLVideoElement | null>;
  actions: React.ReactNode;
  children?: React.ReactNode;
}) {
  const corner = "absolute h-[2.2rem] w-[2.2rem] border-legend";
  return (
    <div className="brushed absolute inset-0 z-30 flex flex-col p-[1.6rem]">
      <h2 className="text-[2.4rem] font-bold leading-tight text-ink">{title}</h2>
      <p aria-live="polite" className="mt-[0.6rem] max-w-[36rem] text-[1.4rem] leading-snug text-ink-soft">
        {hint}
      </p>
      <div className="flex flex-1 items-center justify-center py-[1rem]">
        <div className={`relative w-full max-w-[32rem] overflow-hidden rounded-[0.3rem] bg-[#0d0f12] ${frame === "square" ? "aspect-square" : "aspect-[4/3]"}`}>
          {error ? (
            <div className="flex h-full w-full flex-col items-center justify-center gap-[0.8rem] bg-key text-ink-soft">
              <CameraOff className="h-[4rem] w-[4rem]" />
              <span className="text-[1.3rem] font-bold">Cámara no disponible</span>
            </div>
          ) : (
            <video ref={videoRef} className="h-full w-full object-cover" muted playsInline />
          )}
          {!error && <div className={`pointer-events-none absolute ${frame === "square" ? "inset-[14%]" : "inset-x-[10%] inset-y-[18%]"}`}>
            <span className={`${corner} left-0 top-0 border-l-[0.3rem] border-t-[0.3rem]`} />
            <span className={`${corner} right-0 top-0 border-r-[0.3rem] border-t-[0.3rem]`} />
            <span className={`${corner} bottom-0 left-0 border-b-[0.3rem] border-l-[0.3rem]`} />
            <span className={`${corner} bottom-0 right-0 border-b-[0.3rem] border-r-[0.3rem]`} />
          </div>}
          {children}
        </div>
      </div>
      <div className="flex gap-[0.8rem]">{actions}</div>
    </div>
  );
}
