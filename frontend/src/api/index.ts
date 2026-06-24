const BASE_URL = "http://localhost:8000";

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${url}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Dashboard ─────────────────────────────────────────────────────

export interface CostOverview {
  today_cost: number;
  month_cost: number;
  saved_amount: number;
  saving_rate: number;
  total_requests: number;
}

export interface ModelDistributionItem {
  model: string;
  count: number;
  percentage: number;
}

export interface RecentRouteItem {
  id: string;
  prompt: string;
  model: string;
  provider: string;
  route_reason: string;
  cost_usd: number;
  latency_ms: number;
  created_at: string;
}

export interface CostTrendPoint {
  date: string;
  cost: number;
  requests: number;
}

export const dashboardApi = {
  getOverview: () => request<CostOverview>("/api/dashboard/overview"),
  getModelDistribution: () =>
    request<{ items: ModelDistributionItem[] }>("/api/dashboard/model-distribution"),
  getRecentRoutes: (limit = 20) =>
    request<{ items: RecentRouteItem[] }>(`/api/dashboard/recent-routes?limit=${limit}`),
  getCostTrend: (days = 7) =>
    request<{ points: CostTrendPoint[] }>(`/api/dashboard/cost-trend?days=${days}`),
};

// ── Rules ─────────────────────────────────────────────────────────

export interface RouteRule {
  id: string;
  name: string;
  description: string;
  keywords: string[];
  target_model: string;
  priority: number;
  enabled: boolean;
  created_at: string;
}

export interface RuleCreateInput {
  name: string;
  description?: string;
  keywords?: string[];
  target_model?: string;
  priority?: number;
  enabled?: boolean;
}

export const rulesApi = {
  list: () => request<RouteRule[]>("/api/rules/"),
  create: (data: RuleCreateInput) =>
    request<RouteRule>("/api/rules/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (id: string, data: Partial<RuleCreateInput>) =>
    request<RouteRule>(`/api/rules/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  delete: (id: string) =>
    request<void>(`/api/rules/${id}`, { method: "DELETE" }),
};

// ── Messages (for demo/testing) ───────────────────────────────────

export const messagesApi = {
  send: (content: string, model = "auto") =>
    request<{
      id: string;
      model: string;
      content: { type: string; text: string }[];
      usage: { input_tokens: number; output_tokens: number };
    }>("/v1/messages", {
      method: "POST",
      body: JSON.stringify({
        model,
        messages: [{ role: "user", content }],
        max_tokens: 1024,
      }),
    }),
};
