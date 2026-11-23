import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Local-dev convenience: with NEXT_PUBLIC_API_URL=/backend the browser calls
  // this Next.js server, which forwards to the FastAPI server. Useful when the
  // browser can't reach the API port directly (e.g. GitHub Codespaces).
  // In production NEXT_PUBLIC_API_URL is the full Hugging Face URL and this is unused.
  async rewrites() {
    const target = process.env.API_PROXY_TARGET ?? "http://localhost:7860";
    return [{ source: "/backend/:path*", destination: `${target}/:path*` }];
  },
};

export default nextConfig;
