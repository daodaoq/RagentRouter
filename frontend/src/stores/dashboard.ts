import { create } from "zustand";
import {
  dashboardApi,
  rulesApi,
  messagesApi,
  type CostOverview,
  type ModelDistributionItem,
  type RecentRouteItem,
  type CostTrendPoint,
  type RouteRule,
} from "../api";

interface DashboardState {
  // Data
  overview: CostOverview | null;
  modelDistribution: ModelDistributionItem[];
  recentRoutes: RecentRouteItem[];
  costTrend: CostTrendPoint[];
  rules: RouteRule[];

  // Loading
  loading: boolean;

  // Actions
  fetchAll: () => Promise<void>;
  fetchRules: () => Promise<void>;
  createRule: (data: {
    name: string;
    description?: string;
    keywords?: string[];
    target_model?: string;
    priority?: number;
  }) => Promise<void>;
  deleteRule: (id: string) => Promise<void>;
  sendTestMessage: (content: string) => Promise<{ model: string; text: string } | null>;
}

export const useDashboardStore = create<DashboardState>((set, get) => ({
  overview: null,
  modelDistribution: [],
  recentRoutes: [],
  costTrend: [],
  rules: [],
  loading: false,

  fetchAll: async () => {
    set({ loading: true });
    try {
      const [overview, dist, routes, trend] = await Promise.all([
        dashboardApi.getOverview(),
        dashboardApi.getModelDistribution(),
        dashboardApi.getRecentRoutes(20),
        dashboardApi.getCostTrend(7),
      ]);
      set({
        overview,
        modelDistribution: dist.items,
        recentRoutes: routes.items,
        costTrend: trend.points,
        loading: false,
      });
    } catch (err) {
      console.error("Failed to fetch dashboard data:", err);
      set({ loading: false });
    }
  },

  fetchRules: async () => {
    try {
      const rules = await rulesApi.list();
      set({ rules });
    } catch (err) {
      console.error("Failed to fetch rules:", err);
    }
  },

  createRule: async (data) => {
    try {
      await rulesApi.create({
        name: data.name,
        description: data.description || "",
        keywords: data.keywords || [],
        target_model: data.target_model || "deepseek",
        priority: data.priority || 50,
        enabled: true,
      });
      await get().fetchRules();
    } catch (err) {
      console.error("Failed to create rule:", err);
    }
  },

  deleteRule: async (id) => {
    try {
      await rulesApi.delete(id);
      await get().fetchRules();
    } catch (err) {
      console.error("Failed to delete rule:", err);
    }
  },

  sendTestMessage: async (content) => {
    try {
      const res = await messagesApi.send(content);
      const text = res.content.map((c) => c.text).join("");
      return { model: res.model, text };
    } catch (err) {
      console.error("Failed to send message:", err);
      return null;
    }
  },
}));
