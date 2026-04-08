import { defineConfig } from 'vite'
import { resolve } from 'path'

export default defineConfig({
  // Root is the frontend/ directory
  root: resolve(__dirname),

  // Dev server — proxies /api/* back to Flask so you can work against a live
  // backend without CORS issues or changing any fetch URLs in JS.
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },

  build: {
    // Output directory relative to project root (frontend/)
    outDir: resolve(__dirname, '../static/dist'),

    // Emit manifest.json so Flask can resolve hashed filenames
    manifest: true,

    // Clear the output dir before each build
    emptyOutDir: true,

    rollupOptions: {
      // Multiple JS entry points — CSS is imported inside each .js file
      input: {
        main: resolve(__dirname, 'js/main.js'),
        auth: resolve(__dirname, 'js/auth.js'),
      },

      output: {
        // Predictable chunk naming
        entryFileNames: 'assets/[name]-[hash].js',
        chunkFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash][extname]',
      },
    },
  },
})