import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ command }) => {
  // A production build bakes the API URL in at build time -- there is no way
  // to set it afterwards. Left unset, the built app quietly points at
  // http://localhost:8000, which works perfectly on the machine that built it
  // and fails on every other machine in the world with a console error nobody
  // will be looking at. Better to refuse to build.
  if (command === 'build' && !process.env.VITE_API_BASE) {
    throw new Error(
      'VITE_API_BASE is not set.\n\n' +
        'It must be the full public URL of the backend, e.g.\n' +
        '  https://vitalis-engine-production.up.railway.app\n\n' +
        'On Vercel: Project Settings -> Environment Variables.\n' +
        'Locally:   VITE_API_BASE=http://localhost:8000 npm run build\n',
    )
  }

  return { plugins: [react()] }
})
