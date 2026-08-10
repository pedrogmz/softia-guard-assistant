import express from "express";
import path from "path";
import { createServer as createViteServer } from "vite";
import dotenv from "dotenv";

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

// Backend local (FastAPI + Ollama + RAG). Sin dependencias de nube.
// Usamos 127.0.0.1 (no "localhost") a propósito: el fetch de Node resuelve
// "localhost" a IPv6 (::1) y uvicorn escucha solo en IPv4 -> "fetch failed".
const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";

app.use(express.json());

// Proxy: todo /api/* se reenvía al backend Python local, manteniendo el
// mismo origen para el navegador. El backend resuelve con LLM local + RAG.
app.use("/api", async (req, res) => {
  const target = `${BACKEND_URL}/api${req.url}`;
  try {
    const upstream = await fetch(target, {
      method: req.method,
      headers: { "Content-Type": "application/json" },
      body: req.method === "GET" || req.method === "HEAD" ? undefined : JSON.stringify(req.body),
    });
    const data = await upstream.json();
    res.status(upstream.status).json(data);
  } catch (error: any) {
    console.error("Backend proxy error:", error?.message || error);
    // Contingencia con el mismo shape que consume el frontend (App.tsx).
    res.status(502).json({
      reply:
        "Disculpe las molestias, no puedo contactar con el sistema de seguridad en este momento. Por favor, intente de nuevo o presione el Botón de Pánico.",
      status: "ERROR",
      apartment: null,
      owner: null,
      action: "show_error",
      assistant_animation: "denied",
    });
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
