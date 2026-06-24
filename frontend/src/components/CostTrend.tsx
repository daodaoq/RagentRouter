import { Card, Typography } from "antd";
import { useTranslation } from "react-i18next";
import { AreaChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { useDashboardStore } from "../stores/dashboard";

const { Text } = Typography;

export default function CostTrend() {
  const { t } = useTranslation();
  const { costTrend } = useDashboardStore();
  const maxCost = Math.max(...costTrend.map((p) => p.cost), 0.01);

  return (
    <Card
      title={<span style={{ color: "#374151", fontSize: 14, fontWeight: 600 }}>{t("dashboard.costTrend")}</span>}
      bordered={false}
      style={{
        background: "#ffffff",
        border: "1px solid #e5e7eb",
        borderRadius: 10,
      }}
    >
      {costTrend.length === 0 ? (
        <Text type="secondary">{t("dashboard.noDataYet")}</Text>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={costTrend}>
            <defs>
              <linearGradient id="costGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
            <XAxis dataKey="date" stroke="#9ca3af" fontSize={12} tickLine={false} />
            <YAxis
              stroke="#9ca3af"
              fontSize={12}
              tickLine={false}
              domain={[0, Math.ceil(maxCost * 1.2 * 100) / 100]}
              tickFormatter={(v: number) => `$${v.toFixed(2)}`}
            />
            <Tooltip
              contentStyle={{
                background: "#fff",
                border: "1px solid #e5e7eb",
                borderRadius: 8,
                color: "#374151",
              }}
              formatter={(value: number, name: string) => {
                if (name === "cost") return [`$${value.toFixed(4)}`, t("dashboard.costAxis") as string];
                return [value, t("dashboard.requests") as string];
              }}
              labelFormatter={(label: string) => `${t("dashboard.date")}: ${label}`}
            />
            <Area type="monotone" dataKey="cost" stroke="#6366f1" strokeWidth={2} fill="url(#costGradient)" name="cost" />
            <Line type="monotone" dataKey="requests" stroke="#10b981" strokeWidth={1.5} strokeDasharray="4 4" dot={{ r: 3, fill: "#10b981" }} name="requests" />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </Card>
  );
}
