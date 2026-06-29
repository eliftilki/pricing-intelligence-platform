import type { Metadata } from "next";
import SalesQuantitiesPage from "@/components/sales/SalesQuantitiesPage";

export const metadata: Metadata = {
  title: "feraSet Satış Miktarları",
  description: "Ürün ve pazaryeri bazında satış miktarlarını kaydedin.",
};

export default function SalesPage() {
  return <SalesQuantitiesPage />;
}
