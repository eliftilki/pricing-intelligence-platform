"use client";

import React, { FormEvent, useEffect, useMemo, useState } from "react";
import Badge from "@/components/ui/badge/Badge";
import Button from "@/components/ui/button/Button";
import Input from "@/components/form/input/InputField";
import Label from "@/components/form/Label";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { AuthSession, getAuthSession } from "@/lib/auth-session";
import {
  AnalysisResponse,
  Company,
  Product,
  SellerProduct,
  pricingApi,
} from "@/lib/pricing-api";
import { BoltIcon, BoxIconLine, PlusIcon } from "@/icons";
import { useRouter } from "next/navigation";

const marketplaces = ["TRENDYOL", "HEPSIBURADA", "AMAZON"];

type Toast = {
  type: "success" | "error" | "info";
  message: string;
};

type ProductRow = {
  product: Product;
  sellerProducts: SellerProduct[];
};

const cardClass =
  "rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03]";

function buildQuery(product: Product) {
  return [product.brand, product.name, product.category].filter(Boolean).join(" ");
}

function analysisMessage(result: AnalysisResponse) {
  const total = result.total_competitors || 0;
  const marketplacesWithData = Object.entries(result.scrape_counts || {})
    .filter(([, count]) => count > 0)
    .map(([marketplace]) => marketplace);

  if (result.ingestion_status === "FAILED") {
    return "Analiz baslatildi ancak pazaryerlerinden rakip verisi alinamadi. Urun adini kontrol ederek tekrar deneyin.";
  }

  if (marketplacesWithData.length) {
    return `Analiz tamamlandi. ${marketplacesWithData.join(", ")} uzerinden ${total} rakip bulundu.`;
  }

  return "Analiz tamamlandi. Rakip sonuclari dashboard uzerinden incelenebilir.";
}

export default function CompanyProductsPage() {
  const router = useRouter();
  const [session, setSession] = useState<AuthSession | null>(null);
  const [company, setCompany] = useState<Company | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [sellerProducts, setSellerProducts] = useState<SellerProduct[]>([]);
  const [selectedMarketplaces, setSelectedMarketplaces] =
    useState<string[]>(marketplaces);
  const [toast, setToast] = useState<Toast | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activeProductId, setActiveProductId] = useState("");
  const [form, setForm] = useState({
    name: "",
    brand: "",
    category: "",
  });

  const rows = useMemo<ProductRow[]>(() => {
    const productMap = new Map(products.map((product) => [product.id, product]));
    const grouped = new Map<string, SellerProduct[]>();

    sellerProducts.forEach((sellerProduct) => {
      const existing = grouped.get(sellerProduct.product_id) || [];
      grouped.set(sellerProduct.product_id, [...existing, sellerProduct]);
    });

    return Array.from(grouped.entries())
      .map(([productId, items]) => {
        const product = productMap.get(productId);
        return product ? { product, sellerProducts: items } : null;
      })
      .filter((row): row is ProductRow => row !== null);
  }, [products, sellerProducts]);

  async function loadData(activeSession = session) {
    if (!activeSession) return;
    setIsLoading(true);
    try {
      const [companyData, productData, sellerProductData] = await Promise.all([
        pricingApi.getCompany(activeSession.company_id),
        pricingApi.listProducts(),
        pricingApi.listSellerProducts(activeSession.company_id),
      ]);
      setCompany(companyData);
      setProducts(productData);
      setSellerProducts(sellerProductData);
    } catch (error) {
      setToast({ type: "error", message: errorMessage(error) });
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    const activeSession = getAuthSession();
    if (!activeSession) {
      router.replace("/signin");
      return;
    }

    setSession(activeSession);
    void loadData(activeSession);
  }, []);

  function toggleMarketplace(marketplace: string) {
    setSelectedMarketplaces((current) =>
      current.includes(marketplace)
        ? current.filter((item) => item !== marketplace)
        : [...current, marketplace],
    );
  }

  async function createCompanyProduct(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session) return;

    if (!selectedMarketplaces.length) {
      setToast({ type: "error", message: "En az bir pazaryeri secin." });
      return;
    }

    setIsLoading(true);
    try {
      const product = await pricingApi.createProduct({
        name: form.name,
        brand: form.brand || undefined,
        category: form.category || undefined,
      });

      await Promise.all(
        selectedMarketplaces.map((marketplace) =>
          pricingApi.createSellerProduct({
            company_id: session.company_id,
            product_id: product.id,
            marketplace,
            stock_quantity: 0,
          }),
        ),
      );

      setForm({ name: "", brand: "", category: "" });
      setToast({
        type: "success",
        message: "Urun sirket listenize eklendi. Analiz etmek istediginizde satirdaki Analiz Et butonunu kullanin.",
      });
      await loadData(session);
    } catch (error) {
      setToast({ type: "error", message: errorMessage(error) });
    } finally {
      setIsLoading(false);
    }
  }

  async function analyzeProduct(row: ProductRow) {
    if (!session) return;

    const productMarketplaces = row.sellerProducts.map((sellerProduct) => sellerProduct.marketplace);
    setActiveProductId(row.product.id);
    setToast({
      type: "info",
      message: `${row.product.name} icin pazaryeri verileri toplanip rakip analizi baslatiliyor.`,
    });

    try {
      const result = await pricingApi.runProductAnalysis({
        product_id: row.product.id,
        company_id: session.company_id,
        query: buildQuery(row.product),
        marketplaces: productMarketplaces.length ? productMarketplaces : marketplaces,
      });
      setToast({ type: "success", message: analysisMessage(result) });
      await loadData(session);
    } catch (error) {
      setToast({ type: "error", message: errorMessage(error) });
    } finally {
      setActiveProductId("");
    }
  }

  if (!session) {
    return (
      <div className={cardClass}>
        <p className="text-sm text-gray-500 dark:text-gray-400">Oturum kontrol ediliyor...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
            Urunler
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {company?.name || "Sirketiniz"} icin takip edilecek urunleri yonetin.
          </p>
        </div>
        <Button variant="outline" onClick={() => void loadData()} disabled={isLoading}>
          Yenile
        </Button>
      </div>

      {toast && (
        <div
          className={`rounded-lg border px-4 py-3 text-sm ${
            toast.type === "error"
              ? "border-error-200 bg-error-50 text-error-700 dark:border-error-500/30 dark:bg-error-500/10 dark:text-error-300"
              : toast.type === "success"
                ? "border-success-200 bg-success-50 text-success-700 dark:border-success-500/30 dark:bg-success-500/10 dark:text-success-300"
                : "border-brand-200 bg-brand-50 text-brand-700 dark:border-brand-500/30 dark:bg-brand-500/10 dark:text-brand-300"
          }`}
        >
          {toast.message}
        </div>
      )}

      <section className={cardClass}>
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-brand-50 text-brand-500 dark:bg-brand-500/10">
            <PlusIcon className="size-5" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Sirket urunu ekle
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Bu adim yalnizca urunu sirket listenize ekler; scraping ve agentlar Analiz Et ile calisir.
            </p>
          </div>
        </div>

        <form
          className="grid grid-cols-1 gap-6 xl:grid-cols-[1fr_0.9fr_auto]"
          onSubmit={(event) => void createCompanyProduct(event)}
        >
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3 xl:col-span-1">
            <div>
              <Label>Urun adi</Label>
              <Input
                placeholder="Orn. Logitech G435 Lightspeed"
                value={form.name}
                onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
              />
            </div>
            <div>
              <Label>Marka</Label>
              <Input
                placeholder="Orn. Logitech"
                value={form.brand}
                onChange={(event) => setForm((current) => ({ ...current, brand: event.target.value }))}
              />
            </div>
            <div>
              <Label>Kategori</Label>
              <Input
                placeholder="Orn. Kulaklik"
                value={form.category}
                onChange={(event) => setForm((current) => ({ ...current, category: event.target.value }))}
              />
            </div>
          </div>

          <div>
            <Label>Pazaryerleri</Label>
            <div className="flex flex-wrap gap-2">
              {marketplaces.map((marketplace) => (
                <button
                  key={marketplace}
                  type="button"
                  onClick={() => toggleMarketplace(marketplace)}
                  className={`rounded-lg border px-3 py-2 text-sm font-medium ${
                    selectedMarketplaces.includes(marketplace)
                      ? "border-brand-500 bg-brand-50 text-brand-700 dark:bg-brand-500/10 dark:text-brand-300"
                      : "border-gray-300 text-gray-600 dark:border-gray-700 dark:text-gray-400"
                  }`}
                >
                  {marketplace}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-end">
            <Button disabled={isLoading || !form.name || !selectedMarketplaces.length} startIcon={<PlusIcon />}>
              Urun Ekle
            </Button>
          </div>
        </form>
      </section>

      <section className={cardClass}>
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Sirket urunleri
            </h2>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Her urun icin analiz ayri calisir.
            </p>
          </div>
          <Badge color="light" size="sm">
            {rows.length} urun
          </Badge>
        </div>

        <div className="max-w-full overflow-x-auto">
          <Table>
            <TableHeader className="border-y border-gray-100 dark:border-gray-800">
              <TableRow>
                {["Urun", "Pazaryerleri", "Durum", "Aksiyon"].map((heading) => (
                  <TableCell
                    key={heading}
                    isHeader
                    className="py-3 text-start text-theme-xs font-medium text-gray-500 dark:text-gray-400"
                  >
                    {heading}
                  </TableCell>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody className="divide-y divide-gray-100 dark:divide-gray-800">
              {rows.map((row) => (
                <TableRow key={row.product.id}>
                  <TableCell className="py-3">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-100 dark:bg-gray-800">
                        <BoxIconLine className="size-5 text-gray-600 dark:text-gray-300" />
                      </div>
                      <div>
                        <p className="font-medium text-gray-900 text-theme-sm dark:text-white">
                          {row.product.name}
                        </p>
                        <p className="text-theme-xs text-gray-500 dark:text-gray-400">
                          {[row.product.brand, row.product.category].filter(Boolean).join(" / ") || "-"}
                        </p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="py-3">
                    <div className="flex flex-wrap gap-2">
                      {row.sellerProducts.map((sellerProduct) => (
                        <Badge key={sellerProduct.id} color="light" size="sm">
                          {sellerProduct.marketplace}
                        </Badge>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell className="py-3 text-theme-sm text-gray-700 dark:text-gray-300">
                    Analize hazir
                  </TableCell>
                  <TableCell className="py-3">
                    <Button
                      size="sm"
                      disabled={activeProductId === row.product.id}
                      onClick={() => void analyzeProduct(row)}
                      startIcon={<BoltIcon className="size-4" />}
                    >
                      {activeProductId === row.product.id ? "Analiz ediliyor..." : "Analiz Et"}
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {!rows.length && (
                <TableRow>
                  <TableCell className="py-6 text-center text-sm text-gray-500 dark:text-gray-400">
                    Henuz sirketinize ait urun yok.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </section>
    </div>
  );
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Beklenmeyen bir hata olustu.";
}
