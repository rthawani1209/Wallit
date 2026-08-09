import { LegalLayout } from "@/components/legal/LegalLayout";

export default function TermsPage() {
  return (
    <LegalLayout title="Terms of Service" updated="August 9, 2026">
      <p>
        These terms govern your use of Wallit. By creating an account, you agree to them. If you
        don&apos;t agree, please don&apos;t use Wallit.
      </p>

      <h2>What Wallit is</h2>
      <p>
        Wallit is a personal finance tool that connects to your bank accounts (via Plaid) to help
        you track spending, detect subscriptions, budget, and answer questions about your own
        financial data through an AI assistant. Wallit is <strong>not a bank</strong>, does not
        hold or move your money, and is not a licensed financial, investment, or tax advisor.
        Nothing in the app — including anything the AI assistant says — is personalized financial
        or investment advice.
      </p>

      <h2>Eligibility</h2>
      <p>
        You must be at least 18 years old to create a Wallit account, and you must provide
        accurate information when doing so.
      </p>

      <h2>Your account</h2>
      <ul>
        <li>You&apos;re responsible for keeping your login credentials secure.</li>
        <li>One account per person. Don&apos;t share your login.</li>
        <li>You&apos;re responsible for the accuracy of any information you manually enter, and
        for reviewing the transactions and balances Wallit displays against your actual bank
        statements — Wallit reflects what Plaid reports, which can occasionally lag or differ
        from your bank&apos;s own records.</li>
      </ul>

      <h2>The AI assistant</h2>
      <p>
        Wallit&apos;s assistant can look up your real account data and, only after you explicitly
        confirm, make changes on your behalf (like adjusting a budget or creating a savings
        goal). It won&apos;t make those changes without your confirmation. That said, like any AI
        system, its responses can occasionally be wrong — treat its answers as a helpful starting
        point, not a guarantee, and verify anything important against your actual account data.
      </p>

      <h2>Third-party services</h2>
      <p>
        Linking a bank account happens through Plaid and is subject to Plaid&apos;s own terms.
        Signing in with Google is subject to Google&apos;s terms. We&apos;re not responsible for
        the availability or accuracy of these third-party services.
      </p>

      <h2>Acceptable use</h2>
      <p>
        Don&apos;t use Wallit to attempt unauthorized access to any account, interfere with the
        service, or use it for anything illegal.
      </p>

      <h2>Disclaimer &amp; limitation of liability</h2>
      <p>
        Wallit is provided "as is," without warranties of any kind. We do our best to keep your
        data accurate and the service running, but we&apos;re not liable for financial decisions
        made based on information in the app, or for losses resulting from service interruptions,
        inaccuracies, or unauthorized access to your account resulting from your own failure to
        keep your credentials secure.
      </p>

      <h2>Termination</h2>
      <p>
        You can stop using Wallit and request account deletion at any time. We may suspend or
        terminate accounts that violate these terms.
      </p>

      <h2>Changes to these terms</h2>
      <p>
        We may update these terms as Wallit changes. We&apos;ll update the date at the top of
        this page when we do.
      </p>

      <h2>Contact</h2>
      <p>
        Questions about these terms? Reach us at{" "}
        <a href="mailto:thawaniroh000@gmail.com">thawaniroh000@gmail.com</a>.
      </p>
    </LegalLayout>
  );
}
