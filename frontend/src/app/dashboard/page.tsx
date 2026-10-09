import { redirect } from "next/navigation";

// /dashboard → /overview (the new overview page in the (app) route group)
export default function DashboardRedirect() {
  redirect("/overview");
}
