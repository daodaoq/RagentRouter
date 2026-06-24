import { Card, Typography } from "antd";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { useDashboardStore } from "../stores/dashboard";

const { Text } = Typography;

const COLORS: Record<string, string> = {
  "claude-sonnet-4-6": "#6c5ce7",
  "deepseek-chat": "#00b894",
  "gpt-4o": "#74b9ff",
  claude: "#6c5ce7",
  deepseek: "#00b894",
};

export default function ModelDistribution() {
  const { modelDistribution } = useDashboardStore();

  const data = modelDistribution.map((item) => ({
    name: item.model,
    value: item.count,
    color: COLORS[item.model] || COLORS[item.model.split("-")[0]] || "#636e72",
  }));

  return (
    <Card
      title={<span style={{ color: "#ccc", fontSize: 15 }}>Model Distribution</span>}
      bordered={false}
      style={{
        background: "linear-gradient(135deg, #141428 0%, #1a1a35 100%)",
        border: "1px solid #2a2a45",
        borderRadius: 10,
        height: "100%",
      }}
      bodyStyle={{ paddingBottom: 8 }}
    >
      {data.length === 0 ? (
        <Text type="secondary">No data yet</Text>
      ) : (
        <ResponsiveContainer width="100%" height={260}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={55}
              outerRadius={90}
              paddingAngle={4}
              dataKey="value"
              stroke="none"
            >
              {data.map((entry, i) => (
                <Cell key={i} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                background: "#1a1a35",
                border: "1px solid #2a2a45",
                borderRadius: 8,
                color: "#ccc",
              }}
              formatter={(value: number, name: string) => [`${value} requests`, name]}
            />
            <Legend
              wrapperStyle={{ color: "#888", fontSize: 12 }}
              formatter={(value: string, entry: any) => {
                const pct = modelDistribution.find((d) => d.model === value);
                return `${value} (${pct?.percentage ?? 0}%)`;
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      )}
    </Card>
  );
}
