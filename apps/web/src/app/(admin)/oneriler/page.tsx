import type { Metadata } from "next";
import RecommendationsPage from "@/components/recommendations/RecommendationsPage";

export const metadata: Metadata = {
  title: "feraSet Öneriler",
  description: "Şirketinize ait fiyat önerilerini inceleyin ve karar verin.",
};

export default function OnerilerPage() {
  return <RecommendationsPage />;
}
