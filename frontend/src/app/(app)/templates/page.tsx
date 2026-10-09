import type { Metadata } from "next";
import PageHeader from "@/components/ui/PageHeader";
import TemplateEditor from "@/components/ui/interactive/TemplateEditor";

export const metadata: Metadata = { title: "Voice Templates - Veylo" };

export default function TemplatesPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Voice Templates"
        subtitle="Configure dynamic scripts with tokenized slots for invitation, reminder, and follow-up audio."
      />
      <TemplateEditor />
    </div>
  );
}
