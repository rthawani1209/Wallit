import { LegalLayout } from "@/components/legal/LegalLayout";

export default function PrivacyPage() {
  return (
    <LegalLayout title="Privacy Policy" updated="August 9, 2026">
      <p>
        Wallit ("we," "our," or "us") helps you track and understand your personal finances by
        connecting to your bank accounts. This policy explains what information we collect, why,
        and how it&apos;s handled. It applies to everyone who creates a Wallit account.
      </p>

      <h2>What we collect</h2>
      <ul>
        <li><strong>Account info</strong> — name, email, date of birth, and a hashed password (or
        nothing, if you sign in with Google).</li>
        <li><strong>Financial data</strong> — when you link a bank account through Plaid, we
        receive your account balances and transaction history (merchant names, amounts, dates,
        and Plaid&apos;s own categorization) directly from Plaid. We never see or store your bank
        login credentials — those go straight to Plaid, not to us.</li>
        <li><strong>Google account info</strong> — if you sign in with Google, we receive your
        name and email from Google to create or match your account.</li>
        <li><strong>What you tell the AI assistant</strong> — messages you send to Wallit&apos;s
        assistant, and the real account data it looks up on your behalf to answer you.</li>
      </ul>

      <h2>How we use it</h2>
      <ul>
        <li>To show you your transactions, balances, spending trends, and upcoming bills.</li>
        <li>To automatically categorize transactions and detect recurring subscriptions and
        unusual spending — this uses rule-based logic first, and Anthropic&apos;s Claude API as a
        fallback for merchants that logic can&apos;t confidently classify.</li>
        <li>To power the AI assistant, which can look up your real transactions, balances, and
        subscriptions to answer your questions, and — only with your explicit confirmation in the
        chat — adjust a budget or create a savings goal on your behalf.</li>
        <li>To look up nearby businesses via Google Places, only when you ask about cheaper
        options nearby and only using the location you provide in that conversation.</li>
      </ul>

      <h2>Who we share it with</h2>
      <p>We don&apos;t sell your data. We share it only with the services that make Wallit work:</p>
      <ul>
        <li><strong>Plaid</strong> — to connect to your bank and retrieve transactions. Plaid has
        its own privacy policy governing how it handles your bank credentials and data.</li>
        <li><strong>Anthropic (Claude API)</strong> — merchant names and transaction details are
        sent to Claude when our own categorization logic can&apos;t confidently classify a
        transaction, and your messages (plus the account data needed to answer them) are sent to
        Claude when you use the AI assistant.</li>
        <li><strong>Google</strong> — for Google sign-in, and for Places lookups when you ask the
        assistant about nearby businesses.</li>
      </ul>

      <h2>How we protect it</h2>
      <ul>
        <li>Passwords are hashed with bcrypt — we never store or can see your actual password.</li>
        <li>Your Plaid access token (the credential used to fetch your bank data) is encrypted at
        rest in our database.</li>
        <li>Sessions use a signed, httpOnly cookie that JavaScript on the page can&apos;t read,
        reducing exposure if a browser extension or script on the page were compromised.</li>
      </ul>

      <h2>Your choices</h2>
      <p>
        You can disconnect a bank account or ask us to delete your account and associated data at
        any time by contacting us at the email below. We&apos;ll confirm once it&apos;s done.
      </p>

      <h2>Children&apos;s privacy</h2>
      <p>
        Wallit is not intended for children. Linking a real bank account is an adult financial
        decision, and we don&apos;t knowingly collect data from anyone not old enough to hold or
        access a bank account in their jurisdiction.
      </p>

      <h2>Changes to this policy</h2>
      <p>
        If this policy changes in a meaningful way, we&apos;ll update the date at the top of this
        page and, where required, notify you directly.
      </p>

      <h2>Contact</h2>
      <p>
        Questions about this policy or your data? Reach us at{" "}
        <a href="mailto:privacy@example.com">privacy@example.com</a>.
      </p>
    </LegalLayout>
  );
}
