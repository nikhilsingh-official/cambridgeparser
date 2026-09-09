<script setup lang="ts">
// ============================================================================
//
// Public account and data-deletion instructions for users and OAuth reviewers.
// ============================================================================

import LegalPageShell from '@/components_public/LegalPageShell.vue';
import { RouterLink } from 'vue-router';
</script>

<template>
  <LegalPageShell
    eyebrow="Account controls"
    title="Delete Your Data"
    summary="How to request deletion of a CambridgeParser account, its saved study history, and locally stored drafts."
    effective-date="9 September 2026"
  >
    <section>
      <h2>Request account deletion</h2>
      <p>
        Send an email from the address associated with your CambridgeParser
        account to
        <a href="mailto:privacy@cambridgeparser.com?subject=Account%20deletion%20request">privacy@cambridgeparser.com</a>
        with the subject “Account deletion request”. If you signed in with
        Google, Microsoft, or GitHub, use the email shown on your
        CambridgeParser account where possible.
      </p>
      <p>
        We may ask you to complete a sign-in or reply from the account email to
        prevent somebody else from deleting your information. Never send us
        your password, OAuth token, provider secret, or recovery code.
      </p>
    </section>

    <section>
      <h2>What the request deletes</h2>
      <p>After identity verification, deletion covers active-system copies of:</p>
      <ul>
        <li>your CambridgeParser authentication account and profile;</li>
        <li>saved paper attempts, answers, interaction history, and statistics;</li>
        <li>saved pseudocode progress, submissions, scores, and feedback; and</li>
        <li>account-linked grading quota and activity records.</li>
      </ul>
      <p>
        We aim to complete a verified request within 30 days. Limited records
        may be retained where required for security, fraud prevention, dispute
        resolution, or law. Residual encrypted backups may remain until they
        are overwritten under service-provider backup schedules.
      </p>
    </section>

    <section>
      <h2>Clear data stored on your device</h2>
      <p>
        IDE drafts and theme preferences may be stored only in your browser.
        They are not reachable from our database and are not removed by an
        account-deletion request. Use your browser’s “clear site data” control
        for cambridgeparser.com on every device where you used the Service.
        This also removes the local session and signs you out on that device.
      </p>
    </section>

    <section>
      <h2>Disconnect social sign-in</h2>
      <p>
        Deleting CambridgeParser data does not delete your Google, Microsoft,
        or GitHub account. You can separately remove CambridgeParser from the
        connected-app or third-party-access settings in your identity-provider
        account. Revoking provider access alone does not delete study history
        already stored by CambridgeParser, so submit the request above if you
        also want that information removed.
      </p>
    </section>

    <section>
      <h2>Questions</h2>
      <p>
        For access, correction, export, or other privacy questions, see the
        <RouterLink to="/privacy">Privacy Policy</RouterLink> or email
        <a href="mailto:privacy@cambridgeparser.com">privacy@cambridgeparser.com</a>.
      </p>
    </section>
  </LegalPageShell>
</template>
