import { Card, Table, Tag, Typography } from "antd";
import { useTranslation } from "react-i18next";
import type { ColumnsType } from "antd/es/table";
import { useDashboardStore } from "../stores/dashboard";
import type { RecentRouteItem } from "../api";

const { Text } = Typography;

export default function RecentRoutes() {
  const { t } = useTranslation();
  const { recentRoutes } = useDashboardStore();

  const columns: ColumnsType<RecentRouteItem> = [
    {
      title: t("dashboard.prompt"),
      dataIndex: "prompt",
      key: "prompt",
      ellipsis: true,
      width: 240,
      render: (text: string) => <Text style={{ color: "#374151", fontSize: 13 }}>{text}</Text>,
    },
    {
      title: t("dashboard.model"),
      dataIndex: "model",
      key: "model",
      width: 150,
      render: (model: string, record: RecentRouteItem) => (
        <Tag color={record.provider === "claude" ? "purple" : "green"} style={{ fontSize: 12 }}>
          {model}
        </Tag>
      ),
    },
    {
      title: t("dashboard.reason"),
      dataIndex: "route_reason",
      key: "route_reason",
      ellipsis: true,
      width: 180,
      render: (text: string) => <Text style={{ color: "#6b7280", fontSize: 12 }}>{text}</Text>,
    },
    {
      title: t("dashboard.cost"),
      dataIndex: "cost_usd",
      key: "cost_usd",
      width: 80,
      render: (val: number) => <Text style={{ color: "#10b981", fontSize: 13 }}>${val.toFixed(4)}</Text>,
    },
    {
      title: t("dashboard.latency"),
      dataIndex: "latency_ms",
      key: "latency_ms",
      width: 80,
      render: (val: number) => <Text style={{ color: "#6b7280", fontSize: 13 }}>{val}ms</Text>,
    },
    {
      title: t("dashboard.time"),
      dataIndex: "created_at",
      key: "created_at",
      width: 140,
      render: (val: string) => (
        <Text style={{ color: "#9ca3af", fontSize: 12 }}>{new Date(val).toLocaleString()}</Text>
      ),
    },
  ];

  return (
    <Card
      title={<span style={{ color: "#374151", fontSize: 14, fontWeight: 600 }}>{t("dashboard.recentRoutes")}</span>}
      bordered={false}
      style={{
        background: "#ffffff",
        border: "1px solid #e5e7eb",
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
        scroll={{ x: 880 }}
        pagination={{ pageSize: 8, size: "small" }}
        locale={{ emptyText: t("dashboard.noRoutes") }}
      />
    </Card>
  );
}
