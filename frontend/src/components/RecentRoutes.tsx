import { Card, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useDashboardStore } from "../stores/dashboard";
import type { RecentRouteItem } from "../api";

const { Text } = Typography;

const columns: ColumnsType<RecentRouteItem> = [
  {
    title: "Prompt",
    dataIndex: "prompt",
    key: "prompt",
    ellipsis: true,
    width: 260,
    render: (text: string) => (
      <Text style={{ color: "#ccc", fontSize: 13 }}>{text}</Text>
    ),
  },
  {
    title: "Model",
    dataIndex: "model",
    key: "model",
    width: 160,
    render: (model: string, record: RecentRouteItem) => (
      <Tag
        color={record.provider === "claude" ? "purple" : "green"}
        style={{ fontSize: 12 }}
      >
        {model}
      </Tag>
    ),
  },
  {
    title: "Reason",
    dataIndex: "route_reason",
    key: "route_reason",
    ellipsis: true,
    width: 200,
    render: (text: string) => (
      <Text style={{ color: "#888", fontSize: 12 }}>{text}</Text>
    ),
  },
  {
    title: "Cost",
    dataIndex: "cost_usd",
    key: "cost_usd",
    width: 80,
    render: (val: number) => (
      <Text style={{ color: "#00b894", fontSize: 13 }}>
        ${val.toFixed(4)}
      </Text>
    ),
  },
  {
    title: "Latency",
    dataIndex: "latency_ms",
    key: "latency_ms",
    width: 80,
    render: (val: number) => (
      <Text style={{ color: "#888", fontSize: 13 }}>{val}ms</Text>
    ),
  },
  {
    title: "Time",
    dataIndex: "created_at",
    key: "created_at",
    width: 140,
    render: (val: string) => {
      const d = new Date(val);
      return (
        <Text style={{ color: "#666", fontSize: 12 }}>
          {d.toLocaleString()}
        </Text>
      );
    },
  },
];

export default function RecentRoutes() {
  const { recentRoutes } = useDashboardStore();

  return (
    <Card
      title={
        <span style={{ color: "#ccc", fontSize: 15 }}>Recent Routes</span>
      }
      bordered={false}
      style={{
        background: "linear-gradient(135deg, #141428 0%, #1a1a35 100%)",
        border: "1px solid #2a2a45",
        borderRadius: 10,
        height: "100%",
      }}
      bodyStyle={{ padding: "8px 0" }}
    >
      <Table
        dataSource={recentRoutes}
        columns={columns}
        rowKey="id"
        size="small"
        pagination={{ pageSize: 8, size: "small" }}
        locale={{ emptyText: "No routes yet" }}
        style={{ background: "transparent" }}
        rowClassName={() => "dark-row"}
      />
      <style>{`
        .dark-row td { background: transparent !important; border-bottom: 1px solid #1a1a35 !important; }
        .ant-table { background: transparent !important; color: #ccc !important; }
        .ant-table-thead > tr > th { background: #1a1a35 !important; color: #888 !important; border-bottom: 1px solid #2a2a45 !important; font-size: 12px; }
        .ant-pagination-item a { color: #ccc !important; }
      `}</style>
    </Card>
  );
}
