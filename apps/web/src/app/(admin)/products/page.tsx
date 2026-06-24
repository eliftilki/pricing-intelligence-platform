import type { Metadata } from "next";
import CompanyProductsPage from "@/components/products/CompanyProductsPage";

export const metadata: Metadata = {
  title: "feraSet Ürünler",
  description: "Şirket ürünlerini yönetin ve ürün bazlı analiz başlatın.",
};

export default function ProductsPage() {
  return <CompanyProductsPage />;
}
