import type { Metadata } from "next";
import CompanyProductsPage from "@/components/products/CompanyProductsPage";

export const metadata: Metadata = {
  title: "feraSet Urunler",
  description: "Sirket urunlerini yonetin ve urun bazli analiz baslatin.",
};

export default function ProductsPage() {
  return <CompanyProductsPage />;
}
