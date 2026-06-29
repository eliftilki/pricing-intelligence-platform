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
import { Product, SellerProduct, pricingApi } from "@/lib/pricing-api";
import { BoxIconLine, CheckCircleIcon } from "@/icons";

type Toast = {
  type: "success" | "error";
  message: string;
};

type SalesFormState = {
  quantity: string;
  salesDate: string;
  note: string;
};

type SalesRow = {
  sellerProduct: SellerProduct;
  product?: Product;
};

type MarketplaceGroup = {
  key: string;
  label: string;
  rows: SalesRow[];
};

const cardClass =
  "rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03]";
const marketplaceOrder = ["TRENDYOL", "HEPSIBURADA", "AMAZON"];
const marketplaceLabels: Record<string, string> = {
  TRENDYOL: "Trendyol",
  HEPSIBURADA: "Hepsiburada",
  AMAZON: "Amazon",
};

function todayInputValue() {
  return new Date().toISOString().slice(0, 10);
}

function productDisplayName(row: SalesRow) {
  const generatedName = [row.product?.brand, row.product?.model]
    .filter(Boolean)
    .join(" ")
    .trim();
  return generatedName || row.sellerProduct.display_name || row.product?.name || "-";
}

function productMeta(row: SalesRow) {
  return [row.product?.category, row.product?.color].filter(Boolean).join(" / ");
}

function parseQuantity(value: string) {
  if (!value.trim()) return null;
  const numeric = Number(value);
  if (!Number.isInteger(numeric) || numeric < 0) return null;
  return numeric;
}

function defaultSalesForm(): SalesFormState {
  return {
    quantity: "",
    salesDate: todayInputValue(),
    note: "",
  };
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Beklenmeyen bir hata olustu.";
}

export default function SalesQuantitiesPage() {
  const router = useRouter();
  const [session, setSession] = useState<AuthSession | null>(null);
  const [rows, setRows] = useState<SalesRow[]>([]);
  const [forms, setForms] = useState<Record<string, SalesFormState>>({});
  const [toast, setToast] = useState<Toast | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [savingId, setSavingId] = useState("");

  const totalProducts = useMemo(
    () => new Set(rows.map((row) => row.sellerProduct.product_id)).size,
    [rows],
  );

  const marketplaceGroups = useMemo<MarketplaceGroup[]>(() => {
    const grouped = new Map<string, SalesRow[]>();
    rows.forEach((row) => {
      const key = row.sellerProduct.marketplace.toUpperCase();
      grouped.set(key, [...(grouped.get(key) || []), row]);
    });

    const orderedKeys = [
      ...marketplaceOrder.filter((marketplace) => grouped.has(marketplace)),
      ...Array.from(grouped.keys()).filter(
        (marketplace) => !marketplaceOrder.includes(marketplace),
      ),
    ];

    return orderedKeys.map((key) => ({
      key,
      label: marketplaceLabels[key] || key,
      rows: grouped.get(key) || [],
    }));
  }, [rows]);

  async function loadData(activeSession = session) {
    if (!activeSession) return;
    setIsLoading(true);
    try {
      const [products, sellerProducts] = await Promise.all([
        pricingApi.listProducts(),
        pricingApi.listSellerProducts(activeSession.company_id),
      ]);
      const productMap = new Map(products.map((product) => [product.id, product]));
      const nextRows = sellerProducts.map((sellerProduct) => ({
        sellerProduct,
        product: productMap.get(sellerProduct.product_id),
      }));

      setRows(nextRows);
      setForms((current) => {
        const nextForms = { ...current };
        nextRows.forEach((row) => {
          if (!nextForms[row.sellerProduct.id]) {
            nextForms[row.sellerProduct.id] = defaultSalesForm();
          }
        });
        return nextForms;
      });
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

  function updateForm(sellerProductId: string, values: Partial<SalesFormState>) {
    setForms((current) => ({
      ...current,
      [sellerProductId]: {
        ...defaultSalesForm(),
        ...current[sellerProductId],
        ...values,
      },
    }));
  }

  async function saveSalesQuantity(
    event: FormEvent<HTMLFormElement>,
    sellerProductId: string,
  ) {
    event.preventDefault();

    const form = forms[sellerProductId];
    const salesQuantity = parseQuantity(form?.quantity || "");
    if (salesQuantity === null) {
      setToast({
        type: "error",
        message: "Satis miktari sifir veya pozitif bir tam sayi olmali.",
      });
      return;
    }
    const row = rows.find((item) => item.sellerProduct.id === sellerProductId);
    const currentStock = row?.sellerProduct.stock_quantity ?? 0;
    if (salesQuantity > currentStock) {
      setToast({
        type: "error",
        message: "Satis miktari mevcut stoktan fazla olamaz.",
      });
      return;
    }

    setSavingId(sellerProductId);
    try {
      await pricingApi.recordSalesQuantity(sellerProductId, {
        sales_quantity: salesQuantity,
        sales_date: form.salesDate ? new Date(form.salesDate).toISOString() : undefined,
        note: form.note || undefined,
      });
      updateForm(sellerProductId, { quantity: "", note: "" });
      setToast({ type: "success", message: "Satis miktari kaydedildi ve stok dusuruldu." });
      await loadData();
    } catch (error) {
      setToast({ type: "error", message: errorMessage(error) });
    } finally {
      setSavingId("");
    }
  }

  function renderSalesRow(row: SalesRow) {
    const form = forms[row.sellerProduct.id] || defaultSalesForm();

    return (
      <TableRow key={row.sellerProduct.id}>
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
                {productMeta(row) || "-"}
              </p>
            </div>
          </div>
        </TableCell>
        <TableCell className="py-3 text-theme-sm text-gray-700 dark:text-gray-300">
          {row.sellerProduct.stock_quantity}
        </TableCell>
        <TableCell className="py-3">
          <form
            className="grid min-w-[520px] grid-cols-[120px_150px_1fr_auto] items-end gap-3"
            onSubmit={(event) => void saveSalesQuantity(event, row.sellerProduct.id)}
          >
            <div>
              <Label>Adet</Label>
              <Input
                type="number"
                min="0"
                step={1}
                value={form.quantity}
                onChange={(event) =>
                  updateForm(row.sellerProduct.id, {
                    quantity: event.target.value,
                  })
                }
              />
            </div>
            <div>
              <Label>Tarih</Label>
              <Input
                type="date"
                value={form.salesDate}
                onChange={(event) =>
                  updateForm(row.sellerProduct.id, {
                    salesDate: event.target.value,
                  })
                }
              />
            </div>
            <div>
              <Label>Not</Label>
              <Input
                value={form.note}
                placeholder="Opsiyonel"
                onChange={(event) =>
                  updateForm(row.sellerProduct.id, {
                    note: event.target.value,
                  })
                }
              />
            </div>
            <Button
              size="sm"
              disabled={savingId === row.sellerProduct.id}
              startIcon={<CheckCircleIcon className="size-4" />}
            >
              Kaydet
            </Button>
          </form>
        </TableCell>
      </TableRow>
    );
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
            Satis Miktarlari
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Urun ve pazaryeri bazinda gerceklesen satis adetlerini kaydedin.
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
              : "border-success-200 bg-success-50 text-success-700 dark:border-success-500/30 dark:bg-success-500/10 dark:text-success-300"
          }`}
        >
          {toast.message}
        </div>
      )}

      <section className={cardClass}>
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Gunluk satis girisi
            </h2>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Her kayit gecmise eklenir; stok degerini degistirmez.
            </p>
          </div>
          <div className="flex gap-2">
            <Badge color="light" size="sm">
              {totalProducts} urun
            </Badge>
            <Badge color="light" size="sm">
              {rows.length} pazaryeri kaydi
            </Badge>
          </div>
        </div>

        <div className="space-y-5">
          {marketplaceGroups.map((group) => (
            <div
              key={group.key}
              className="rounded-lg border border-gray-100 dark:border-gray-800"
            >
              <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3 dark:border-gray-800">
                <div>
                  <h3 className="text-base font-semibold text-gray-900 dark:text-white">
                    {group.label}
                  </h3>
                  <p className="mt-1 text-theme-xs text-gray-500 dark:text-gray-400">
                    {group.rows.length} pazaryeri urunu icin satis girisi
                  </p>
                </div>
                <Badge color="light" size="sm">
                  {group.rows.length} kayit
                </Badge>
              </div>
              <div className="max-w-full overflow-x-auto">
                <Table>
                  <TableHeader className="border-y border-gray-100 dark:border-gray-800">
                    <TableRow>
                      {["Urun", "Mevcut Stok", "Satis Girisi"].map((heading) => (
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
                    {group.rows.map(renderSalesRow)}
                  </TableBody>
                </Table>
              </div>
            </div>
          ))}
          {!rows.length && (
            <div className="rounded-lg border border-gray-100 py-8 text-center text-sm text-gray-500 dark:border-gray-800 dark:text-gray-400">
              Satis girisi yapilacak urun bulunamadi.
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
