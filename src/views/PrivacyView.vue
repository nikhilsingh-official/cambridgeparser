<script setup lang="ts">
// ============================================================================
//
// Public privacy notice for CambridgeParser and its OAuth sign-in flows.
// This is product-specific boilerplate and must be reviewed when data handling,
// providers, ownership, or applicable law changes.
// ============================================================================

import LegalPageShell from '@/components_public/LegalPageShell.vue';
import { RouterLink } from 'vue-router';
</script>

<template>
  <LegalPageShell
    eyebrow="Privacy notice"
    title="Privacy Policy"
    summary="What CambridgeParser collects, why it is needed, and the choices you have when using the paper solver, pseudocode IDE, and third-party sign-in."
    effective-date="11 September 2026"
  >
    <section>
      <h2>1. Who this policy covers</h2>
      <p>
        This Privacy Policy applies to CambridgeParser at cambridgeparser.com
        (the <strong>Service</strong>). “CambridgeParser”, “we”, and “us” refer
        to the operator of the Service. This notice applies whether you create
        an account with email and password or use Google, Microsoft, or GitHub
        to sign in.
      </p>
      <p>
        For privacy questions or verified data requests, contact
        <a href="mailto:privacy@cambridgeparser.com">privacy@cambridgeparser.com</a>.
      </p>
    </section>

    <section>
      <h2>2. Information we collect</h2>
      <h3>Account and sign-in information</h3>
      <p>
        When you register, Supabase Auth processes your email address, account
        identifier, authentication method, sign-in events, and security tokens.
        If you choose social sign-in, we receive the basic identity information
        the provider makes available for authentication, such as a stable
        provider account identifier, email address, name, avatar, and related
        profile metadata. The exact fields depend on the provider and your
        provider account settings.
      </p>
      <p>
        CambridgeParser requests only the standard permissions needed to
        identify you and sign you in. We do not request access to Google Drive,
        Gmail, contacts, calendars, GitHub repositories, Microsoft files, or
        the ability to post or act on your behalf.
      </p>

      <h3>Study and submission information</h3>
      <p>When you use the Service, we may store:</p>
      <ul>
        <li>papers and questions attempted, selected answers, marks, and completion status;</li>
        <li>timing, confidence, flags, option changes, and other study interactions;</li>
        <li>pseudocode answers, parser results, rubric scores, marking-point feedback, and attempt history;</li>
        <li>timezone and local study date used to calculate streaks and progress; and</li>
        <li>preferences such as the selected visual theme.</li>
      </ul>

      <h3>Technical information</h3>
      <p>
        Our hosting, authentication, database, and security providers may
        process IP address, browser and device information, request timestamps,
        referring pages, and diagnostic or security logs when you access the
        Service. We use Vercel Web Analytics and Speed Insights to measure page
        visits and real-world performance so we can understand and improve the
        Service. These tools are configured without advertising cookies or
        cross-site behavioral profiles. We do not use third-party advertising
        trackers or behavioral advertising.
      </p>
    </section>

    <section>
      <h2>3. How we use information</h2>
      <p>We use information only as reasonably necessary to:</p>
      <ul>
        <li>create and secure your account and maintain your signed-in session;</li>
        <li>save attempts and restore your progress across devices;</li>
        <li>calculate study statistics, feedback, recommendations, and grading quotas;</li>
        <li>provide pseudocode grading and explain marking decisions;</li>
        <li>operate, troubleshoot, prevent abuse of, and improve the Service;</li>
        <li>respond to support, privacy, and security requests; and</li>
        <li>comply with legal obligations and enforce our Terms.</li>
      </ul>
      <p>
        We do not sell personal information. We do not use OAuth identity data
        for advertising, credit decisions, or unrelated profiling.
      </p>
    </section>

    <section>
      <h2>4. Google API data</h2>
      <p>
        Information received through Google sign-in is used to authenticate
        you, associate you with your CambridgeParser account, display basic
        account information, and protect the Service. We do not use that
        information to train general-purpose artificial-intelligence models.
      </p>
      <p>
        Our handling of information received from Google APIs follows the
        <a href="https://developers.google.com/terms/api-services-user-data-policy" rel="noopener noreferrer">Google API Services User Data Policy</a>,
        including its Limited Use requirements.
      </p>
    </section>

    <section>
      <h2>5. AI-assisted grading</h2>
      <p>
        If you request pseudocode grading, the answer you submit, relevant
        question text, marking criteria, and parser diagnostics are sent by a
        Supabase Edge Function to Google AI Studio and, when configured as a
        fallback, OpenRouter and its selected model provider. This processing
        is necessary to return rubric-based feedback.
      </p>
      <p>
        The grading request is designed not to include your email address,
        OAuth profile, provider account identifier, or OAuth tokens. Do not put
        personal, confidential, or third-party information in a pseudocode
        answer. AI providers process grading requests under their own API terms,
        retention settings, and privacy policies.
      </p>
    </section>

    <section>
      <h2>6. When information is shared</h2>
      <p>We disclose information only in the following circumstances:</p>
      <ul>
        <li>
          <strong>Service providers:</strong> Supabase provides authentication,
          database, and Edge Function infrastructure; Vercel hosts and delivers
          the website; font and content-delivery providers deliver public assets;
          and configured AI providers process grading requests.
        </li>
        <li>
          <strong>Identity providers:</strong> Google, Microsoft, or GitHub
          processes the sign-in you initiate under its own terms. We do not
          control information that you provide directly to that provider.
        </li>
        <li>
          <strong>Legal and safety:</strong> we may disclose information when
          reasonably necessary to comply with law, respond to valid legal
          process, protect users, investigate abuse, or defend legal rights.
        </li>
        <li>
          <strong>Business changes:</strong> information may transfer as part of
          a merger, financing, acquisition, reorganization, or sale, subject to
          this Policy and applicable law.
        </li>
      </ul>
    </section>

    <section>
      <h2>7. Browser storage and cookies</h2>
      <p>
        The Service uses browser storage to maintain your Supabase session,
        remember your theme, and retain in-progress IDE drafts on that device.
        Authentication providers may set their own cookies during sign-in. We
        do not currently use advertising cookies. Clearing site data in your
        browser signs you out and may remove locally saved drafts and settings.
      </p>
    </section>

    <section>
      <h2>8. Retention and deletion</h2>
      <p>
        We retain account and study information while your account is active so
        the Service can preserve your progress. Security and operational logs
        may be retained for a limited period appropriate to troubleshooting,
        abuse prevention, legal compliance, and provider backup schedules.
      </p>
      <p>
        To request deletion of your CambridgeParser account and associated
        study data, follow our <RouterLink to="/data-deletion">data-deletion instructions</RouterLink>
        or email
        <a href="mailto:privacy@cambridgeparser.com?subject=Account%20deletion%20request">privacy@cambridgeparser.com</a>
        from the account email with the subject “Account deletion request”. We
        may ask you to verify control of the account. After verification, we
        will delete the account and associated active-system records within 30
        days unless retention is required by law, security, fraud prevention,
        or dispute resolution. Residual encrypted backups may remain until
        overwritten under provider backup schedules.
      </p>
      <p>
        Account deletion does not automatically clear drafts or preferences
        stored only in your browser; clear site data on each device to remove
        those local copies. You can also revoke CambridgeParser’s social-login
        access from your Google, Microsoft, or GitHub account settings.
      </p>
    </section>

    <section>
      <h2>9. Security</h2>
      <p>
        We use access controls, encrypted HTTPS connections, row-level database
        security, secret management, and user-scoped authorization to protect
        information. No system is completely secure, so we cannot guarantee
        absolute security. Contact us promptly if you believe your account or
        information has been compromised.
      </p>
    </section>

    <section>
      <h2>10. Your privacy rights</h2>
      <p>
        Depending on where you live, you may have rights to access, correct,
        delete, restrict, object to, or receive a portable copy of personal
        information, and to withdraw consent where processing relies on
        consent. Email us to exercise a right. We may verify your identity and
        may retain information where an applicable exception permits or
        requires it. You may also have the right to complain to your local data
        protection authority.
      </p>
    </section>

    <section>
      <h2>11. International processing</h2>
      <p>
        The Service and its providers may process information in countries
        other than yours. Those countries may have different data-protection
        laws. Where required, we rely on provider contractual safeguards or
        other lawful transfer mechanisms.
      </p>
    </section>

    <section>
      <h2>12. Students and children</h2>
      <p>
        CambridgeParser is an educational tool but is not directed to children
        who are too young to consent to an online service under their local
        law. If parental, guardian, or school authorization is required where
        you live, do not create an account without it. A parent or guardian may
        contact us to request review or deletion of a child’s information.
      </p>
    </section>

    <section>
      <h2>13. Changes and contact</h2>
      <p>
        We may update this Policy when the Service, providers, or legal
        requirements change. We will update the date above and provide
        additional notice when a change is material. Questions and requests
        may be sent to
        <a href="mailto:privacy@cambridgeparser.com">privacy@cambridgeparser.com</a>.
      </p>
    </section>
  </LegalPageShell>
</template>
