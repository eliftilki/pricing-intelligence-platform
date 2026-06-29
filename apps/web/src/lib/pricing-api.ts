const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

const AGENT_SERVICE_BASE_URL =
  process.env.NEXT_PUBLIC_AGENT_SERVICE_URL?.replace(/\/$/, "") ||
  "http://localhost:8002";

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
  name?: string | null;
  brand?: string | null;
  model?: string | null;
  category?: string | null;
  color?: string | null;
  connection_type?: string | null;
  storage_capacity?: string | null;
  ram_capacity?: string | null;
  sim_type?: string | null;
  switch_type?: string | null;
  keyboard_layout?: string | null;
  barcode?: string | null;
  description?: string | null;
  created_at: string;
};

export type SellerProduct = {
  id: UUID;
  company_id: UUID;
  product_id: UUID;
  marketplace: string;
  display_name?: string | null;
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

export type SalesQuantityRecord = {
  id: UUID;
  company_id: UUID;
  product_id: UUID;
  seller_product_id: UUID;
  marketplace: string;
  sales_quantity: number;
  sales_date?: string | null;
  note?: string | null;
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
  ingestion_message?: string | null;
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

export type PricingRecommendationResult = {
  product_name?: string | null;
  marketplace?: string | null;
  current_price?: string | number | null;
  recommended_price?: string | number | null;
  action?: string | null;
  expected_sales?: string | number | null;
  unit_profit?: string | number | null;
  expected_profit?: string | number | null;
  profit_uplift?: string | number | null;
  commission_rate?: string | number | null;
  selected_reason?: string | null;
  reason_codes?: string[] | null;
  risk_level?: string | null;
  competitor_min_price?: string | number | null;
  competitor_avg_price?: string | number | null;
  tier1_min_price?: string | number | null;
};

export type PricingIntelligenceResponse = {
  product_id: UUID;
  status: "SUCCESS" | "PARTIAL_SUCCESS" | "FAILED" | string;
  error_code?: string | null;
  failed_stage?: string | null;
  analyzed_count: number;
  inserted_count: number;
  message: string;
  ingestion_result?: {
    job_id?: UUID;
    status?: string;
    message?: string;
    scrape_counts?: Record<string, number>;
  } | null;
  warnings: string[];
  candidate_prices?: number[] | null;
  selected_candidate_strategy?: string | null;
  optimization_result?: Record<string, unknown> | null;
  marketplace_recommendations?: Array<Record<string, unknown>> | null;
  recommendation?: PricingRecommendationResult | null;
  recommendation_persistence?: {
    status?: string;
    recommendation_id?: UUID;
    message?: string;
  } | null;
  slm_explanation?: {
    explanation?: string;
    model_name?: string;
  } | null;
  pipeline_summary?: {
    outcome?: string;
    completed_stages?: string[];
    failed_stage?: string | null;
    warning_count?: number;
    error_count?: number;
  } | null;
  errors: string[];
};

export type CompetitorListing = {
  id?: UUID;
  product_id?: UUID;
  marketplace?: string | null;
  rank?: number | null;
  seller_name?: string | null;
  seller_score?: string | number | null;
  price?: string | number | null;
  shipping_price?: string | number | null;
  stock_status?: string | null;
  is_in_stock?: boolean | null;
  fast_shipping?: boolean | null;
  free_shipping?: boolean | null;
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
  reason_codes?: string[] | string | null;
  analyzed_at?: string | null;
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

function formatApiError(status: number, detail: string) {
  const trimmedDetail = detail.trim();
  const productConflictMessages = [
    "This product already exists for the selected marketplace.",
    "Bu ürün seçtiğiniz pazaryerinde zaten şirket listenizde var.",
  ];

  if (
    status === 409 &&
    productConflictMessages.some((message) => trimmedDetail.includes(message))
  ) {
    return (
      "Bu ürün seçtiğiniz pazaryerinde zaten şirket listenizde var. " +
      "Mevcut ürünü düzenleyebilir veya farklı bir pazaryeri seçebilirsiniz."
    );
  }

  return trimmedDetail || `İşlem tamamlanamadı. Lütfen tekrar deneyin.`;
}

async function requestFrom<T>(
  baseUrl: string,
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");

  if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }

  if (options.token) {
    headers.set("Authorization", `Bearer ${options.token}`);
  }

  const response = await fetch(`${baseUrl}${path}`, {
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
    throw new Error(formatApiError(response.status, detail));
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  return requestFrom<T>(API_BASE_URL, path, options);
}

export const pricingApi = {
  baseUrl: API_BASE_URL,
  agentServiceBaseUrl: AGENT_SERVICE_BASE_URL,
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
    name?: string;
    brand?: string;
    model?: string;
    category?: string;
    color?: string;
    connection_type?: string | null;
    storage_capacity?: string | null;
    ram_capacity?: string | null;
    sim_type?: string | null;
    switch_type?: string | null;
    keyboard_layout?: string | null;
    barcode?: string;
    description?: string;
  }) => request<Product>("/products", { method: "POST", body }),
  createSellerProduct: (body: {
    company_id: UUID;
    product_id: UUID;
    marketplace: string;
    display_name?: string;
    marketplace_url?: string;
    marketplace_product_id?: string;
    our_price?: number;
    cost_price?: number;
    stock_quantity?: number;
  }) => request<SellerProduct>("/products/seller-products", { method: "POST", body }),
  listSellerProducts: (companyId: UUID) =>
    request<SellerProduct[]>(`/products/seller-products/company/${companyId}`),
  updateCompanyProduct: (
    companyId: UUID,
    productId: UUID,
    body: {
      name?: string;
      brand?: string;
      model?: string;
      category?: string;
      color?: string;
      connection_type?: string | null;
      storage_capacity?: string | null;
      ram_capacity?: string | null;
      sim_type?: string | null;
      switch_type?: string | null;
      keyboard_layout?: string | null;
      display_name?: string;
      our_price?: number;
      cost_price?: number;
      stock_quantity?: number;
    },
  ) =>
    request<SellerProduct[]>(
      `/products/company-products/${companyId}/${productId}`,
      { method: "PATCH", body },
    ),
  deleteCompanyProduct: (companyId: UUID, productId: UUID) =>
    request<{ status: string; product_id: UUID }>(
      `/products/company-products/${companyId}/${productId}`,
      { method: "DELETE" },
    ),
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
  runAnalysis: (body: {
    product_id: UUID;
    company_id?: UUID;
    query?: string;
    marketplaces: string[];
  }) =>
    request<AnalysisResponse>("/analysis/run", { method: "POST", body }),
  runPricingIntelligence: (body: {
    product_id: UUID;
    seller_product_id: UUID;
    ingestion_marketplaces: string[];
    ingestion_query?: string;
    ingestion_company_id?: UUID;
    run_candidate_prices?: boolean;
    run_optimization?: boolean;
    persist_optimization?: boolean;
    sales_7d_avg?: number;
  }) =>
    requestFrom<PricingIntelligenceResponse>(
      AGENT_SERVICE_BASE_URL,
      "/pricing-intelligence/run",
      { method: "POST", body },
    ),
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
  recordSalesQuantity: (
    sellerProductId: UUID,
    body: { sales_quantity: number; sales_date?: string; note?: string },
  ) =>
    request<SalesQuantityRecord>(
      `/products/seller-products/${sellerProductId}/sales`,
      { method: "POST", body },
    ),
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
