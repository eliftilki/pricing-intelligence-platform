"use client";

import React, { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
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
  CompetitorListing,
  CompetitorTier,
  PriceRecommendation,
  Product,
  SellerProduct,
  pricingApi,
} from "@/lib/pricing-api";
import { BoltIcon, BoxIconLine, DollarLineIcon, PlusIcon } from "@/icons";

const marketplaces = ["TRENDYOL", "HEPSIBURADA", "AMAZON"];

type Toast = {
  type: "success" | "error" | "info";
  message: string;
};

type ProductInsight = {
  product: Product;
  sellerProducts: SellerProduct[];
  recommendations: PriceRecommendation[];
  listings: CompetitorListing[];
  tiers: CompetitorTier[];
};

const cardClass =
  "rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03]";

function buildQuery(product: Product) {
  return [product.brand, product.name, product.category].filter(Boolean).join(" ");
}

function toMoney(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === "") return "-";
  const numeric = Number(value);
  if (Number.isNaN(numeric)) return String(value);
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
    maximumFractionDigits: 0,
  }).format(numeric);
}

function toPercent(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === "") return "-";
  const numeric = Number(value);
  if (Number.isNaN(numeric)) return String(value);
  return `${new Intl.NumberFormat("tr-TR", {
    maximumFractionDigits: 1,
  }).format(Math.abs(numeric) <= 1 ? numeric * 100 : numeric)}%`;
}

function latestRecommendation(row: ProductInsight) {
  return [...row.recommendations].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  )[0];
}

function latestAnalysisDate(row: ProductInsight) {
  const dates = [
    ...row.recommendations.map((item) => item.created_at),
    ...row.tiers.map((item) => item.analyzed_at),
    ...row.listings.map((item) => item.scraped_at),
  ]
    .filter(Boolean)
    .map((date) => new Date(date || "").getTime())
    .filter((time) => !Number.isNaN(time));

  return dates.length ? Math.max(...dates) : null;
}

function maxBuyboxScore(row: ProductInsight) {
  return Math.max(0, ...row.tiers.map((tier) => Number(tier.buybox_threat_score || 0)));
}

function riskLevel(row: ProductInsight) {
  const recommendationRisk = latestRecommendation(row)?.risk_level;
  if (recommendationRisk) return recommendationRisk;

  const buyboxScore = maxBuyboxScore(row);
  if (buyboxScore >= 70) return "Yuksek";
  if (buyboxScore >= 40) return "Orta";
  return latestAnalysisDate(row) ? "Dusuk" : "-";
}

function statusText(row: ProductInsight, activeProductId: string) {
  if (activeProductId === row.product.id) return "Analiz Calisiyor";
  return latestAnalysisDate(row) ? "Analiz Tamamlandi" : "Analiz Bekliyor";
}

function statusColor(status: string) {
  if (status.includes("Calisiyor")) return "info";
  if (status.includes("Tamamlandi")) return "success";
  return "warning";
}

function reasonCodes(tier: CompetitorTier) {
  if (Array.isArray(tier.reason_codes)) return tier.reason_codes;
  if (typeof tier.reason_codes === "string") {
    try {
      const parsed = JSON.parse(tier.reason_codes) as unknown;
      return Array.isArray(parsed) ? parsed.map(String) : [tier.reason_codes];
    } catch {
      return [tier.reason_codes];
    }
  }
  return [];
}

function humanReason(code: string) {
  const labels: Record<string, string> = {
    RANK_1_BUYBOX_POSITION: "Buybox pozisyonunda veya en gorunur rakiplerden biri.",
    RANK_2_STRONG_VISIBILITY: "Arama sonucunda yuksek gorunurluge sahip.",
    RANK_3_VISIBLE_COMPETITOR: "Ilk siralarda gorunen bir rakip.",
    BUYBOX_PRICE_PRESSURE: "Fiyat baskisi buybox riskini artiriyor.",
    BUYBOX_FAST_SHIPPING_ADVANTAGE: "Hizli kargo avantaji var.",
    BUYBOX_FREE_SHIPPING_ADVANTAGE: "Ucretsiz kargo avantaji var.",
    COMPETITOR_UNDER_CUTTING_US_HIGH_THREAT: "Sizden belirgin sekilde daha dusuk fiyatli.",
    COMPETITOR_PRICE_SLIGHTLY_HIGHER: "Fiyati size yakin oldugu icin takip edilmeli.",
    VERY_AGGRESSIVE_PRICE: "Agresif fiyat politikasi uyguluyor.",
    DESTRUCTIVE_PRICE_DUMPING: "Cok agresif fiyat dususu var.",
    HIGH_IMPACT_COMPETITOR: "Fiyat ve gorunurluk etkisi yuksek.",
    MEDIUM_IMPACT_COMPETITOR: "Orta seviyede etkili rakip.",
    RANK_1_PRICE_LEADER: "Pazar lideri fiyata yakin konumda.",
    CRITICAL_PRICE_DUMPING_BYPASS: "Kritik fiyat baskisi olusturuyor.",
  };

  return labels[code] || code.replaceAll("_", " ").toLocaleLowerCase("tr-TR");
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

  return "Analiz tamamlandi. Sonuclari urun detayindan inceleyebilirsiniz.";
}

export default function CompanyProductsPage() {
  const router = useRouter();
  const [session, setSession] = useState<AuthSession | null>(null);
  const [company, setCompany] = useState<Company | null>(null);
  const [rows, setRows] = useState<ProductInsight[]>([]);
  const [selectedMarketplaces, setSelectedMarketplaces] =
    useState<string[]>(marketplaces);
  const [toast, setToast] = useState<Toast | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activeProductId, setActiveProductId] = useState("");
  const [expandedProductId, setExpandedProductId] = useState("");
  const [advancedProductId, setAdvancedProductId] = useState("");
  const [form, setForm] = useState({
    name: "",
    brand: "",
    category: "",
  });

  const selectedRow = useMemo(
    () => rows.find((row) => row.product.id === expandedProductId),
    [expandedProductId, rows],
  );

  async function loadData(activeSession = session) {
    if (!activeSession) return;
    setIsLoading(true);
    try {
      const [companyData, products, sellerProducts] = await Promise.all([
        pricingApi.getCompany(activeSession.company_id),
        pricingApi.listProducts(),
        pricingApi.listSellerProducts(activeSession.company_id),
      ]);

      const productMap = new Map(products.map((product) => [product.id, product]));
      const grouped = new Map<string, SellerProduct[]>();

      sellerProducts.forEach((sellerProduct) => {
        grouped.set(sellerProduct.product_id, [
          ...(grouped.get(sellerProduct.product_id) || []),
          sellerProduct,
        ]);
      });

      const insights = await Promise.all(
        Array.from(grouped.entries()).map(async ([productId, items]) => {
          const product = productMap.get(productId);
          if (!product) return null;

          const [listings, tiers, recommendationGroups] = await Promise.all([
            pricingApi.listCompetitorListings(productId).catch(() => []),
            pricingApi.listCompetitorTiers(productId).catch(() => []),
            Promise.all(
              items.map((item) =>
                pricingApi.listRecommendations(item.id).catch(() => []),
              ),
            ),
          ]);

          return {
            product,
            sellerProducts: items,
            listings,
            tiers,
            recommendations: recommendationGroups.flat(),
          };
        }),
      );

      setCompany(companyData);
      setRows(
        insights
          .filter((row): row is ProductInsight => row !== null)
          .sort((a, b) => {
            const bDate = latestAnalysisDate(b) || 0;
            const aDate = latestAnalysisDate(a) || 0;
            return bDate - aDate;
          }),
      );
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
        message: "Urun eklendi. Analizi hazir oldugunda satirdaki Analiz Baslat butonuyla calistirabilirsiniz.",
      });
      await loadData(session);
    } catch (error) {
      setToast({ type: "error", message: errorMessage(error) });
    } finally {
      setIsLoading(false);
    }
  }

  async function analyzeProduct(row: ProductInsight) {
    if (!session) return;

    const productMarketplaces = row.sellerProducts.map(
      (sellerProduct) => sellerProduct.marketplace,
    );
    setActiveProductId(row.product.id);
    setToast({
      type: "info",
      message: `${row.product.name} icin analiz calisiyor. Sonuc tamamlandiginda satir otomatik guncellenecek.`,
    });

    try {
      const result = await pricingApi.runAnalysis({
        product_id: row.product.id,
        company_id: session.company_id,
        query: buildQuery(row.product),
        marketplaces: productMarketplaces.length ? productMarketplaces : marketplaces,
      });
      setToast({ type: "success", message: analysisMessage(result) });
      await loadData(session);
      setExpandedProductId(row.product.id);
    } catch (error) {
      setToast({ type: "error", message: errorMessage(error) });
    } finally {
      setActiveProductId("");
    }
  }

  if (!session) {
    return (
      <div className={cardClass}>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Oturum kontrol ediliyor...
        </p>
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
            {company?.name || "Sirketiniz"} icin urun ekleyin, analiz baslatin ve fiyat onerilerini inceleyin.
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
              Bu adim yalnizca urunu listenize ekler; analiz butonuyla rakip verileri toplanir.
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
                placeholder="Orn. Samsung S24 FE"
                value={form.name}
                onChange={(event) =>
                  setForm((current) => ({ ...current, name: event.target.value }))
                }
              />
            </div>
            <div>
              <Label>Marka</Label>
              <Input
                placeholder="Orn. Samsung"
                value={form.brand}
                onChange={(event) =>
                  setForm((current) => ({ ...current, brand: event.target.value }))
                }
              />
            </div>
            <div>
              <Label>Kategori</Label>
              <Input
                placeholder="Orn. Telefon"
                value={form.category}
                onChange={(event) =>
                  setForm((current) => ({ ...current, category: event.target.value }))
                }
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
            <Button
              disabled={isLoading || !form.name || !selectedMarketplaces.length}
              startIcon={<PlusIcon />}
            >
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
              Fiyat kararini urun bazinda buradan yonetin.
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
                {["Urun", "Durum", "Son Analiz", "Onerilen Fiyat", "Buybox Riski", "Aksiyon"].map((heading) => (
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
              {rows.map((row) => {
                const recommendation = latestRecommendation(row);
                const latestAt = latestAnalysisDate(row);
                const status = statusText(row, activeProductId);

                return (
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
                      <Badge color={statusColor(status)} size="sm">
                        {status}
                      </Badge>
                    </TableCell>
                    <TableCell className="py-3 text-theme-sm text-gray-700 dark:text-gray-300">
                      {latestAt
                        ? new Date(latestAt).toLocaleString("tr-TR", {
                            day: "2-digit",
                            month: "short",
                            hour: "2-digit",
                            minute: "2-digit",
                          })
                        : "-"}
                    </TableCell>
                    <TableCell className="py-3 text-theme-sm font-medium text-gray-900 dark:text-white">
                      {toMoney(recommendation?.recommended_price)}
                    </TableCell>
                    <TableCell className="py-3">
                      <RiskBadge row={row} />
                    </TableCell>
                    <TableCell className="py-3">
                      <div className="flex flex-wrap gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() =>
                            setExpandedProductId((current) =>
                              current === row.product.id ? "" : row.product.id,
                            )
                          }
                        >
                          {expandedProductId === row.product.id ? "Detayi Kapat" : "Detay"}
                        </Button>
                        <Button
                          size="sm"
                          disabled={activeProductId === row.product.id}
                          onClick={() => void analyzeProduct(row)}
                          startIcon={<BoltIcon className="size-4" />}
                        >
                          {activeProductId === row.product.id
                            ? "Analiz Calisiyor..."
                            : latestAt
                              ? "Yeniden Analiz Et"
                              : "Analiz Baslat"}
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
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

      {selectedRow && (
        <ProductDetail
          row={selectedRow}
          advancedOpen={advancedProductId === selectedRow.product.id}
          onToggleAdvanced={() =>
            setAdvancedProductId((current) =>
              current === selectedRow.product.id ? "" : selectedRow.product.id,
            )
          }
        />
      )}
    </div>
  );
}

function RiskBadge({ row }: { row: ProductInsight }) {
  const risk = riskLevel(row);
  const normalizedRisk = risk.toLocaleLowerCase("tr-TR");
  const color =
    normalizedRisk.includes("high") || normalizedRisk.includes("yuksek")
      ? "error"
      : normalizedRisk.includes("medium") || normalizedRisk.includes("orta")
        ? "warning"
        : risk === "-"
          ? "light"
          : "success";

  return (
    <Badge color={color} size="sm">
      {risk}
    </Badge>
  );
}

function ProductDetail({
  row,
  advancedOpen,
  onToggleAdvanced,
}: {
  row: ProductInsight;
  advancedOpen: boolean;
  onToggleAdvanced: () => void;
}) {
  const recommendation = latestRecommendation(row);
  const strongestTiers = [...row.tiers]
    .sort((a, b) => Number(b.buybox_threat_score || 0) - Number(a.buybox_threat_score || 0))
    .slice(0, 5);
  const usedCompetitorCount = row.tiers.filter((tier) => tier.tier !== "NOISE").length;
  const ignoredCompetitorCount = Math.max(row.listings.length - usedCompetitorCount, 0);
  const topTier = strongestTiers[0];

  const summaryReasons = [
    topTier?.seller_name
      ? `${topTier.seller_name} en onemli rakip olarak takip ediliyor.`
      : "Rakip verisi geldikce en onemli saticilar burada ozetlenir.",
    maxBuyboxScore(row) >= 70
      ? "Buybox kaybetme riski yuksek seviyede."
      : maxBuyboxScore(row) >= 40
        ? "Buybox riski orta seviyede takip edilmeli."
        : "Buybox riski dusuk seviyede gorunuyor.",
    recommendation?.explanation ||
      recommendation?.action ||
      "Mevcut marj ve rakip fiyatlari birlikte degerlendiriliyor.",
  ];

  return (
    <section className={cardClass}>
      <div className="mb-5 flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            {row.product.name} Analiz Ozeti
          </h2>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Varsayilan gorunum fiyat onerisi, risk ve kisa gerekceyi gosterir.
          </p>
        </div>
        <RiskBadge row={row} />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <MetricCard
          label="Onerilen Fiyat"
          value={toMoney(recommendation?.recommended_price)}
          icon={<DollarLineIcon className="size-5" />}
        />
        <MetricCard
          label="Beklenen Kar Etkisi"
          value={toPercent(recommendation?.profit_uplift)}
          icon={<BoltIcon className="size-5" />}
        />
        <MetricCard
          label="Risk Seviyesi"
          value={riskLevel(row)}
          icon={<BoxIconLine className="size-5" />}
        />
      </div>

      <div className="mt-5 rounded-lg bg-gray-50 p-4 dark:bg-gray-900/60">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
          Gerekce
        </h3>
        <ul className="mt-3 space-y-2 text-sm text-gray-600 dark:text-gray-300">
          {summaryReasons.map((reason) => (
            <li key={reason} className="flex gap-2">
              <span className="mt-2 h-1.5 w-1.5 rounded-full bg-brand-500" />
              <span>{reason}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-6 border-t border-gray-100 pt-5 dark:border-gray-800">
        <h3 className="text-base font-semibold text-gray-900 dark:text-white">
          Detayli Analiz
        </h3>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
          <InfoPill label="Rakip Sayisi" value={row.listings.length} />
          <InfoPill label="Analizde Kullanilan" value={usedCompetitorCount} />
          <InfoPill label="Goz Ardi Edilen" value={ignoredCompetitorCount} />
        </div>

        <div className="mt-4 max-w-full overflow-x-auto">
          <Table>
            <TableHeader className="border-y border-gray-100 dark:border-gray-800">
              <TableRow>
                {["Satici", "Fiyat", "Tehdit", "Neden onemli"].map((heading) => (
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
              {strongestTiers.map((tier) => {
                const listing = row.listings.find(
                  (item) => item.seller_name === tier.seller_name,
                );
                const reasons = reasonCodes(tier).slice(0, 2).map(humanReason);

                return (
                  <TableRow key={tier.id || `${tier.seller_name}-${tier.tier}`}>
                    <TableCell className="py-3 text-theme-sm font-medium text-gray-900 dark:text-white">
                      {tier.seller_name || "-"}
                    </TableCell>
                    <TableCell className="py-3 text-theme-sm text-gray-700 dark:text-gray-300">
                      {toMoney(listing?.price)}
                    </TableCell>
                    <TableCell className="py-3">
                      <ThreatBadge score={Number(tier.buybox_threat_score || 0)} />
                    </TableCell>
                    <TableCell className="py-3 text-theme-sm text-gray-600 dark:text-gray-300">
                      {reasons.length ? reasons.join(" ") : "Fiyat ve gorunurluk nedeniyle takip ediliyor."}
                    </TableCell>
                  </TableRow>
                );
              })}
              {!strongestTiers.length && (
                <TableRow>
                  <TableCell className="py-6 text-center text-sm text-gray-500 dark:text-gray-400">
                    Henuz rakip analizi yok.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      <div className="mt-6">
        <Button variant="outline" size="sm" onClick={onToggleAdvanced}>
          {advancedOpen ? "Uzman Modunu Kapat" : "Uzman Modu"}
        </Button>

        {advancedOpen && (
          <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-2">
            {strongestTiers.map((tier) => (
              <div
                key={`advanced-${tier.id || tier.seller_name}`}
                className="rounded-lg border border-gray-100 p-4 dark:border-gray-800"
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="font-medium text-gray-900 text-theme-sm dark:text-white">
                    {tier.seller_name || "-"}
                  </p>
                  <Badge color="light" size="sm">
                    {tier.tier || "-"}
                  </Badge>
                </div>
                <div className="mt-3 grid grid-cols-3 gap-3 text-theme-xs">
                  <InfoPill label="Strength" value={toPercent(tier.competitor_strength_score)} />
                  <InfoPill label="Threat" value={toPercent(tier.buybox_threat_score)} />
                  <InfoPill label="Aggression" value={toPercent(tier.price_aggression_score)} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function MetricCard({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-gray-100 p-4 dark:border-gray-800">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
          {icon}
        </div>
        <span className="text-sm text-gray-500 dark:text-gray-400">{label}</span>
      </div>
      <p className="mt-3 text-xl font-semibold text-gray-900 dark:text-white">{value}</p>
    </div>
  );
}

function InfoPill({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg bg-gray-50 px-3 py-2 dark:bg-gray-900/60">
      <span className="text-theme-xs text-gray-500 dark:text-gray-400">{label}</span>
      <p className="mt-1 font-medium text-gray-900 text-theme-sm dark:text-white">{value}</p>
    </div>
  );
}

function ThreatBadge({ score }: { score: number }) {
  const label = score >= 70 ? "Yuksek" : score >= 40 ? "Orta" : "Dusuk";
  const color = score >= 70 ? "error" : score >= 40 ? "warning" : "success";

  return (
    <Badge color={color} size="sm">
      {label}
    </Badge>
  );
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Beklenmeyen bir hata olustu.";
}
