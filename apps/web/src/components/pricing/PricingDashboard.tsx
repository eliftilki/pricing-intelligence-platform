"use client";

import React, { useEffect, useMemo, useState } from "react";
import Badge from "@/components/ui/badge/Badge";
import Button from "@/components/ui/button/Button";
import Label from "@/components/form/Label";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Company,
  CompetitorListing,
  CompetitorTier,
  PriceRecommendation,
  Product,
  SellerProduct,
  pricingApi,
} from "@/lib/pricing-api";
import { AuthSession, getAuthSession } from "@/lib/auth-session";
import {
  BoltIcon,
  BoxIconLine,
  DollarLineIcon,
  GroupIcon,
} from "@/icons";
import { useRouter } from "next/navigation";

type LoadState = "idle" | "loading" | "success" | "error";

type Toast = {
  type: "success" | "error" | "info";
  message: string;
};

const cardClass =
  "rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03]";

const fieldClass =
  "rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm text-gray-800 shadow-theme-xs focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90";

function toMoney(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === "") return "-";
  const numeric = Number(value);
  if (Number.isNaN(numeric)) return String(value);
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
    maximumFractionDigits: 2,
  }).format(numeric);
}

function toPercent(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === "") return "-";
  const numeric = Number(value);
  if (Number.isNaN(numeric)) return String(value);
  return `${Math.round(numeric * 100)}%`;
}

function toScorePercent(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === "") return "-";
  const numeric = Number(value);
  if (Number.isNaN(numeric)) return String(value);
  return `${new Intl.NumberFormat("tr-TR", {
    maximumFractionDigits: 2,
  }).format(numeric)}%`;
}

export default function PricingDashboard() {
  const router = useRouter();
  const [session, setSession] = useState<AuthSession | null>(null);
  const [company, setCompany] = useState<Company | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [sellerProducts, setSellerProducts] = useState<SellerProduct[]>([]);
  const [recommendations, setRecommendations] = useState<PriceRecommendation[]>([]);
  const [listings, setListings] = useState<CompetitorListing[]>([]);
  const [tiers, setTiers] = useState<CompetitorTier[]>([]);

  const [selectedProductId, setSelectedProductId] = useState("");
  const [selectedSellerProductId, setSelectedSellerProductId] = useState("");
  const [decisionNote, setDecisionNote] = useState("");
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [actionState, setActionState] = useState<LoadState>("idle");
  const [toast, setToast] = useState<Toast | null>(null);

  const companyProductIds = useMemo(
    () => new Set(sellerProducts.map((sellerProduct) => sellerProduct.product_id)),
    [sellerProducts],
  );

  const visibleProducts = useMemo(
    () =>
      products.filter((product) =>
        companyProductIds.size ? companyProductIds.has(product.id) : false,
      ),
    [companyProductIds, products],
  );

  const selectedProduct = useMemo(
    () => products.find((product) => product.id === selectedProductId),
    [products, selectedProductId],
  );

  const selectedSellerProduct = useMemo(
    () =>
      sellerProducts.find(
        (sellerProduct) => sellerProduct.id === selectedSellerProductId,
      ),
    [sellerProducts, selectedSellerProductId],
  );

  const stats = useMemo(
    () => [
      {
        label: "Takipteki Urun",
        value: visibleProducts.length,
        icon: <BoxIconLine className="text-gray-800 dark:text-white/90" />,
      },
      {
        label: "Satici Kaydi",
        value: sellerProducts.length,
        icon: <GroupIcon className="text-gray-800 size-6 dark:text-white/90" />,
      },
      {
        label: "Rakip Ilan",
        value: listings.length,
        icon: <BoltIcon className="text-gray-800 size-6 dark:text-white/90" />,
      },
      {
        label: "Acik Oneri",
        value: recommendations.filter((item) => item.status === "PENDING").length,
        icon: <DollarLineIcon className="text-gray-800 size-6 dark:text-white/90" />,
      },
    ],
    [listings.length, visibleProducts.length, recommendations, sellerProducts.length],
  );

  async function refreshBaseData(activeSession = session) {
    if (!activeSession) return;

    setLoadState("loading");
    try {
      const [companyData, productData, sellerProductData] = await Promise.all([
        pricingApi.getCompany(activeSession.company_id),
        pricingApi.listProducts(),
        pricingApi.listSellerProducts(activeSession.company_id),
      ]);
      setCompany(companyData);
      setProducts(productData);
      setSellerProducts(sellerProductData);
      setSelectedSellerProductId((current) => current || sellerProductData[0]?.id || "");
      setSelectedProductId((current) => current || sellerProductData[0]?.product_id || "");
      setToast({ type: "success", message: "Sirket verileriniz guncellendi." });
      setLoadState("success");
    } catch (error) {
      setToast({ type: "error", message: errorMessage(error) });
      setLoadState("error");
    }
  }

  useEffect(() => {
    const activeSession = getAuthSession();
    if (!activeSession) {
      router.replace("/signin");
      return;
    }

    setSession(activeSession);
    void Promise.resolve().then(() => refreshBaseData(activeSession));
  }, []);

  useEffect(() => {
    if (!selectedProductId) {
      void Promise.resolve().then(() => {
        setListings([]);
        setTiers([]);
      });
      return;
    }

    Promise.all([
      pricingApi.listCompetitorListings(selectedProductId),
      pricingApi.listCompetitorTiers(selectedProductId),
    ])
      .then(([listingData, tierData]) => {
        setListings(listingData);
        setTiers(tierData);
      })
      .catch((error) =>
        setToast({ type: "error", message: `Rakip verileri alinamadi: ${errorMessage(error)}` }),
      );
  }, [selectedProductId]);

  useEffect(() => {
    if (!selectedSellerProductId) {
      void Promise.resolve().then(() => {
        setRecommendations([]);
      });
      return;
    }

    pricingApi
      .listRecommendations(selectedSellerProductId)
      .then(setRecommendations)
      .catch((error) =>
        setToast({ type: "error", message: `Oneriler alinamadi: ${errorMessage(error)}` }),
      );
  }, [selectedSellerProductId]);

  async function decideRecommendation(
    recommendation: PriceRecommendation,
    action: "approve" | "reject" | "apply",
  ) {
    setActionState("loading");
    try {
      await pricingApi.decideRecommendation(
        recommendation.id,
        action,
        decisionNote || undefined,
        session?.access_token,
      );
      setToast({ type: "success", message: `Oneri ${action} islemi tamamlandi.` });
      setActionState("success");
      if (selectedSellerProductId) {
        setRecommendations(await pricingApi.listRecommendations(selectedSellerProductId));
      }
    } catch (error) {
      setToast({ type: "error", message: errorMessage(error) });
      setActionState("error");
    }
  }

  async function applyRecommendedPrice(recommendation: PriceRecommendation) {
    if (!session?.access_token) {
      setToast({
        type: "error",
        message: "Oturum bulunamadi. Lutfen tekrar giris yapin.",
      });
      return;
    }

    setActionState("loading");
    try {
      await pricingApi.updatePrice(
        recommendation.seller_product_id,
        {
          new_price: Number(recommendation.recommended_price),
          change_source: "RECOMMENDATION",
          recommendation_id: recommendation.id,
        },
        session.access_token,
      );
      await decideRecommendation(recommendation, "apply");
      setToast({ type: "success", message: "Onerilen fiyat satici urunune uygulandi." });
    } catch (error) {
      setToast({ type: "error", message: errorMessage(error) });
      setActionState("error");
    }
  }

  const isBusy = actionState === "loading" || loadState === "loading";

  if (!session) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-6 text-sm text-gray-600 dark:border-gray-800 dark:bg-white/[0.03] dark:text-gray-300">
        Oturum kontrol ediliyor...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
            {company?.name || "feraSet"}
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Sirketinize ait urun, rakip ve fiyat onerileri
          </p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <Button variant="outline" onClick={() => void refreshBaseData()} disabled={isBusy}>
            Yenile
          </Button>
        </div>
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

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map((stat) => (
          <div key={stat.label} className={cardClass}>
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-gray-100 dark:bg-gray-800">
              {stat.icon}
            </div>
            <div className="mt-5">
              <span className="text-sm text-gray-500 dark:text-gray-400">{stat.label}</span>
              <h2 className="mt-2 text-2xl font-semibold text-gray-900 dark:text-white">
                {stat.value}
              </h2>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <section className={`${cardClass} xl:col-span-2`}>
          <div className="mb-5 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Sirket Paneli
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Bu ekranda yalnizca kendi sirketinizin verileri gosterilir.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div>
              <Label>Sirket</Label>
              <div className={`${fieldClass} flex h-11 w-full items-center`}>
                {company?.name || "Sirket bilgisi yukleniyor"}
              </div>
            </div>
            <div>
              <Label>Urun</Label>
              <select
                className={`${fieldClass} h-11 w-full`}
                value={selectedProductId}
                onChange={(event) => setSelectedProductId(event.target.value)}
              >
                <option value="">Urun secin</option>
                {visibleProducts.map((product) => (
                  <option key={product.id} value={product.id}>
                    {product.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label>Satici Urunu</Label>
              <select
                className={`${fieldClass} h-11 w-full`}
                value={selectedSellerProductId}
                onChange={(event) => {
                  const sellerProduct = sellerProducts.find(
                    (item) => item.id === event.target.value,
                  );
                  setSelectedSellerProductId(event.target.value);
                  setSelectedProductId(sellerProduct?.product_id || "");
                }}
              >
                <option value="">Satici urunu secin</option>
                {sellerProducts.map((sellerProduct) => (
                  <option key={sellerProduct.id} value={sellerProduct.id}>
                    {sellerProduct.marketplace} - {toMoney(sellerProduct.our_price)}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="mt-5 grid grid-cols-1 gap-3 rounded-lg bg-gray-50 p-4 text-sm dark:bg-gray-900/60 md:grid-cols-3">
            <div>
              <span className="text-gray-500 dark:text-gray-400">Secili urun</span>
              <p className="mt-1 font-medium text-gray-900 dark:text-white">
                {selectedProduct?.brand ? `${selectedProduct.brand} ` : ""}
                {selectedProduct?.name || "-"}
              </p>
            </div>
            <div>
              <span className="text-gray-500 dark:text-gray-400">Mevcut fiyat</span>
              <p className="mt-1 font-medium text-gray-900 dark:text-white">
                {toMoney(selectedSellerProduct?.our_price)}
              </p>
            </div>
            <div>
              <span className="text-gray-500 dark:text-gray-400">Min. marj</span>
              <p className="mt-1 font-medium text-gray-900 dark:text-white">
                {toPercent(selectedSellerProduct?.min_margin_rate)}
              </p>
            </div>
          </div>
        </section>

        <section className={cardClass}>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Karar Notu
          </h2>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Onay, red ve uygulama islemlerinde bu not kaydedilir.
          </p>
          <div className="mt-4 space-y-4">
            <div>
              <Label>Karar notu</Label>
              <textarea
                className={`${fieldClass} min-h-24 w-full`}
                value={decisionNote}
                onChange={(event) => setDecisionNote(event.target.value)}
                placeholder="Opsiyonel not"
              />
            </div>
          </div>
        </section>
      </div>

      <section className={cardClass}>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Fiyat Onerileri
          </h2>
          <Badge color={recommendations.length ? "info" : "light"} size="sm">
            {recommendations.length} kayit
          </Badge>
        </div>
        <div className="max-w-full overflow-x-auto">
          <Table>
            <TableHeader className="border-y border-gray-100 dark:border-gray-800">
              <TableRow>
                {["Durum", "Mevcut", "Oneri", "Aksiyon", "Risk", "Islemler"].map((heading) => (
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
              {recommendations.map((recommendation) => (
                <TableRow key={recommendation.id}>
                  <TableCell className="py-3 text-theme-sm text-gray-700 dark:text-gray-300">
                    {recommendation.status}
                  </TableCell>
                  <TableCell className="py-3 text-theme-sm text-gray-700 dark:text-gray-300">
                    {toMoney(recommendation.current_price)}
                  </TableCell>
                  <TableCell className="py-3 text-theme-sm font-medium text-gray-900 dark:text-white">
                    {toMoney(recommendation.recommended_price)}
                  </TableCell>
                  <TableCell className="py-3 text-theme-sm text-gray-700 dark:text-gray-300">
                    {recommendation.action}
                  </TableCell>
                  <TableCell className="py-3 text-theme-sm text-gray-700 dark:text-gray-300">
                    {recommendation.risk_level || "-"}
                  </TableCell>
                  <TableCell className="py-3">
                    <div className="flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={isBusy}
                        onClick={() => void decideRecommendation(recommendation, "approve")}
                      >
                        Onayla
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={isBusy}
                        onClick={() => void decideRecommendation(recommendation, "reject")}
                      >
                        Reddet
                      </Button>
                      <Button
                        size="sm"
                        disabled={isBusy}
                        onClick={() => void applyRecommendedPrice(recommendation)}
                      >
                        Uygula
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {!recommendations.length && (
                <TableRow>
                  <TableCell
                    className="py-6 text-center text-sm text-gray-500 dark:text-gray-400"
                  >
                    Secili satici urunu icin henuz fiyat onerisi yok.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <DataTable
          title="Rakip Ilanlari"
          badge={`${listings.length} ilan`}
          headers={["Pazaryeri", "Satici", "Fiyat", "Stok", "Tarih"]}
          rows={listings.slice(0, 8).map((listing, index) => [
            listing.marketplace || "-",
            listing.seller_name || `Rakip ${index + 1}`,
            toMoney(listing.price),
            listing.stock_status || "-",
            listing.scraped_at ? new Date(listing.scraped_at).toLocaleString("tr-TR") : "-",
          ])}
        />
        <DataTable
          title="Rakip Tier Analizi"
          badge={`${tiers.length} skor`}
          headers={["Satici", "Tier", "Guc", "Agresiflik", "Buybox"]}
          rows={tiers.slice(0, 8).map((tier) => [
            tier.seller_name || "-",
            tier.tier || "-",
            toScorePercent(tier.competitor_strength_score),
            toScorePercent(tier.price_aggression_score),
            toScorePercent(tier.buybox_threat_score),
          ])}
        />
      </div>
    </div>
  );
}

function DataTable({
  title,
  badge,
  headers,
  rows,
}: {
  title: string;
  badge: string;
  headers: string[];
  rows: string[][];
}) {
  return (
    <section className={cardClass}>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h2>
        <Badge color="light" size="sm">
          {badge}
        </Badge>
      </div>
      <div className="max-w-full overflow-x-auto">
        <Table>
          <TableHeader className="border-y border-gray-100 dark:border-gray-800">
            <TableRow>
              {headers.map((heading) => (
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
            {rows.map((row, rowIndex) => (
              <TableRow key={`${title}-${rowIndex}`}>
                {row.map((cell, cellIndex) => (
                  <TableCell
                    key={`${title}-${rowIndex}-${cellIndex}`}
                    className="py-3 text-theme-sm text-gray-700 dark:text-gray-300"
                  >
                    {cell}
                  </TableCell>
                ))}
              </TableRow>
            ))}
            {!rows.length && (
              <TableRow>
                <TableCell className="py-6 text-center text-sm text-gray-500 dark:text-gray-400">
                  Henuz veri yok.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </section>
  );
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Beklenmeyen bir hata olustu.";
}
