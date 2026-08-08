import { redirect } from "next/navigation";

// Root route redirects to login — real entry points are /login and /dashboard
export default function Home() {
  redirect("/login");
}
