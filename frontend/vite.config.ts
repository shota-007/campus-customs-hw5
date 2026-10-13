import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dashboard dev server. It calls the FastAPI backend at VITE_API_URL (default http://localhost:8000).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
});
