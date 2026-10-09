import type { Metadata } from "next";
import PageHeader from "@/components/ui/PageHeader";
import ContactsPanel from "@/components/ui/interactive/ContactsPanel";

export const metadata: Metadata = { title: "Contacts - Veylo" };

export default function ContactsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Audience & Contacts"
        subtitle="Validate phone numbers, inspect language preferences, and manage recipient datasets."
      />
      <ContactsPanel />
    </div>
  );
}
