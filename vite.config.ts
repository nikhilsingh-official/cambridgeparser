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
          // ECharts is ~690 kB raw. Left in the route chunk it made
          // StatsPage the largest bundle in the app and re-downloaded on every
          // deploy that touched the page; split out it caches independently.
          echarts: ['echarts/core', 'echarts/charts', 'echarts/components', 'echarts/renderers', 'echarts/features'],
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