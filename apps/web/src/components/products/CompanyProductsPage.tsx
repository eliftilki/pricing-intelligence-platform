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
import {
  BoltIcon,
  BoxIconLine,
  DollarLineIcon,
  EyeIcon,
  PencilIcon,
  PlusIcon,
  TrashBinIcon,
} from "@/icons";

const marketplaces = ["TRENDYOL", "HEPSIBURADA", "AMAZON"];
const categoryOptions = [
  "Telefon",
  "Bilgisayar",
  "Tablet",
  "Klavye",
  "Kulaklık",
  "Mouse",
  "Monitor",
  "Akıllı Saat",
  "Oyun Konsolu",
  "Hoparlor",
  "Şarj Aleti",
  "Kablo",
  "Aksesuar",
  "Ev Elektroniği",
];
const brandOptions = ["Apple", "Samsung", "Xiaomi", "Huawei", "Lenovo", "Asus", "HP", "Dell"];
const connectionTypeOptions = ["Kablosuz", "Kablolu"];
const storageOptions = ["64 GB", "128 GB", "256 GB", "512 GB", "1 TB"];
const ramOptions = ["4 GB", "6 GB", "8 GB", "12 GB", "16 GB"];
const simTypeOptions = ["Tek SIM", "Cift SIM", "eSIM", "Nano SIM", "Nano SIM + eSIM"];
const switchTypeOptions = ["Mekanik", "Membran", "Optik", "Sessiz", "Scissor"];
const keyboardLayoutOptions = ["TR Q", "TR F", "US Q", "UK Q"];
const colorOptions = ["Siyah", "Beyaz", "Gri", "Gümüş", "Mavi", "Yeşil", "Kırmızı", "Altın"];

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

type ProductFormState = {
  brand: string;
  category: string;
  color: string;
  model: string;
  connectionType: string;
  storageCapacity: string;
  ramCapacity: string;
  simType: string;
  switchType: string;
  keyboardLayout: string;
  ourPrice: string;
  costPrice: string;
  stockQuantity: string;
};

const cardClass =
  "rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03]";
const selectClass =
  "h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm text-gray-800 shadow-theme-xs focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:focus:border-brand-800";

function primarySellerProduct(row: ProductInsight) {
  return row.sellerProducts[0];
}

function buildProductNameFromParts(brand?: string | null, model?: string | null) {
  return [brand, model].filter(Boolean).join(" ").trim();
}

function productDisplayName(row: ProductInsight) {
  return (
    buildProductNameFromParts(row.product.brand, row.product.model) ||
    primarySellerProduct(row)?.display_name ||
    row.product.name ||
    "-"
  );
}

function buildQuery(row: ProductInsight) {
  return [
    row.product.brand,
    row.product.model,
    row.product.color,
    row.product.category,
    row.product.connection_type,
    row.product.storage_capacity,
    row.product.ram_capacity,
    row.product.sim_type,
    row.product.switch_type,
    row.product.keyboard_layout,
  ]
    .filter(Boolean)
    .join(" ");
}

function isHeadphoneCategory(category: string | null | undefined) {
  return Boolean(category?.toLocaleLowerCase("tr-TR").includes("kulak"));
}

function isPhoneCategory(category: string | null | undefined) {
  return Boolean(category?.toLocaleLowerCase("tr-TR").includes("telefon"));
}

function isMouseCategory(category: string | null | undefined) {
  return Boolean(category?.toLocaleLowerCase("tr-TR").includes("mouse"));
}

function isKeyboardCategory(category: string | null | undefined) {
  return Boolean(category?.toLocaleLowerCase("tr-TR").includes("klavye"));
}

function hasConnectionTypeFeature(category: string | null | undefined) {
  return (
    isHeadphoneCategory(category) ||
    isMouseCategory(category) ||
    isKeyboardCategory(category)
  );
}

function hasProductFeatures(category: string | null | undefined) {
  return hasConnectionTypeFeature(category) || isPhoneCategory(category);
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

function optionalNumber(value: string) {
  if (!value.trim()) return undefined;
  const numeric = Number(value);
  return Number.isNaN(numeric) ? undefined : numeric;
}

function toInputValue(value: string | number | null | undefined) {
  return value === null || value === undefined ? "" : String(value);
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
  if (buyboxScore >= 70) return "Yüksek";
  if (buyboxScore >= 40) return "Orta";
  return latestAnalysisDate(row) ? "Düşük" : "-";
}

function statusText(row: ProductInsight, activeProductId: string) {
  if (activeProductId === row.product.id) return "Analiz Çalışıyor";
  return latestAnalysisDate(row) ? "Analiz Tamamlandı" : "Analiz Bekliyor";
}

function statusColor(status: string) {
  if (status.includes("Çalışıyor")) return "info";
  if (status.includes("Tamamlandı")) return "success";
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
    RANK_1_BUYBOX_POSITION: "Buybox pozisyonunda veya en görünür rakiplerden biri.",
    RANK_2_STRONG_VISIBILITY: "Arama sonucunda yüksek görünürlüğe sahip.",
    RANK_3_VISIBLE_COMPETITOR: "İlk sıralarda görünen bir rakip.",
    BUYBOX_PRICE_PRESSURE: "Fiyat baskısı buybox riskini artırıyor.",
    BUYBOX_FAST_SHIPPING_ADVANTAGE: "Hızlı kargo avantajı var.",
    BUYBOX_FREE_SHIPPING_ADVANTAGE: "Ücretsiz kargo avantajı var.",
    COMPETITOR_UNDER_CUTTING_US_HIGH_THREAT: "Sizden belirgin şekilde daha düşük fiyatlı.",
    COMPETITOR_PRICE_SLIGHTLY_HIGHER: "Fiyatı size yakın olduğu için takip edilmeli.",
    VERY_AGGRESSIVE_PRICE: "Agresif fiyat politikası uyguluyor.",
    DESTRUCTIVE_PRICE_DUMPING: "Çok agresif fiyat düşüşü var.",
    HIGH_IMPACT_COMPETITOR: "Fiyat ve görünürlük etkisi yüksek.",
    MEDIUM_IMPACT_COMPETITOR: "Orta seviyede etkili rakip.",
    RANK_1_PRICE_LEADER: "Pazar lideri fiyata yakın konumda.",
    CRITICAL_PRICE_DUMPING_BYPASS: "Kritik fiyat baskısı oluşturuyor.",
  };

  return labels[code] || code.replaceAll("_", " ").toLocaleLowerCase("tr-TR");
}

function analysisMessage(result: AnalysisResponse) {
  const total = result.total_competitors || 0;
  const marketplacesWithData = Object.entries(result.scrape_counts || {})
    .filter(([, count]) => count > 0)
    .map(([marketplace]) => marketplace);
  const ingestionMessage = result.ingestion_message?.toLocaleLowerCase("tr-TR") || "";
  const usedOnlyCachedData =
    ingestionMessage.includes("yeni scraping calistirilmadi") ||
    ingestionMessage.includes("yeniden scraping yapılmadı") ||
    ingestionMessage.includes("basarili scrape kullanildi");
  const cachedCountMatch = ingestionMessage.match(/used cached data for (\d+)/);
  const cachedCount = cachedCountMatch ? Number(cachedCountMatch[1]) : 0;

  if (result.ingestion_status === "FAILED") {
    return "Analiz başlatıldı ancak pazaryerlerinden rakip verisi alınamadı. Ürün adını ve pazaryeri seçimini kontrol edip tekrar deneyin.";
  }

  if (usedOnlyCachedData && marketplacesWithData.length) {
    return `Son 12 saat i\u00e7inde toplanan g\u00fcncel veriler kullan\u0131ld\u0131; yeniden scraping yap\u0131lmad\u0131. ${marketplacesWithData.join(", ")} \u00fczerinden ${total} rakip analiz edildi.`;
  }

  if (marketplacesWithData.length) {
    if (cachedCount > 0) {
      return `Analiz tamamland\u0131. ${marketplacesWithData.join(", ")} \u00fczerinden ${total} rakip bulundu; baz\u0131 pazaryerlerinde son 12 saat i\u00e7indeki veriler kullan\u0131ld\u0131.`;
    }

    return `Analiz tamamlandı. ${marketplacesWithData.join(", ")} üzerinden ${total} rakip bulundu.`;
  }

  return "Analiz tamamlandı. Sonuçları ürün detayından inceleyebilirsiniz.";
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
  const [editingProductId, setEditingProductId] = useState("");
  const [editForm, setEditForm] = useState<ProductFormState | null>(null);
  const [form, setForm] = useState<ProductFormState>({
    brand: "",
    category: "",
    color: "",
    model: "",
    connectionType: "",
    storageCapacity: "",
    ramCapacity: "",
    simType: "",
    switchType: "",
    keyboardLayout: "",
    ourPrice: "",
    costPrice: "",
    stockQuantity: "",
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

  function productFormPayload(currentForm: ProductFormState) {
    const productName = buildProductNameFromParts(currentForm.brand, currentForm.model);
    const isPhone = isPhoneCategory(currentForm.category);
    const isKeyboard = isKeyboardCategory(currentForm.category);
    const hasConnectionType = hasConnectionTypeFeature(currentForm.category);

    return {
      name: productName,
      brand: currentForm.brand || undefined,
      category: currentForm.category || undefined,
      color: currentForm.color || undefined,
      model: currentForm.model || undefined,
      connection_type: hasConnectionType
        ? currentForm.connectionType || undefined
        : null,
      storage_capacity: isPhone ? currentForm.storageCapacity || undefined : null,
      ram_capacity: isPhone ? currentForm.ramCapacity || undefined : null,
      sim_type: isPhone ? currentForm.simType || undefined : null,
      switch_type: isKeyboard ? currentForm.switchType || undefined : null,
      keyboard_layout: isKeyboard ? currentForm.keyboardLayout || undefined : null,
      display_name: productName,
      our_price: optionalNumber(currentForm.ourPrice),
      cost_price: optionalNumber(currentForm.costPrice),
      stock_quantity: optionalNumber(currentForm.stockQuantity),
    };
  }

  async function createCompanyProduct(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session) return;

    if (!selectedMarketplaces.length) {
      setToast({ type: "error", message: "Devam etmek için en az bir pazaryeri seçin." });
      return;
    }

    setIsLoading(true);
    try {
      const product = await pricingApi.createProduct({
        ...productFormPayload(form),
      });

      await Promise.all(
        selectedMarketplaces.map((marketplace) =>
          pricingApi.createSellerProduct({
            company_id: session.company_id,
            product_id: product.id,
            marketplace,
            display_name: buildProductNameFromParts(form.brand, form.model),
            our_price: optionalNumber(form.ourPrice),
            cost_price: optionalNumber(form.costPrice),
            stock_quantity: optionalNumber(form.stockQuantity) ?? 0,
          }),
        ),
      );

      setForm({
        brand: "",
        category: "",
        color: "",
        model: "",
        connectionType: "",
        storageCapacity: "",
        ramCapacity: "",
        simType: "",
        switchType: "",
        keyboardLayout: "",
        ourPrice: "",
        costPrice: "",
        stockQuantity: "",
      });
      setToast({
        type: "success",
        message: "Ürün listenize eklendi. Hazır olduğunuzda satırdaki Analiz Başlat butonuyla rakip analizini çalıştırabilirsiniz.",
      });
      await loadData(session);
    } catch (error) {
      setToast({ type: "error", message: errorMessage(error) });
    } finally {
      setIsLoading(false);
    }
  }

  function startEditing(row: ProductInsight) {
    const sellerProduct = primarySellerProduct(row);
    setEditingProductId(row.product.id);
    setEditForm({
      brand: row.product.brand || "",
      category: row.product.category || "",
      color: row.product.color || "",
      model: row.product.model || "",
      connectionType: row.product.connection_type || "",
      storageCapacity: row.product.storage_capacity || "",
      ramCapacity: row.product.ram_capacity || "",
      simType: row.product.sim_type || "",
      switchType: row.product.switch_type || "",
      keyboardLayout: row.product.keyboard_layout || "",
      ourPrice: toInputValue(sellerProduct?.our_price),
      costPrice: toInputValue(sellerProduct?.cost_price),
      stockQuantity: toInputValue(sellerProduct?.stock_quantity),
    });
  }

  async function updateCompanyProduct(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session || !editForm || !editingProductId) return;

    setIsLoading(true);
    try {
      await pricingApi.updateCompanyProduct(
        session.company_id,
        editingProductId,
        productFormPayload(editForm),
      );
      setToast({ type: "success", message: "Ürün bilgileri güncellendi." });
      setEditingProductId("");
      setEditForm(null);
      await loadData(session);
    } catch (error) {
      setToast({ type: "error", message: errorMessage(error) });
    } finally {
      setIsLoading(false);
    }
  }

  async function deleteCompanyProduct(row: ProductInsight) {
    if (!session) return;

    const confirmed = window.confirm(
      `${productDisplayName(row)} ürününü şirket listenizden kaldırmak istiyor musunuz?`,
    );
    if (!confirmed) return;

    setIsLoading(true);
    try {
      await pricingApi.deleteCompanyProduct(session.company_id, row.product.id);
      setToast({ type: "success", message: "Ürün şirket listenizden kaldırıldı." });
      if (expandedProductId === row.product.id) setExpandedProductId("");
      if (editingProductId === row.product.id) {
        setEditingProductId("");
        setEditForm(null);
      }
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
      message: `${productDisplayName(row)} için analiz çalışıyor. Sonuç hazır olduğunda satır otomatik güncellenecek.`,
    });

    try {
      const result = await pricingApi.runAnalysis({
        product_id: row.product.id,
        company_id: session.company_id,
        query: buildQuery(row),
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
            Ürünler
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {company?.name || "Şirketiniz"} için ürün ekleyin, analiz başlatın ve fiyat önerilerini inceleyin.
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
              Şirket ürünü ekle
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Ürünü şirket listenize ekleyin; analiz butonuyla rakip verilerini dilediğiniz zaman toplayabilirsiniz.
            </p>
          </div>
        </div>

        <form
          className="grid grid-cols-1 gap-6 xl:grid-cols-[1fr_0.8fr_auto]"
          onSubmit={(event) => void createCompanyProduct(event)}
        >
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:col-span-1 xl:grid-cols-2">
            <div className="hidden">
              <Label>Ürün adı</Label>
              <Input
                placeholder="Orn. Samsung S24 FE"
                value={buildProductNameFromParts(form.brand, form.model)}
                disabled
              />
            </div>
            <div className="order-1">
              <Label>Marka</Label>
              <Input
                list="product-brand-options"
                placeholder="Orn. Samsung"
                value={form.brand}
                onChange={(event) =>
                  setForm((current) => ({ ...current, brand: event.target.value }))
                }
              />
              <datalist id="product-brand-options">
                {brandOptions.map((brand) => (
                  <option key={brand} value={brand} />
                ))}
              </datalist>
            </div>
            <div className="order-3">
              <Label>Kategori</Label>
              <select
                className={selectClass}
                value={form.category}
                onChange={(event) => {
                  const category = event.target.value;
                  setForm((current) => ({
                    ...current,
                    category,
                    connectionType: hasConnectionTypeFeature(category)
                      ? current.connectionType
                      : "",
                    storageCapacity: isPhoneCategory(category)
                      ? current.storageCapacity
                      : "",
                    ramCapacity: isPhoneCategory(category) ? current.ramCapacity : "",
                    simType: isPhoneCategory(category) ? current.simType : "",
                    switchType: isKeyboardCategory(category)
                      ? current.switchType
                      : "",
                    keyboardLayout: isKeyboardCategory(category)
                      ? current.keyboardLayout
                      : "",
                  }));
                }}
              >
                <option value="">Kategori seçin</option>
                {categoryOptions.map((category) => (
                  <option key={category} value={category}>
                    {category}
                  </option>
                ))}
              </select>
            </div>
            <div className="order-4">
              <Label>Renk</Label>
              <select
                className={selectClass}
                value={form.color}
                onChange={(event) =>
                  setForm((current) => ({ ...current, color: event.target.value }))
                }
              >
                <option value="">Renk seçin</option>
                {colorOptions.map((color) => (
                  <option key={color} value={color}>
                    {color}
                  </option>
                ))}
              </select>
            </div>
            <div className="order-2">
              <Label>Model</Label>
              <Input
                placeholder="Orn. SM-S711B"
                value={form.model}
                onChange={(event) =>
                  setForm((current) => ({ ...current, model: event.target.value }))
                }
              />
            </div>
            {hasProductFeatures(form.category) && (
              <div className="order-5 rounded-lg border border-gray-100 p-4 md:col-span-2 dark:border-gray-800">
                <h3 className="mb-3 text-sm font-semibold text-gray-900 dark:text-white">
                  Ürün özellikleri
                </h3>
                {hasConnectionTypeFeature(form.category) && (
                  <div>
                    <Label>Bağlantı tipi</Label>
                    <select
                      className={selectClass}
                      value={form.connectionType}
                      onChange={(event) =>
                        setForm((current) => ({
                          ...current,
                          connectionType: event.target.value,
                        }))
                      }
                    >
                      <option value="">Bağlantı tipi seçin</option>
                      {connectionTypeOptions.map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
                {isPhoneCategory(form.category) && (
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                    <div>
                      <Label>Hafıza</Label>
                      <select
                        className={selectClass}
                        value={form.storageCapacity}
                        onChange={(event) =>
                          setForm((current) => ({
                            ...current,
                            storageCapacity: event.target.value,
                          }))
                        }
                      >
                        <option value="">Hafıza seçin</option>
                        {storageOptions.map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <Label>RAM</Label>
                      <select
                        className={selectClass}
                        value={form.ramCapacity}
                        onChange={(event) =>
                          setForm((current) => ({
                            ...current,
                            ramCapacity: event.target.value,
                          }))
                        }
                      >
                        <option value="">RAM seçin</option>
                        {ramOptions.map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <Label>SIM kart</Label>
                      <select
                        className={selectClass}
                        value={form.simType}
                        onChange={(event) =>
                          setForm((current) => ({
                            ...current,
                            simType: event.target.value,
                          }))
                        }
                      >
                        <option value="">SIM tipi seçin</option>
                        {simTypeOptions.map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                )}
                {isKeyboardCategory(form.category) && (
                  <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
                    <div>
                      <Label>Switch tipi</Label>
                      <select
                        className={selectClass}
                        value={form.switchType}
                        onChange={(event) =>
                          setForm((current) => ({
                            ...current,
                            switchType: event.target.value,
                          }))
                        }
                      >
                        <option value="">Switch tipi seçin</option>
                        {switchTypeOptions.map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <Label>Dil dizilimi</Label>
                      <select
                        className={selectClass}
                        value={form.keyboardLayout}
                        onChange={(event) =>
                          setForm((current) => ({
                            ...current,
                            keyboardLayout: event.target.value,
                          }))
                        }
                      >
                        <option value="">Dil dizilimi seçin</option>
                        {keyboardLayoutOptions.map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                )}
              </div>
            )}
            <div className="order-7">
              <Label>Satış fiyatı</Label>
              <Input
                type="number"
                min="0"
                step={0.01}
                placeholder="Orn. 24999"
                value={form.ourPrice}
                onChange={(event) =>
                  setForm((current) => ({ ...current, ourPrice: event.target.value }))
                }
              />
            </div>
            <div className="order-7">
              <Label>Maliyet</Label>
              <Input
                type="number"
                min="0"
                step={0.01}
                placeholder="Orn. 21000"
                value={form.costPrice}
                onChange={(event) =>
                  setForm((current) => ({ ...current, costPrice: event.target.value }))
                }
              />
            </div>
            <div className="order-8">
              <Label>Stok</Label>
              <Input
                type="number"
                min="0"
                step={1}
                placeholder="Orn. 25"
                value={form.stockQuantity}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    stockQuantity: event.target.value,
                  }))
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

          <div className="order-7 flex items-end">
            <Button
              disabled={
                isLoading ||
                !form.brand.trim() ||
                !form.model.trim() ||
                !selectedMarketplaces.length
              }
              startIcon={<PlusIcon />}
            >
              Ürün Ekle
            </Button>
          </div>
        </form>
      </section>

      {editForm && (
        <section className={cardClass}>
          <div className="mb-5 flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Ürün bilgilerini düzenle
              </h2>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                Değişiklikler bu şirketin aktif pazaryeri kayıtlarına uygulanır.
              </p>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => {
                setEditingProductId("");
                setEditForm(null);
              }}
            >
              Vazgeç
            </Button>
          </div>

          <form
            className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-2"
            onSubmit={(event) => void updateCompanyProduct(event)}
          >
            <div className="hidden">
              <Label>Ürün adı</Label>
              <Input
                value={buildProductNameFromParts(editForm.brand, editForm.model)}
                disabled
              />
            </div>
            <div className="order-1">
              <Label>Marka</Label>
              <Input
                list="product-brand-options"
                value={editForm.brand}
                onChange={(event) =>
                  setEditForm((current) =>
                    current ? { ...current, brand: event.target.value } : current,
                  )
                }
              />
            </div>
            <div className="order-3">
              <Label>Kategori</Label>
              <select
                className={selectClass}
                value={editForm.category}
                onChange={(event) => {
                  const category = event.target.value;
                  setEditForm((current) =>
                    current
                      ? {
                          ...current,
                          category,
                          connectionType: hasConnectionTypeFeature(category)
                            ? current.connectionType
                            : "",
                          storageCapacity: isPhoneCategory(category)
                            ? current.storageCapacity
                            : "",
                          ramCapacity: isPhoneCategory(category)
                            ? current.ramCapacity
                            : "",
                          simType: isPhoneCategory(category) ? current.simType : "",
                          switchType: isKeyboardCategory(category)
                            ? current.switchType
                            : "",
                          keyboardLayout: isKeyboardCategory(category)
                            ? current.keyboardLayout
                            : "",
                        }
                      : current,
                  );
                }}
              >
                <option value="">Kategori seçin</option>
                {categoryOptions.map((category) => (
                  <option key={category} value={category}>
                    {category}
                  </option>
                ))}
              </select>
            </div>
            <div className="order-4">
              <Label>Renk</Label>
              <select
                className={selectClass}
                value={editForm.color}
                onChange={(event) =>
                  setEditForm((current) =>
                    current ? { ...current, color: event.target.value } : current,
                  )
                }
              >
                <option value="">Renk seçin</option>
                {colorOptions.map((color) => (
                  <option key={color} value={color}>
                    {color}
                  </option>
                ))}
              </select>
            </div>
            <div className="order-2">
              <Label>Model</Label>
              <Input
                value={editForm.model}
                onChange={(event) =>
                  setEditForm((current) =>
                    current ? { ...current, model: event.target.value } : current,
                  )
                }
              />
            </div>
            {hasProductFeatures(editForm.category) && (
              <div className="order-5 rounded-lg border border-gray-100 p-4 md:col-span-2 dark:border-gray-800">
                <h3 className="mb-3 text-sm font-semibold text-gray-900 dark:text-white">
                  Ürün özellikleri
                </h3>
                {hasConnectionTypeFeature(editForm.category) && (
                  <div>
                    <Label>Bağlantı tipi</Label>
                    <select
                      className={selectClass}
                      value={editForm.connectionType}
                      onChange={(event) =>
                        setEditForm((current) =>
                          current
                            ? { ...current, connectionType: event.target.value }
                            : current,
                        )
                      }
                    >
                      <option value="">Bağlantı tipi seçin</option>
                      {connectionTypeOptions.map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
                {isPhoneCategory(editForm.category) && (
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                    <div>
                      <Label>Hafıza</Label>
                      <select
                        className={selectClass}
                        value={editForm.storageCapacity}
                        onChange={(event) =>
                          setEditForm((current) =>
                            current
                              ? { ...current, storageCapacity: event.target.value }
                              : current,
                          )
                        }
                      >
                        <option value="">Hafıza seçin</option>
                        {storageOptions.map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <Label>RAM</Label>
                      <select
                        className={selectClass}
                        value={editForm.ramCapacity}
                        onChange={(event) =>
                          setEditForm((current) =>
                            current
                              ? { ...current, ramCapacity: event.target.value }
                              : current,
                          )
                        }
                      >
                        <option value="">RAM seçin</option>
                        {ramOptions.map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <Label>SIM kart</Label>
                      <select
                        className={selectClass}
                        value={editForm.simType}
                        onChange={(event) =>
                          setEditForm((current) =>
                            current
                              ? { ...current, simType: event.target.value }
                              : current,
                          )
                        }
                      >
                        <option value="">SIM tipi seçin</option>
                        {simTypeOptions.map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                )}
                {isKeyboardCategory(editForm.category) && (
                  <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
                    <div>
                      <Label>Switch tipi</Label>
                      <select
                        className={selectClass}
                        value={editForm.switchType}
                        onChange={(event) =>
                          setEditForm((current) =>
                            current
                              ? { ...current, switchType: event.target.value }
                              : current,
                          )
                        }
                      >
                        <option value="">Switch tipi seçin</option>
                        {switchTypeOptions.map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <Label>Dil dizilimi</Label>
                      <select
                        className={selectClass}
                        value={editForm.keyboardLayout}
                        onChange={(event) =>
                          setEditForm((current) =>
                            current
                              ? { ...current, keyboardLayout: event.target.value }
                              : current,
                          )
                        }
                      >
                        <option value="">Dil dizilimi seçin</option>
                        {keyboardLayoutOptions.map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                )}
              </div>
            )}
            <div className="order-6">
              <Label>Satış fiyatı</Label>
              <Input
                type="number"
                min="0"
                step={0.01}
                value={editForm.ourPrice}
                onChange={(event) =>
                  setEditForm((current) =>
                    current ? { ...current, ourPrice: event.target.value } : current,
                  )
                }
              />
            </div>
            <div className="order-6">
              <Label>Maliyet</Label>
              <Input
                type="number"
                min="0"
                step={0.01}
                value={editForm.costPrice}
                onChange={(event) =>
                  setEditForm((current) =>
                    current ? { ...current, costPrice: event.target.value } : current,
                  )
                }
              />
            </div>
            <div className="order-7">
              <Label>Stok</Label>
              <Input
                type="number"
                min="0"
                step={1}
                value={editForm.stockQuantity}
                onChange={(event) =>
                  setEditForm((current) =>
                    current
                      ? { ...current, stockQuantity: event.target.value }
                      : current,
                  )
                }
              />
            </div>
            <div className="order-8 flex items-end">
              <Button
                disabled={
                  isLoading ||
                  !editForm.brand.trim() ||
                  !editForm.model.trim() ||
                  !editingProductId
                }
                startIcon={<PlusIcon />}
              >
                Değişiklikleri Kaydet
              </Button>
            </div>
          </form>
        </section>
      )}

      <section className={cardClass}>
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Şirket ürünleri
            </h2>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Fiyat kararlarını ürün bazında buradan yönetin.
            </p>
          </div>
          <Badge color="light" size="sm">
            {rows.length} ürün
          </Badge>
        </div>

        <div className="max-w-full overflow-x-auto">
          <Table>
            <TableHeader className="border-y border-gray-100 dark:border-gray-800">
              <TableRow>
                {["Ürün", "Durum", "Son Analiz", "Önerilen Fiyat", "Buybox Riski", "Aksiyon"].map((heading) => (
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
                            {productDisplayName(row)}
                          </p>
                          <p className="text-theme-xs text-gray-500 dark:text-gray-400">
                            {[row.product.brand, row.product.model, row.product.color, row.product.category].filter(Boolean).join(" / ") || "-"}
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
                      <div className="flex min-w-[260px] flex-wrap gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => startEditing(row)}
                          startIcon={<PencilIcon className="size-4" />}
                          className="text-gray-700 dark:text-gray-300"
                        >
                          Düzenle
                        </Button>
                        <Button
                          size="sm"
                          variant="danger"
                          onClick={() => void deleteCompanyProduct(row)}
                          startIcon={<TrashBinIcon className="size-4" />}
                        >
                          Sil
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() =>
                            setExpandedProductId((current) =>
                              current === row.product.id ? "" : row.product.id,
                            )
                          }
                          startIcon={<EyeIcon className="size-4" />}
                        >
                          {expandedProductId === row.product.id ? "Kapat" : "Detay"}
                        </Button>
                        <Button
                          size="sm"
                          disabled={activeProductId === row.product.id}
                          onClick={() => void analyzeProduct(row)}
                          startIcon={<BoltIcon className="size-4" />}
                        >
                          {activeProductId === row.product.id
                            ? "Analiz Çalışıyor..."
                            : latestAt
                              ? "Yeniden Analiz Et"
                              : "Analiz Başlat"}
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
              {!rows.length && (
                <TableRow>
                  <TableCell className="py-6 text-center text-sm text-gray-500 dark:text-gray-400">
                    Henüz şirketinize ait ürün yok.
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
      : "Rakip verisi geldikçe en önemli satıcılar burada özetlenir.",
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
            {productDisplayName(row)} Analiz Özeti
          </h2>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Varsayılan görünüm fiyat önerisi, risk ve kısa gerekçeyi gösterir.
          </p>
        </div>
        <RiskBadge row={row} />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <MetricCard
          label="Önerilen Fiyat"
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
          Gerekçe
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
          Detaylı Analiz
        </h3>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
          <InfoPill label="Rakip Sayisi" value={row.listings.length} />
          <InfoPill label="Analizde Kullanılan" value={usedCompetitorCount} />
          <InfoPill label="Göz Ardı Edilen" value={ignoredCompetitorCount} />
        </div>

        <div className="mt-4 max-w-full overflow-x-auto">
          <Table>
            <TableHeader className="border-y border-gray-100 dark:border-gray-800">
              <TableRow>
                {["Satıcı", "Fiyat", "Tehdit", "Neden önemli"].map((heading) => (
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
                    Henüz rakip analizi yok.
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
  const label = score >= 70 ? "Yüksek" : score >= 40 ? "Orta" : "Düşük";
  const color = score >= 70 ? "error" : score >= 40 ? "warning" : "success";

  return (
    <Badge color={color} size="sm">
      {label}
    </Badge>
  );
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Beklenmeyen bir hata oluştu.";
}
