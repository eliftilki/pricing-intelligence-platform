"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Badge from "@/components/ui/badge/Badge";
import Button from "@/components/ui/button/Button";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { AuthSession, getAuthSession } from "@/lib/auth-session";
import {
  Company,
  CompetitorTier,
  PriceRecommendation,
  Product,
  SellerProduct,
  pricingApi,
} from "@/lib/pricing-api";
import { BoltIcon, BoxIconLine, DollarLineIcon, GroupIcon } from "@/icons";

type LoadState = "idle" | "loading" | "success" | "error";

type ProductSummary = {
  product: Product;
  sellerProducts: SellerProduct[];
  recommendations: PriceRecommendation[];
  tiers: CompetitorTier[];
};

type Toast = {
  type: "success" | "error";
  message: string;
};

const cardClass =
  "rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03]";

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

function latestDate(summary: ProductSummary) {
  const dates = [
    ...summary.recommendations.map((item) => item.created_at),
    ...summary.tiers.map((item) => item.analyzed_at),
  ]
    .filter((date): date is string => Boolean(date))
    .map((date) => new Date(date).getTime())
    .filter((time) => !Number.isNaN(time));

  return dates.length ? Math.max(...dates) : null;
}

function latestRecommendation(summary: ProductSummary) {
  return [...summary.recommendations].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  )[0];
}

function isRisky(summary: ProductSummary) {
  const recommendation = latestRecommendation(summary);
  const risk = recommendation?.risk_level?.toLocaleLowerCase("tr-TR") || "";
  const maxBuybox = Math.max(
    0,
    ...summary.tiers.map((tier) => Number(tier.buybox_threat_score || 0)),
  );

  return risk.includes("high") || risk.includes("yuksek") || maxBuybox >= 70;
}

export default function PricingDashboard() {
  const router = useRouter();
  const [session, setSession] = useState<AuthSession | null>(null);
  const [company, setCompany] = useState<Company | null>(null);
  const [summaries, setSummaries] = useState<ProductSummary[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [toast, setToast] = useState<Toast | null>(null);

  async function loadDashboard(activeSession = session) {
    if (!activeSession) return;

    setLoadState("loading");
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

      const productSummaries = await Promise.all(
        Array.from(grouped.entries()).map(async ([productId, items]) => {
          const product = productMap.get(productId);
          if (!product) return null;

          const [tiers, recommendationGroups] = await Promise.all([
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
            recommendations: recommendationGroups.flat(),
            tiers,
          };
        }),
      );

      setCompany(companyData);
      setSummaries(
        productSummaries.filter(
          (summary): summary is ProductSummary => summary !== null,
        ),
      );
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
    void loadDashboard(activeSession);
  }, []);

  const metrics = useMemo(() => {
    const analyzed = summaries.filter((summary) => latestDate(summary) !== null);
    const pending = summaries.filter((summary) => latestDate(summary) === null);
    const risky = summaries.filter(isRisky);

    return [
      {
        label: "Toplam Urun",
        value: summaries.length,
        icon: <BoxIconLine className="text-gray-800 dark:text-white/90" />,
      },
      {
        label: "Toplam Analiz",
        value: analyzed.length,
        icon: <BoltIcon className="text-gray-800 size-6 dark:text-white/90" />,
      },
      {
        label: "Riskli Urun",
        value: risky.length,
        icon: <DollarLineIcon className="text-gray-800 size-6 dark:text-white/90" />,
      },
      {
        label: "Analiz Bekliyor",
        value: pending.length,
        icon: <GroupIcon className="text-gray-800 size-6 dark:text-white/90" />,
      },
    ];
  }, [summaries]);

  const recentAnalyses = useMemo(
    () =>
      summaries
        .map((summary) => ({ ...summary, latestAt: latestDate(summary) }))
        .filter((summary) => summary.latestAt !== null)
        .sort((a, b) => (b.latestAt || 0) - (a.latestAt || 0))
        .slice(0, 5),
    [summaries],
  );

  const pendingAnalyses = useMemo(
    () => summaries.filter((summary) => latestDate(summary) === null).slice(0, 5),
    [summaries],
  );

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
            {company?.name || "feraSet"} Dashboard
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Urun portfoyunuzun analiz durumunu ve risk ozetini takip edin.
          </p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <Button
            variant="outline"
            onClick={() => void loadDashboard()}
            disabled={loadState === "loading"}
          >
            Yenile
          </Button>
          <Link href="/products">
            <Button>Urunlere Git</Button>
          </Link>
        </div>
      </div>

      {toast && (
        <div
          className={`rounded-lg border px-4 py-3 text-sm ${
            toast.type === "error"
              ? "border-error-200 bg-error-50 text-error-700 dark:border-error-500/30 dark:bg-error-500/10 dark:text-error-300"
              : "border-success-200 bg-success-50 text-success-700 dark:border-success-500/30 dark:bg-success-500/10 dark:text-success-300"
          }`}
        >
          {toast.message}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => (
          <div key={metric.label} className={cardClass}>
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-gray-100 dark:bg-gray-800">
              {metric.icon}
            </div>
            <div className="mt-5">
              <span className="text-sm text-gray-500 dark:text-gray-400">
                {metric.label}
              </span>
              <h2 className="mt-2 text-2xl font-semibold text-gray-900 dark:text-white">
                {metric.value}
              </h2>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <section className={`${cardClass} xl:col-span-2`}>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Son Calisan Analizler
            </h2>
            <Badge color="light" size="sm">
              {recentAnalyses.length} kayit
            </Badge>
          </div>
          <div className="max-w-full overflow-x-auto">
            <Table>
              <TableHeader className="border-y border-gray-100 dark:border-gray-800">
                <TableRow>
                  {["Urun", "Onerilen Fiyat", "Risk", "Son Analiz"].map((heading) => (
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
                {recentAnalyses.map((summary) => {
                  const recommendation = latestRecommendation(summary);
                  const date = summary.latestAt
                    ? new Date(summary.latestAt).toLocaleString("tr-TR", {
                        day: "2-digit",
                        month: "short",
                        hour: "2-digit",
                        minute: "2-digit",
                      })
                    : "-";

                  return (
                    <TableRow key={summary.product.id}>
                      <TableCell className="py-3 text-theme-sm font-medium text-gray-900 dark:text-white">
                        {summary.product.name}
                      </TableCell>
                      <TableCell className="py-3 text-theme-sm text-gray-700 dark:text-gray-300">
                        {toMoney(recommendation?.recommended_price)}
                      </TableCell>
                      <TableCell className="py-3">
                        <RiskBadge summary={summary} />
                      </TableCell>
                      <TableCell className="py-3 text-theme-sm text-gray-700 dark:text-gray-300">
                        {date}
                      </TableCell>
                    </TableRow>
                  );
                })}
                {!recentAnalyses.length && (
                  <TableRow>
                    <TableCell className="py-6 text-center text-sm text-gray-500 dark:text-gray-400">
                      Henuz calismis analiz yok.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </section>

        <section className={cardClass}>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Bekleyen Analizler
            </h2>
            <Badge color={pendingAnalyses.length ? "warning" : "success"} size="sm">
              {pendingAnalyses.length} urun
            </Badge>
          </div>
          <div className="space-y-3">
            {pendingAnalyses.map((summary) => (
              <div
                key={summary.product.id}
                className="rounded-lg border border-gray-100 p-3 dark:border-gray-800"
              >
                <p className="font-medium text-gray-900 text-theme-sm dark:text-white">
                  {summary.product.name}
                </p>
                <p className="mt-1 text-theme-xs text-gray-500 dark:text-gray-400">
                  Analiz baslatilmayi bekliyor.
                </p>
              </div>
            ))}
            {!pendingAnalyses.length && (
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Bekleyen analiz yok.
              </p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

function RiskBadge({ summary }: { summary: ProductSummary }) {
  const recommendation = latestRecommendation(summary);
  const risk = recommendation?.risk_level || (isRisky(summary) ? "Yuksek" : "Dusuk");
  const normalizedRisk = risk.toLocaleLowerCase("tr-TR");
  const color =
    normalizedRisk.includes("high") || normalizedRisk.includes("yuksek")
      ? "error"
      : normalizedRisk.includes("medium") || normalizedRisk.includes("orta")
        ? "warning"
        : "success";

  return (
    <Badge color={color} size="sm">
      {risk}
    </Badge>
  );
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Beklenmeyen bir hata olustu.";
}
