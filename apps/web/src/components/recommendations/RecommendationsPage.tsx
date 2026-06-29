"use client";

import React, { useEffect, useState } from "react";
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
  PriceRecommendation,
  Product,
  SellerProduct,
  pricingApi,
} from "@/lib/pricing-api";

type LoadState = "idle" | "loading" | "success" | "error";

type RecommendationRow = {
  recommendation: PriceRecommendation;
  product?: Product;
  sellerProduct?: SellerProduct;
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

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Beklenmeyen bir hata oluştu.";
}

function productName(row: RecommendationRow) {
  return row.sellerProduct?.display_name || row.product?.name || "Bilinmeyen ürün";
}

function StatusBadge({ status }: { status: string }) {
  const normalized = status.toLocaleUpperCase("tr-TR");
  const color =
    normalized === "APPROVED" || normalized === "APPLIED"
      ? "success"
      : normalized === "REJECTED"
        ? "error"
        : "warning";

  const label =
    normalized === "PENDING"
      ? "Beklemede"
      : normalized === "APPROVED"
        ? "Onaylandı"
        : normalized === "REJECTED"
          ? "Reddedildi"
          : normalized === "APPLIED"
            ? "Uygulandı"
            : status;

  return (
    <Badge color={color} size="sm">
      {label}
    </Badge>
  );
}

function RiskBadge({ riskLevel }: { riskLevel: string | null | undefined }) {
  if (!riskLevel) {
    return (
      <Badge color="light" size="sm">
        -
      </Badge>
    );
  }

  const normalized = riskLevel.toLocaleLowerCase("tr-TR");
  const color =
    normalized.includes("high") || normalized.includes("yuksek")
      ? "error"
      : normalized.includes("medium") || normalized.includes("orta")
        ? "warning"
        : "success";

  return (
    <Badge color={color} size="sm">
      {riskLevel}
    </Badge>
  );
}

export default function RecommendationsPage() {
  const router = useRouter();
  const [session, setSession] = useState<AuthSession | null>(null);
  const [rows, setRows] = useState<RecommendationRow[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [toast, setToast] = useState<Toast | null>(null);
  const [decidingId, setDecidingId] = useState<string | null>(null);

  async function loadRecommendations(activeSession = session) {
    if (!activeSession) return;

    setLoadState("loading");
    try {
      const [products, sellerProducts] = await Promise.all([
        pricingApi.listProducts(),
        pricingApi.listSellerProducts(activeSession.company_id),
      ]);

      const productMap = new Map(products.map((product) => [product.id, product]));
      const sellerProductMap = new Map(
        sellerProducts.map((sellerProduct) => [sellerProduct.id, sellerProduct]),
      );

      const recommendationGroups = await Promise.all(
        sellerProducts.map((sellerProduct) =>
          pricingApi.listRecommendations(sellerProduct.id).catch(() => []),
        ),
      );

      const nextRows = recommendationGroups
        .flat()
        .map((recommendation) => ({
          recommendation,
          product: productMap.get(recommendation.product_id),
          sellerProduct: sellerProductMap.get(recommendation.seller_product_id),
        }))
        .sort(
          (a, b) =>
            new Date(b.recommendation.created_at).getTime() -
            new Date(a.recommendation.created_at).getTime(),
        );

      setRows(nextRows);
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
    void loadRecommendations(activeSession);
  }, []);

  async function handleDecision(
    recommendation: PriceRecommendation,
    action: "approve" | "reject" | "apply",
  ) {
    if (!session) return;

    setDecidingId(recommendation.id);
    try {
      await pricingApi.decideRecommendation(recommendation.id, action, undefined, session.access_token);
      setToast({ type: "success", message: "Karar kaydedildi." });
      await loadRecommendations();
    } catch (error) {
      setToast({ type: "error", message: errorMessage(error) });
    } finally {
      setDecidingId(null);
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
            Fiyat Önerileri
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Pipeline'ın ürettiği fiyat önerilerini inceleyin, onaylayın veya reddedin.
          </p>
        </div>
        <Button
          variant="outline"
          onClick={() => void loadRecommendations()}
          disabled={loadState === "loading"}
        >
          Yenile
        </Button>
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

      <section className={cardClass}>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Tüm Öneriler
          </h2>
          <Badge color="light" size="sm">
            {rows.length} kayıt
          </Badge>
        </div>
        <div className="max-w-full overflow-x-auto">
          <Table>
            <TableHeader className="border-y border-gray-100 dark:border-gray-800">
              <TableRow>
                {[
                  "Ürün",
                  "Güncel Fiyat",
                  "Önerilen Fiyat",
                  "Aksiyon",
                  "Risk",
                  "Durum",
                  "Tarih",
                  "",
                ].map((heading) => (
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
                const { recommendation } = row;
                const isPending = recommendation.status.toLocaleUpperCase("tr-TR") === "PENDING";
                const isDeciding = decidingId === recommendation.id;

                return (
                  <TableRow key={recommendation.id}>
                    <TableCell className="py-3 text-theme-sm font-medium text-gray-900 dark:text-white">
                      {productName(row)}
                    </TableCell>
                    <TableCell className="py-3 text-theme-sm text-gray-700 dark:text-gray-300">
                      {toMoney(recommendation.current_price)}
                    </TableCell>
                    <TableCell className="py-3 text-theme-sm text-gray-700 dark:text-gray-300">
                      {toMoney(recommendation.recommended_price)}
                    </TableCell>
                    <TableCell className="py-3 text-theme-sm text-gray-700 dark:text-gray-300">
                      {recommendation.action}
                    </TableCell>
                    <TableCell className="py-3">
                      <RiskBadge riskLevel={recommendation.risk_level} />
                    </TableCell>
                    <TableCell className="py-3">
                      <StatusBadge status={recommendation.status} />
                    </TableCell>
                    <TableCell className="py-3 text-theme-sm text-gray-700 dark:text-gray-300">
                      {new Date(recommendation.created_at).toLocaleString("tr-TR", {
                        day: "2-digit",
                        month: "short",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </TableCell>
                    <TableCell className="py-3">
                      {isPending ? (
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={isDeciding}
                            onClick={() => void handleDecision(recommendation, "approve")}
                          >
                            Onayla
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={isDeciding}
                            onClick={() => void handleDecision(recommendation, "reject")}
                          >
                            Reddet
                          </Button>
                        </div>
                      ) : recommendation.status.toLocaleUpperCase("tr-TR") === "APPROVED" ? (
                        <Button
                          size="sm"
                          disabled={isDeciding}
                          onClick={() => void handleDecision(recommendation, "apply")}
                        >
                          Fiyatı Uygula
                        </Button>
                      ) : null}
                    </TableCell>
                  </TableRow>
                );
              })}
              {!rows.length && (
                <TableRow>
                  <TableCell className="py-6 text-center text-sm text-gray-500 dark:text-gray-400">
                    Henüz oluşturulmuş bir fiyat önerisi yok.
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
