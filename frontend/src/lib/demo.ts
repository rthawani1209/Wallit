// Demo accounts get addresses on this domain (see backend services/demo.py).
const DEMO_EMAIL_DOMAIN = "@demo.wallit.app";

export function isDemoEmail(email: string | null | undefined): boolean {
  return !!email && email.endsWith(DEMO_EMAIL_DOMAIN);
}
