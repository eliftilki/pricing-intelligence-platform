import type { Metadata } from "next";
import React from "react";
import PricingDashboard from "@/components/pricing/PricingDashboard";

export const metadata: Metadata = {
  title: "feraSet Dashboard",
  description: "feraSet pricing intelligence dashboard",
};

export default function DashboardPage() {
  return <PricingDashboard />;
}
