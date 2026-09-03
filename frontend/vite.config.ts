import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import {defineConfig} from 'vite';

export default defineConfig(() => {
  return {
    plugins: [react(), tailwindcss()],
    // Trata los modelos 3D .fbx como assets (import ?url devuelve su URL servida)
    assetsInclude: ['**/*.fbx'],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      host: true,
      // Redirige las llamadas /api al backend local Python (FastAPI/Ollama).
      // Ajusta el target si el backend corre en otro host/puerto.
      proxy: {
        '/api': {
          target: process.env.BACKEND_URL || 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      },
      allowedHosts: ['frontend.softiaguardassistant.orb.local', '.orb.local'],
      // HMR is disabled in AI Studio via DISABLE_HMR env var.
      // Do not modifyâfile watching is disabled to prevent flickering during agent edits.
      hmr: process.env.DISABLE_HMR !== 'true',
      // Disable file watching when DISABLE_HMR is true to save CPU during agent edits.
      watch: process.env.DISABLE_HMR === 'true' ? null : {},
    },
  };
});
