<!--
Research date: 2026-09-01.
Sources are limited to official Supabase documentation and first-party Supabase
reference/source material. Recommendations are labelled separately from facts.
-->

# Supabase password recovery options (CP-007)

**Implementation status (2026-09-07):** Option A is implemented and verified
against the local Supabase Auth server and Mailpit. The remaining work is hosted
configuration and preview/production verification, not application wiring.

## Decision summary

**Recommendation:** keep the application's current browser-only **implicit auth
flow** and add a dedicated `/reset-password` experience. The request form should
call `resetPasswordForEmail()`, always show the same acknowledgement regardless
of whether the account exists, and redirect the email link to the dedicated
route. The application-level auth listener should retain the
`PASSWORD_RECOVERY` event long enough for that route to render a confirmed
new-password form. The form should call `updateUser({ password })`, then clear
recovery state and sign the user out so they can verify the new password by
signing in normally.

This is a recommendation, not a Supabase requirement. It is the smallest fit
for this repository because it is a client-rendered Vue SPA with no auth server,
uses `createWebHistory()`, and currently creates its Supabase client without a
`flowType`, which leaves supabase-js on its documented JavaScript client default
of implicit flow. Supabase explicitly describes implicit flow as suitable only
for client-side apps; PKCE is needed when a server must receive the session.
[Password-based Auth](https://supabase.com/docs/guides/auth/passwords)
[Implicit flow](https://supabase.com/docs/guides/auth/sessions/implicit-flow)

Do not implement recovery on the existing `/login` callback. That route is
`guestOnly`, so the recovery session created from a valid link is immediately
redirected to `/dashboard`. The current store also discards the auth event name,
so it cannot distinguish `PASSWORD_RECOVERY` from an ordinary sign-in. These are
repository observations from `src/router/router.ts` and
`src/stores/useAuth.ts`, not claims about Supabase.

## Documented Supabase facts

Supabase's documented recovery flow has two steps:

1. Call `supabase.auth.resetPasswordForEmail(email, { redirectTo })` to send the
   recovery email.
2. On the authenticated change-password page, collect the new password and call
   `supabase.auth.updateUser({ password })`.

`resetPasswordForEmail()` only sends the email; it does not change the password.
The change-password page is documented as accessible only to authenticated
users. [Password-based Auth — Resetting a password](https://supabase.com/docs/guides/auth/passwords#resetting-a-password)
[JavaScript `resetPasswordForEmail`](https://supabase.com/docs/reference/javascript/auth-resetpasswordforemail)
[JavaScript `updateUser`](https://supabase.com/docs/reference/javascript/auth-updateuser)

When a recovery link succeeds, supabase-js emits a `PASSWORD_RECOVERY` auth
event with a session. Supabase's reference example uses that event to show the
new-password UI and then calls `updateUser()`.
[JavaScript `onAuthStateChange`](https://supabase.com/docs/reference/javascript/auth-onauthstatechange#listen-to-password-recovery-events)

`resetPasswordForEmail()` deliberately does not reveal whether the email maps
to an account: a nonexistent email produces no message but still returns
without an error. The UI must therefore use a generic response such as “If an
account exists, check your email.”
[Password-based Auth — Resetting a password](https://supabase.com/docs/guides/auth/passwords#resetting-a-password)

The `redirectTo` value must match the project's Auth Redirect URLs allow-list.
The configured Site URL is the fallback when no redirect is supplied, and
Supabase calls correct Site URL configuration critical for password resets.
Supabase recommends an exact production redirect instead of a wildcard; broader
wildcards are intended for local or preview environments.
[Redirect URLs](https://supabase.com/docs/guides/auth/redirect-urls)

If authentication fails, Supabase still redirects to the requested application
URL and puts error details in URL parameters/fragments. `otp_expired` identifies
an expired recovery token. PKCE can additionally return `flow_state_expired`,
`flow_state_not_found`, or `bad_code_verifier`. These should lead to a safe
“link expired or invalid” state with a way to request another email, not a blank
page or dashboard redirect.
[Redirect URL error handling](https://supabase.com/docs/guides/auth/redirect-urls#error-handling)
[Auth error codes](https://supabase.com/docs/guides/auth/debugging/error-codes)

Auth email links are single-use. Corporate email scanners can consume a link
before the user clicks it; Supabase's production checklist suggests an
intermediate page on a controlled domain whose button performs the actual
single-use navigation. Custom SMTP link tracking can also alter auth links and
should be disabled.
[Production Checklist — Email link validity](https://supabase.com/docs/guides/deployment/going-into-prod#email-link-validity)

Supabase's built-in email service is best-effort and limited to two emails per
hour across email-sending Auth endpoints. The password reset endpoint also has
a default per-user cooldown of 60 seconds. Supabase recommends custom SMTP for
production; CAPTCHA is available on password-reset endpoints for abuse
protection.
[Password-based Auth — Email sending](https://supabase.com/docs/guides/auth/passwords#email-sending)
[Auth rate limits](https://supabase.com/docs/guides/auth/rate-limits)
[Production Checklist — Abuse prevention](https://supabase.com/docs/guides/deployment/going-into-prod#abuse-prevention)

## Flow choices for this Vue SPA

### Option A — retain implicit flow (recommended now)

**Documented behavior:** after verification, implicit flow returns access and
refresh tokens in the URL fragment. The browser client detects them, persists
the session in local storage, and emits the auth event. URL fragments are not
sent to the hosting server. This flow only works on the client.
[Implicit flow](https://supabase.com/docs/guides/auth/sessions/implicit-flow)

**Repository fit:** the application is already a client-only SPA and its single
Supabase client uses the JavaScript default. Vue Router uses history routing,
so the auth token fragment does not collide with application routing. A direct
redirect such as `https://cambridgeparser.com/reset-password` is a normal Vercel
deep link and must also be covered by the deployment's SPA rewrite.

**Trade-offs:** credentials briefly exist in the fragment until supabase-js
extracts them. They are not included in ordinary HTTP requests or server access
logs, but browser extensions and scripts executing in the page remain part of
the client-side threat model. **Inference from the documented PKCE constraint:**
because implicit flow has no originating-browser code verifier, it keeps emailed
links usable when opened on a different browser/device from the one that
requested them.

### Option B — switch the shared client to PKCE

**Documented behavior:** PKCE redirects with a short-lived, single-use `code`
instead of tokens. The code is valid for five minutes and is exchanged for a
session; `detectSessionInUrl: true` can make the client perform that exchange.
Password Recovery is one of the routes supported by Supabase PKCE.
[PKCE flow](https://supabase.com/docs/guides/auth/sessions/pkce-flow)
[Advanced Auth guide — PKCE support](https://supabase.com/docs/guides/auth/server-side/advanced-guide#which-authentication-flows-have-pkce-support)

**Material limitation:** the verifier is stored when recovery is requested, so
the email link must be completed in the same browser and device. Starting an
overlapping PKCE flow can overwrite the earlier verifier unless Supabase's
experimental flow-ID option is enabled. That is meaningful friction for a
password-recovery email and is why this note does not recommend changing the
whole application's flow solely for CP-007.
[PKCE flow — Limitations and overlapping flows](https://supabase.com/docs/guides/auth/sessions/pkce-flow#limitations)

PKCE becomes the better architecture if CambridgeParser later adds SSR or a
server callback that must receive auth state. That would be an auth-wide
migration affecting OAuth and signup too, not a small recovery-only change.

The installed supabase-js version is `2.112.3`. This matters only if PKCE is
chosen: Supabase fixed missing `PASSWORD_RECOVERY` emission for PKCE recovery in
`2.104.1`, so the installed version includes that fix.
[supabase-js changelog](https://github.com/supabase/supabase-js/blob/master/CHANGELOG.md#21041-2026-04-23)

### Option C — recovery OTP form / custom email template

Supabase email templates expose both a six-digit `{{ .Token }}` and
`{{ .TokenHash }}`. A custom flow can ask the user for the code and call
`verifyOtp({ email, token, type: 'recovery' })`, then show the password form once
a session is returned. This avoids single-click links being consumed by link
scanners but adds an email-and-code screen, custom template work, and more test
surface.
[Email Templates](https://supabase.com/docs/guides/auth/auth-email-templates)
[OTP verification troubleshooting](https://supabase.com/docs/guides/troubleshooting/otp-verification-failures-token-has-expired-or-otp_expired-errors-5ee4d0)

This is a viable later hardening option, not the lowest-complexity CP-007 fix.

## Recommended application state machine

The following is a repository recommendation based on the documented two-step
flow; it is not prescribed verbatim by Supabase.

1. **Request form:** expose “Forgot password?” from sign-in. Accept a syntactically
   valid email, call the existing store method, and always show the same success
   acknowledgement. Disable repeat submission while pending and map rate-limit
   and network errors separately.
2. **Email callback:** change `redirectTo` from `/login` to
   `/reset-password`. Add the exact production and development URLs to the
   hosted/local allow-lists.
3. **Capture recovery:** preserve `PASSWORD_RECOVERY` in the central auth store.
   The listener is installed before router navigation, while a route component
   listener may mount after the one-time event has already fired.
4. **Recovery route:** do not mark the route `guestOnly`. Render the form only
   when a recovery event/session was observed. If an auth error is present in
   the callback URL, prioritize the error even if an unrelated old session
   exists.
5. **New password:** require password and confirmation fields, reject mismatch
   locally, and let `updateUser()` enforce the hosted project's actual password
   policy. Branch on stable Auth `error.code` values rather than message text.
   At minimum, map `weak_password`, `same_password`, `validation_failed`,
   `session_expired`, `session_not_found`, `over_email_send_rate_limit`, and
   `over_request_rate_limit` to actionable text.
   [Auth error handling](https://supabase.com/docs/guides/auth/debugging/error-codes#best-practices-for-error-handling)
6. **Completion:** clear recovery state, call `signOut()`, and route to sign-in
   with a “Password updated” notice. Supabase only requires `updateUser()`;
   signing out is recommended here so the user verifies the new credential and
   the temporary recovery session is not left active.
7. **Invalid/expired/reused callback:** show one neutral error, remove sensitive
   or noisy callback parameters with `history.replaceState`, and provide a
   button back to the request form. Do not silently route to the dashboard.

## Configuration required before hosted rollout can be called complete

These are repository observations and recommendations:

- Hosted Auth **Site URL:** `https://www.cambridgeparser.com` (the current
  canonical origin; Vercel redirects the apex to `www`).
- Hosted exact Redirect URL:
  `https://www.cambridgeparser.com/reset-password`.
- Optionally keep `https://cambridgeparser.com/reset-password` as a second exact
  Redirect URL in case the apex redirect is changed later.
- Preview redirect patterns only if password recovery is intentionally tested
  on previews; keep the production entry exact.
- Local Site URL matches Vite (`http://127.0.0.1:5173`), and local redirect
  patterns cover both `127.0.0.1` and `localhost` on port 5173.
- Verify the Reset Password email template honors `{{ .RedirectTo }}`. Supabase
  notes that customized templates may need this instead of `{{ .SiteURL }}`.
  [Redirect URLs — Email templates](https://supabase.com/docs/guides/auth/redirect-urls#email-templates-when-using-redirectto)
- Configure production SMTP before relying on recovery as an availability
  feature; the built-in sender is explicitly best-effort.
- Decide the hosted password-strength policy first, then mirror it as guidance
  in the form. Supabase recommends at least eight characters and supports
  stronger character requirements and leaked-password protection; the backend
  error remains authoritative.
  [Password security](https://supabase.com/docs/guides/auth/password-security)

## Security and UX acceptance criteria

- Requesting recovery for an existing and nonexistent email produces the same
  visible response.
- Request and submit buttons prevent double submission; 429/rate-limit and
  network failures remain distinguishable from the neutral account response.
- The reset form is never shown for a normal sign-in session merely because the
  user navigated directly to `/reset-password`.
- Password and confirmation values are never logged, placed in a URL, or saved
  in local/session storage.
- Weak and mismatched passwords leave the recovery form usable.
- A successful update cannot be submitted twice.
- Expired, malformed, already-used, and email-scanner-consumed links show a
  recoverable error with a new-request action.
- Refresh and browser back/forward behavior do not reveal the password or
  accidentally re-submit it. A refresh after the one-time callback may require
  requesting a fresh link; that is preferable to treating an ordinary persisted
  session as proof of recovery intent.
- Test locally through Mailpit; Supabase documents that the CLI captures local
  auth emails there. [Local development with Mailpit](https://supabase.com/docs/guides/auth/passwords#local-development-with-mailpit)
- Test the hosted flow with the real SMTP provider, exact production redirect,
  SPA deep-link rewrite, fresh link, expired link, reused link, nonexistent
  account, and a different browser/device.

## Implementation boundary

The application implementation now includes the dedicated route and form,
central recovery-event state, neutral request UI, stable Auth-code handling,
callback cleanup, local Auth URL configuration, and focused state-rule tests.
A real local recovery email was followed through password update, sign-out, and
fresh login. No database migration or Edge Function is required for this flow.

The repository cannot configure the hosted Supabase dashboard or SMTP account.
Before launch, add the exact production redirect, verify the Reset Password
template uses the intended redirect, configure SMTP, and repeat fresh, expired,
reused, nonexistent-account, and cross-device cases against the deployed app.
