const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

export type UUID = string;

export type Company = {
  id: UUID;
  name: string;
  marketplace_seller_name?: string | null;
  tax_number?: string | null;
  website_url?: string | null;
  created_at: string;
};

export type Product = {
  id: UUID;
  name: string;
  brand?: string | null;
  model?: string | null;
  category?: string | null;
  barcode?: string | null;
  description?: string | null;
  created_at: string;
};

export type SellerProduct = {
  id: UUID;
  company_id: UUID;
  product_id: UUID;
  marketplace: string;
  marketplace_url?: string | null;
  marketplace_product_id?: string | null;
  our_price?: string | number | null;
  cost_price?: string | number | null;
  commission_rate: string | number;
  shipping_cost: string | number;
  packaging_cost: string | number;
  stock_quantity: number;
  min_margin_rate: string | number;
  is_active: boolean;
  created_at: string;
};

export type DataCollectionResponse = {
  job_id?: UUID;
  product_id?: UUID;
  seller_product_ids?: Record<string, UUID>;
  status?: string;
  message?: string;
  scrape_counts?: Record<string, number>;
};

export type AuthResponse = {
  access_token: string;
  refresh_token?: string | null;
  user_id: UUID;
  company_id: UUID;
};

export type AnalysisResponse = {
  session_id: UUID;
  product_id: UUID;
  ingestion_status: string;
  scrape_counts: Record<string, number>;
  total_competitors: number;
  price_range: {
    min?: number | null;
    max?: number | null;
    median?: number | null;
    mean?: number | null;
  };
  recommendation: {
    suggested_price?: number | null;
    strategy: string;
    confidence: number;
    rationale: string;
  };
  competitors: unknown[];
};

export type CompetitorListing = {
  id?: UUID;
  product_id?: UUID;
  marketplace?: string | null;
  seller_name?: string | null;
  price?: string | number | null;
  shipping_price?: string | number | null;
  stock_status?: string | null;
  product_url?: string | null;
  scraped_at?: string | null;
};

export type CompetitorTier = {
  id?: UUID;
  product_id?: UUID;
  seller_name?: string | null;
  marketplace?: string | null;
  tier?: string | null;
  competitor_strength_score?: string | number | null;
  price_aggression_score?: string | number | null;
  buybox_threat_score?: string | number | null;
  rationale?: string | null;
};

export type PriceRecommendation = {
  id: UUID;
  company_id: UUID;
  product_id: UUID;
  seller_product_id: UUID;
  current_price: string | number;
  recommended_price: string | number;
  action: string;
  expected_sales_quantity?: string | number | null;
  expected_profit?: string | number | null;
  profit_uplift?: string | number | null;
  confidence_score?: string | number | null;
  risk_level?: string | null;
  reason_codes?: unknown;
  explanation?: string | null;
  status: string;
  created_at: string;
};

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  token?: string;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");

  if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }

  if (options.token) {
    headers.set("Authorization", `Bearer ${options.token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const errorBody = (await response.json()) as { detail?: unknown };
      detail =
        typeof errorBody.detail === "string"
          ? errorBody.detail
          : JSON.stringify(errorBody.detail ?? errorBody);
    } catch {
      detail = await response.text();
    }
    throw new Error(`${response.status} ${detail}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const pricingApi = {
  baseUrl: API_BASE_URL,
  health: () => request<{ status: string; service: string }>("/health"),
  login: (body: { email: string; password: string }) =>
    request<AuthResponse>("/auth/login", { method: "POST", body }),
  register: (body: {
    email: string;
    password: string;
    full_name: string;
    company_name: string;
  }) => request<AuthResponse>("/auth/register", { method: "POST", body }),
  listCompanies: () => request<Company[]>("/companies"),
  getCompany: (companyId: UUID) => request<Company>(`/companies/${companyId}`),
  createCompany: (body: {
    name: string;
    marketplace_seller_name?: string;
    tax_number?: string;
    website_url?: string;
  }) => request<Company>("/companies", { method: "POST", body }),
  listProducts: () => request<Product[]>("/products"),
  createProduct: (body: {
    name: string;
    brand?: string;
    model?: string;
    category?: string;
    barcode?: string;
    description?: string;
  }) => request<Product>("/products", { method: "POST", body }),
  createSellerProduct: (body: {
    company_id: UUID;
    product_id: UUID;
    marketplace: string;
    marketplace_url?: string;
    marketplace_product_id?: string;
    our_price?: number;
    cost_price?: number;
    stock_quantity?: number;
  }) => request<SellerProduct>("/products/seller-products", { method: "POST", body }),
  listSellerProducts: (companyId: UUID) =>
    request<SellerProduct[]>(`/products/seller-products/company/${companyId}`),
  runDataCollection: (body: { product_id: UUID; marketplaces: string[] }) =>
    request<DataCollectionResponse>("/data-collection/run", {
      method: "POST",
      body,
    }),
  searchAndRunDataCollection: (body: {
    product_id: UUID;
    company_id: UUID;
    query: string;
    marketplaces: string[];
  }) =>
    request<DataCollectionResponse>("/data-collection/search-and-run", {
      method: "POST",
      body,
    }),
  runAnalysis: (body: { product_id: UUID; marketplaces: string[] }) =>
    request<AnalysisResponse>("/analysis/run", { method: "POST", body }),
  runProductAnalysis: (body: {
    product_id: UUID;
    company_id: UUID;
    query: string;
    marketplaces: string[];
  }) => request<AnalysisResponse>("/analysis/search-and-run", { method: "POST", body }),
  listCompetitorListings: (productId: UUID) =>
    request<CompetitorListing[]>(`/competitors/products/${productId}/listings`),
  listCompetitorTiers: (productId: UUID) =>
    request<CompetitorTier[]>(`/competitors/products/${productId}/tiers`),
  listRecommendations: (sellerProductId: UUID) =>
    request<PriceRecommendation[]>(
      `/recommendations/seller-products/${sellerProductId}`,
    ),
  updatePrice: (
    sellerProductId: UUID,
    body: { new_price: number; change_source?: string; recommendation_id?: UUID },
    token?: string,
  ) =>
    request<SellerProduct>(`/products/seller-products/${sellerProductId}/price`, {
      method: "PATCH",
      body,
      token,
    }),
  decideRecommendation: (
    recommendationId: UUID,
    action: "approve" | "reject" | "apply",
    decision_note?: string,
    token?: string,
  ) =>
    request<Record<string, unknown>>(`/recommendations/${recommendationId}/${action}`, {
      method: "POST",
      body: { decision_note },
      token,
    }),
};
