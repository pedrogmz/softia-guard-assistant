import express from "express";
import path from "path";
import { createServer as createViteServer } from "vite";
import dotenv from "dotenv";

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

// Backend local (FastAPI + Ollama + RAG + Whisper). Sin dependencias de nube.
// Usamos 127.0.0.1 (no "localhost") a propósito: el fetch de Node resuelve
// "localhost" a IPv6 (::1) y uvicorn escucha solo en IPv4 -> "fetch failed".
const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";

// Proxy en streaming: reenvía /api/* al backend tal cual, sin parsear el cuerpo.
// Así funciona igual para JSON (/api/verify) que para audio binario
// multipart (/api/transcribe). NO usamos express.json() para no consumir el stream.
app.use("/api", async (req, res) => {
  const target = `${BACKEND_URL}/api${req.url}`;
  const hasBody = req.method !== "GET" && req.method !== "HEAD";
  try {
    const headers: Record<string, string> = {};
    if (req.headers["content-type"]) headers["content-type"] = req.headers["content-type"] as string;

    const upstream = await fetch(target, {
      method: req.method,
      headers,
      body: hasBody ? (req as any) : undefined,
      // Requerido por undici para enviar un stream de request en Node.
      ...(hasBody ? { duplex: "half" } : {}),
    } as any);

    res.status(upstream.status);
    const contentType = upstream.headers.get("content-type");
    if (contentType) res.set("content-type", contentType);
    const buffer = Buffer.from(await upstream.arrayBuffer());
    res.send(buffer);
  } catch (error: any) {
    console.error("Backend proxy error:", error?.message || error);
    // Para las rutas que devuelven un VerifyResponse/GateResponse devolvemos el shape
    // que consume App.tsx; para el resto, un error genérico.
    if (["/verify", "/identify", "/access-request"].some((p) => req.url.startsWith(p))) {
      res.status(502).json({
        reply:
          "Disculpe, no puedo contactar con el sistema en este momento. Intente de nuevo en un momento o pida ayuda al vigilante de turno.",
        status: "ERROR",
        apartment: null,
        owner: null,
        action: "show_error",
        assistant_animation: "denied",
      });
    } else {
      res.status(502).json({ error: "backend_unavailable" });
    }
  }
});

// Setup Vite middleware for development or serve built files for production
async function startServer() {
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Frontend server on http://0.0.0.0:${PORT} (API -> ${BACKEND_URL})`);
  });
}

startServer();
