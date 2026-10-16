import type { NextConfig } from "next";

// Endereço do backend FastAPI. Em produção, defina API_URL no servidor.
const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  experimental: {
    agentFeedback: true,
  },
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  // O navegador fala só com o Next; o Next repassa /api/v1 para o FastAPI.
  // Assim o cookie de sessão fica na mesma origem e não é preciso configurar CORS.
  async rewrites() {
    return [{ source: "/api/v1/:caminho*", destination: `${API_URL}/api/v1/:caminho*` }];
  },
};

export default nextConfig;
