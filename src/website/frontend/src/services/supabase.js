// Central Supabase client for the web client.
//
// Replaces the Firebase initialization this module used to hold. The URL and
// anon key are public by design: they identify the project and grant nothing on
// their own. Access is enforced by Row Level Security (see
// supabase/migrations/), exactly as it used to be enforced by
// database.rules.json. The only true secrets (the grading provider API keys)
// live in the Vercel Function's environment and are never imported here.
//
// This project is shared with the Soluer solver under apps/solver, which is the
// point: one auth.users table means signing into either app is the same
// account. Both clients therefore must agree on these two values.
//
// Everything Supabase-related is created once, here, so the rest of the app
// never touches the SDK's init surface directly.

import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || 'http://127.0.0.1:54321'
const SUPABASE_ANON_KEY =
  import.meta.env.VITE_SUPABASE_ANON_KEY
  || 'sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH'

// Both fall back to the local `supabase start` defaults so `npm run dev:website`
// works with no .env present. A production build must set them; see
// docs/roadmap.md Part D on making a missing URL fail the build rather than
// silently pointing a deployed site at localhost.
export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    // The IDE routes with createWebHashHistory, so OAuth implicit-flow tokens
    // returned in the URL fragment would collide with the router's own use of
    // it. PKCE returns a ?code query parameter instead and does not.
    flowType: 'pkce',
  },
})
