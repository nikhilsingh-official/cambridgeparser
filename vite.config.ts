import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  build: {
    rollupOptions: {
      output: {
        // split the heavy third-party libraries out of the route chunks so
        // they are cached independently of application code - a change to a
        // component should not force a re-download of pdf.js.
        manualChunks: {
          pdfjs: ['pdfjs-dist'],
          supabase: ['@supabase/supabase-js'],
          lottie: ['lottie-web'],
        },
      },
    },
  },
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `
          @use "@/styles/main.scss" as *;
        `
      }
    }
  }
})