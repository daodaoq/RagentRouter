import { useEffect, useState } from "react";
import {
  Card, Row, Col, Statistic, Table, Tag, Spin, Empty, Typography,
} from "antd";
import { BarChartOutlined } from "@ant-design/icons";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from "recharts";
import { useTranslation } from "react-i18next";
import PageHelp from "../components/PageHelp";

const { Text, Title } = Typography;

interface Overview {
  available: boolean;
  total: { requests: number; input_tokens: number; output_tokens: number; cost_usd: number };
  today: { requests: number; input_tokens: number; output_tokens: number; cost_usd: number };
  month: { requests: number; input_tokens: number; output_tokens: number; cost_usd: number };
}

interface ModelItem {
  model: string;
  requests: number;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
}

interface RecentItem {
  time: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  status_code: number;
  latency_ms: number;
}

interface TrendPoint {
  date: string;
  requests: number;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
}

const API = "http://localhost:8000/api/traffic";

function fmt(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return String(n);
}

export default function TrafficMonitor() {
  const { t } = useTranslation();
  const [overview, setOverview] = useState<Overview | null>(null);
  const [models, setModels] = useState<ModelItem[]>([]);
  const [recent, setRecent] = useState<RecentItem[]>([]);
  const [trend, setTrend] = useState<TrendPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [available, setAvailable] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch(`${API}/overview`).then(r => r.json()),
      fetch(`${API}/by-model`).then(r => r.json()),
      fetch(`${API}/recent?limit=30`).then(r => r.json()),
      fetch(`${API}/daily-trend?days=14`).then(r => r.json()),
    ]).then(([ov, bm, rc, tr]) => {
      setOverview(ov);
      setAvailable(ov.available);
      setModels(bm.items || []);
      setRecent(rc.items || []);
      setTrend(tr.points || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ textAlign: "center", paddingTop: 120 }}><Spin size="large" /></div>;
  if (!available) return <Empty description={t("traffic.noData")} style={{ paddingTop: 120 }} />;

  const modelColumns = [
    { title: t("traffic.model"), dataIndex: "model", key: "model", width: 180,
      render: (m: string) => <Text strong style={{ color: "#374151", fontSize: 13 }}>{m}</Text> },
    { title: t("traffic.requests"), dataIndex: "requests", key: "requests", width: 80,
      render: (v: number) => <Text style={{ color: "#374151" }}>{v}</Text> },
    { title: "Input Tokens", dataIndex: "input_tokens", key: "it", width: 110,
      render: (v: number) => <Text style={{ color: "#6366f1" }}>{fmt(v)}</Text> },
    { title: "Output Tokens", dataIndex: "output_tokens", key: "ot", width: 110,
      render: (v: number) => <Text style={{ color: "#10b981" }}>{fmt(v)}</Text> },
    { title: t("traffic.cost"), dataIndex: "cost_usd", key: "cost", width: 100,
      render: (v: number) => <Text strong style={{ color: "#f59e0b" }}>${v.toFixed(4)}</Text> },
  ];

  const recentColumns = [
    { title: t("traffic.time"), dataIndex: "time", key: "time", width: 140,
      render: (v: string) => <Text style={{ color: "#9ca3af", fontSize: 12 }}>{v.replace("T", " ").substring(0, 16)}</Text> },
    { title: t("traffic.model"), dataIndex: "model", key: "model", width: 170,
      render: (m: string) => <Tag color="purple" style={{ fontSize: 11 }}>{m}</Tag> },
    { title: "In", dataIndex: "input_tokens", key: "in", width: 70,
      render: (v: number) => <Text style={{ color: "#6366f1", fontSize: 12 }}>{fmt(v)}</Text> },
    { title: "Out", dataIndex: "output_tokens", key: "out", width: 70,
      render: (v: number) => <Text style={{ color: "#10b981", fontSize: 12 }}>{fmt(v)}</Text> },
    { title: t("traffic.cost"), dataIndex: "cost_usd", key: "cost", width: 90,
      render: (v: number) => <Text style={{ color: "#f59e0b", fontSize: 12 }}>${v.toFixed(6)}</Text> },
    { title: "Status", dataIndex: "status_code", key: "status", width: 70,
      render: (v: number) => <Tag color={v === 200 ? "green" : "red"} style={{ fontSize: 11 }}>{v}</Tag> },
  ];

  return (
    <div style={{ padding: 20 }}>
      <Title level={4} style={{ color: "#374151", marginBottom: 16 }}>
        <BarChartOutlined style={{ marginRight: 8 }} />
        {t("traffic.title")}
        <PageHelp page="traffic" />
        <Text type="secondary" style={{ fontSize: 12, fontWeight: 400, marginLeft: 12 }}>
          {t("traffic.source")}
        </Text>
      </Title>

      {/* Overview cards */}
      <Row gutter={[16, 16]}>
        {[
          { label: t("traffic.todayRequests"), value: overview?.today.requests ?? 0, color: "#6366f1" },
          { label: t("traffic.todayTokens"), value: ((overview?.today.input_tokens ?? 0) + (overview?.today.output_tokens ?? 0)), color: "#10b981", fmt: true },
          { label: t("traffic.todayCost"), value: overview?.today.cost_usd ?? 0, color: "#f59e0b", prefix: "$", precision: 4 },
          { label: t("traffic.totalCost"), value: overview?.total.cost_usd ?? 0, color: "#374151", prefix: "$", precision: 2 },
          { label: t("traffic.totalRequests"), value: overview?.total.requests ?? 0, color: "#8b5cf6" },
          { label: t("traffic.totalTokens"), value: ((overview?.total.input_tokens ?? 0) + (overview?.total.output_tokens ?? 0)), color: "#06b6d4", fmt: true },
        ].map((card, i) => (
          <Col xs={12} sm={8} lg={4} key={i}>
            <Card bordered={false} style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10 }}>
              <Statistic
                title={<span style={{ color: "#6b7280", fontSize: 11, fontWeight: 500 }}>{card.label}</span>}
                value={card.fmt ? fmt(card.value) : card.value}
                precision={card.precision}
                prefix={card.prefix}
                valueStyle={{ color: card.color, fontSize: 22, fontWeight: 700 }}
              />
            </Card>
          </Col>
        ))}
      </Row>

      {/* Trend chart */}
      <Row style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card
            title={<span style={{ color: "#374151", fontSize: 14, fontWeight: 600 }}>{t("traffic.dailyTrend")}</span>}
            bordered={false}
            style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10 }}
          >
            {trend.length === 0 ? (
              <Text type="secondary">{t("traffic.noTrendData")}</Text>
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <AreaChart data={trend}>
                  <defs>
                    <linearGradient id="trafficGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.15} />
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                  <XAxis dataKey="date" stroke="#9ca3af" fontSize={11} tickLine={false} />
                  <YAxis stroke="#9ca3af" fontSize={11} tickLine={false}
                    tickFormatter={(v: number) => `$${v.toFixed(2)}`} />
                  <Tooltip contentStyle={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 8 }}
                    formatter={(v: any, name: string) => {
                      if (name === "cost_usd") return [`$${Number(v).toFixed(6)}`, t("traffic.cost")];
                      return [fmt(Number(v)), t("traffic.requests")];
                    }} />
                  <Area type="monotone" dataKey="cost_usd" stroke="#6366f1" strokeWidth={2} fill="url(#trafficGrad)" name="cost_usd" />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </Card>
        </Col>
      </Row>

      {/* Model breakdown + Recent requests */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={10}>
          <Card
            title={<span style={{ color: "#374151", fontSize: 14, fontWeight: 600 }}>{t("traffic.byModel")}</span>}
            bordered={false}
            style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, height: "100%" }}
            bodyStyle={{ padding: "4px 0" }}
          >
            <Table dataSource={models} columns={modelColumns} rowKey="model" size="small"
              pagination={false} scroll={{ x: 580 }}
              locale={{ emptyText: t("traffic.noData") }} />
          </Card>
        </Col>
        <Col xs={24} lg={14}>
          <Card
            title={<span style={{ color: "#374151", fontSize: 14, fontWeight: 600 }}>{t("traffic.recentRequests")}</span>}
            bordered={false}
            style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, height: "100%" }}
            bodyStyle={{ padding: "4px 0" }}
          >
            <Table dataSource={recent} columns={recentColumns} rowKey={(r, i) => `${r.time}-${i}`}
              size="small" pagination={{ pageSize: 10, size: "small" }}
              scroll={{ x: 610 }}
              locale={{ emptyText: t("traffic.noData") }} />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
