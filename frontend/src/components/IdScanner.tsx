import { useEffect, useRef, useState } from "react";
import { Camera, Keyboard, X } from "lucide-react";
import { PanelKey } from "./panel";
import { CameraPage } from "./QrScanner";

interface IdScannerProps {
  onCapture: (image: Blob) => void;
  onClose: () => void;
  // Alternativa: escribir el número de cédula en el teclado
  onType: () => void;
}

// Cámara para mostrar la cédula: captura un fotograma fijo y lo entrega como imagen (JPEG).
export default function IdScanner({ onCapture, onClose, onType }: IdScannerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const onCaptureRef = useRef(onCapture);
  const [error, setError] = useState(false);
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
        console.error("getUserMedia no disponible (¿contexto seguro? usa localhost o HTTPS)");
        setError(true);
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
        if (!cancelled) setError(true);
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
    <CameraPage
      title="Muestre su cédula a la cámara"
      hint={
        error
          ? "La cámara no está disponible en este momento. Puede escribir el número de su cédula."
          : "Ponga la cédula dentro del recuadro, con la foto hacia la cámara, y toque «Tomar foto»."
      }
      frame="card"
      error={error}
      videoRef={videoRef}
      actions={
        <div className="flex w-full flex-col gap-[0.6rem]">
          {!error && (
            <PanelKey tone="call" icon={<Camera />} onClick={capture} disabled={!ready} className="min-h-[4rem] text-[1.4rem]">
              Tomar foto
            </PanelKey>
          )}
          <div className="flex gap-[0.8rem]">
            <PanelKey tone={error ? "call" : "key"} icon={<Keyboard />} onClick={onType} className="flex-1">
              Escribir el número
            </PanelKey>
            <PanelKey tone="quiet" icon={<X />} onClick={onClose} className="flex-1">
              Cancelar
            </PanelKey>
          </div>
        </div>
      }
    >
      <canvas ref={canvasRef} className="hidden" />
    </CameraPage>
  );
}
