import type { Metadata } from "next";
import FeraSetLanding from "@/components/landing/FeraSetLanding";

export const metadata: Metadata = {
  title: "feraSet",
  description: "E-ticaret saticilari icin fiyat zeka platformu.",
};

export default function HomePage() {
  return <FeraSetLanding />;
}
