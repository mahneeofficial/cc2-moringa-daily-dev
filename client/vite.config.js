import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true, // Prevents switching to 5174 automatically
    host: true, // bind 0.0.0.0 so the dev server works behind proxies / on LAN
    allowedHosts: true, // allow preview-proxy hostnames (e.g. *.e2b.app sandboxes)
  },
});
