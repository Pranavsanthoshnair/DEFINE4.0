import type { Metadata } from "next";
import PageHeader from "@/components/ui/PageHeader";
import CampaignWizard from "@/components/ui/interactive/CampaignWizard";

export const metadata: Metadata = { title: "Create Campaign - Veylo" };

export default function NewCampaignPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Create New Campaign"
        subtitle="Set up your event audio invitation workflow with automated Indic voice synthesis."
      />
      <CampaignWizard />
    </div>
  );
}
