import { spawn } from 'node:child_process'
import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const repoRoot = fileURLToPath(new URL('../../..', import.meta.url))

// Dev-server grading endpoint. Mirrors the production contract: the browser
// POSTs {record_id, source, parse} to /api/grade and gets a grading-result/v1 JSON
// back. Locally it shells out to the real Python pipeline (dry-run without
// OPENROUTER_API_KEY); in production api/grade.py runs as a Vercel Function and
// reads the key from Vercel's server-side environment.
function gradingApiPlugin() {
  const handler = (req, res, next) => {
    if (req.method !== 'POST') {
      next()
      return
    }
    let body = ''
    req.on('data', (chunk) => {
      body += chunk
    })
    req.on('end', () => {
      const python = spawn('python3', ['-m', 'src.website.grade_one'], {
        cwd: repoRoot,
        env: process.env,
      })
      let stdout = ''
      let stderr = ''
      python.stdout.on('data', (chunk) => {
        stdout += chunk
      })
      python.stderr.on('data', (chunk) => {
        stderr += chunk
      })
      python.on('error', (error) => {
        res.statusCode = 500
        res.setHeader('Content-Type', 'application/json')
        res.end(JSON.stringify({ ok: false, result: null, error: String(error) }))
      })
      python.on('close', (code) => {
        res.setHeader('Content-Type', 'application/json')
        if (code === 0 && stdout) {
          res.end(stdout)
        } else {
          res.statusCode = 500
          res.end(
            JSON.stringify({
              ok: false,
              result: null,
              error: stderr || `grading process exited with code ${code}`,
            }),
          )
        }
      })
      python.stdin.write(body)
      python.stdin.end()
    })
  }

  return {
    name: 'grading-api',
    configureServer(server) {
      server.middlewares.use('/api/grade', handler)
    },
    configurePreviewServer(server) {
      server.middlewares.use('/api/grade', handler)
    },
  }
}

export default defineConfig({
  root: fileURLToPath(new URL('.', import.meta.url)),
  base: './',
  plugins: [vue(), gradingApiPlugin()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
    outDir: '../static',
    emptyOutDir: true,
  },
})
