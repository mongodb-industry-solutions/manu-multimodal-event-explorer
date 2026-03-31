/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // Proxy browser /api calls to backend sidecar (server-side only)
    // Use 127.0.0.1 instead of localhost to avoid IPv6 issues
    return [
      {
        source: '/api/:path*',
        destination: 'http://127.0.0.1:8000/api/:path*',
      },
    ];
  },
};

export default nextConfig;
