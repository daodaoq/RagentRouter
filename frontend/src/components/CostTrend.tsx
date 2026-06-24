import { Card, Typography } from "antd";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
} from "recharts";
import { useDashboardStore } from "../stores/dashboard";

const { Text } = Typography;

export default function CostTrend() {
  const { costTrend } = useDashboardStore();

  const maxCost = Math.max(...costTrend.map((p) => p.cost), 0.01);

  return (
    <Card
      title={
        <span style={{ color: "#ccc", fontSize: 15 }}>Cost Trend (7 days)</span>
      }
      bordered={false}
      style={{
        background: "linear-gradient(135deg, #141428 0%, #1a1a35 100%)",
        border: "1px solid #2a2a45",
        borderRadius: 10,
      }}
    >
      {costTrend.length === 0 ? (
        <Text type="secondary">No data yet</Text>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={costTrend}>
            <defs>
              <linearGradient id="costGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6c5ce7" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#6c5ce7" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1a1a35" />
            <XAxis
              dataKey="date"
              stroke="#666"
              fontSize={12}
              tickLine={false}
            />
            <YAxis
              stroke="#666"
              fontSize={12}
              tickLine={false}
              domain={[0, Math.ceil(maxCost * 1.2 * 100) / 100]}
              tickFormatter={(v: number) => `$${v.toFixed(2)}`}
            />
            <Tooltip
              contentStyle={{
                background: "#1a1a35",
                border: "1px solid #2a2a45",
                borderRadius: 8,
                color: "#ccc",
              }}
              formatter={(value: number, name: string) => {
                if (name === "cost") return [`$${value.toFixed(4)}`, "Cost"];
                return [value, "Requests"];
              }}
              labelFormatter={(label: string) => `Date: ${label}`}
            />
            <Area
              type="monotone"
              dataKey="cost"
              stroke="#6c5ce7"
              strokeWidth={2}
              fill="url(#costGradient)"
              name="cost"
            />
            <Line
              type="monotone"
              dataKey="requests"
              stroke="#00b894"
              strokeWidth={1.5}
              strokeDasharray="4 4"
              dot={{ r: 3, fill: "#00b894" }}
              name="requests"
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </Card>
  );
}
