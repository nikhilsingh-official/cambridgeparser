import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import { readFile, writeFile } from 'node:fs/promises'
// build crawler-readable heads from the exact catalogue used at runtime.
import { STATIC_SEO_ROUTES, renderSeoDocument, resolveSeoMetadata } from './src/lib/seo'

// Vue remains a client-rendered application, but crawlers and link-preview
// bots receive the correct route title, canonical, robots rule, social card,
// and JSON-LD before JavaScript runs.
function staticSeoDocuments() {
  return {
    name: 'cambridgeparser-static-seo-documents',
    apply: 'build' as const,
    enforce: 'post' as const,
    async closeBundle() {
      const outputDirectory = path.resolve(__dirname, 'dist')
      const template = await readFile(path.join(outputDirectory, 'index.html'), 'utf8')

      await Promise.all(STATIC_SEO_ROUTES.map(async route => {
        const seo = resolveSeoMetadata(route.page, route.routePath)
        const html = renderSeoDocument(template, seo)
        await writeFile(path.join(outputDirectory, route.outputFile), html)
      }))
    },
  }
}

export default defineConfig({
  plugins: [vue(), staticSeoDocuments()],
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
          // keep the manual chunk aligned with LoadingScreen's
          // expression-free canvas player so the full eval build stays out.
          lottie: ['lottie-web/build/player/lottie_light_canvas'],
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
