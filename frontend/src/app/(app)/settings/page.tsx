import type { Metadata } from "next";
import PageHeader from "@/components/ui/PageHeader";
import SettingsForm from "@/components/ui/interactive/SettingsForm";

export const metadata: Metadata = { title: "Settings - Veylo" };

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Telephony & Engine Settings"
        subtitle="Configure Exotel telephony credentials, AI voice provider tokens, and compliance throttles."
      />
      <SettingsForm />
    </div>
  );
}
