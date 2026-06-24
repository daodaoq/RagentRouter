import { useEffect, useState, useCallback } from "react";
import {
  Card, Row, Col, Statistic, Table, Tag, Spin, Empty, Typography, Switch,
} from "antd";
import {
  BarChartOutlined, ReloadOutlined, WarningOutlined,
  ThunderboltOutlined, ClockCircleOutlined,
} from "@ant-design/icons";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ComposedChart, Bar, Legend,
} from "recharts";
import { useTranslation } from "react-i18next";
import PageHelp from "../components/PageHelp";

const { Text, Title } = Typography;

interface Overview {
  available: boolean;
  total: { requests: number; input_tokens: number; output_tokens: number; cache_read_tokens: number; cost_usd: number };
  today: { requests: number; input_tokens: number; output_tokens: number; cache_read_tokens: number; cost_usd: number };
  month: { requests: number; input_tokens: number; output_tokens: number; cache_read_tokens: number; cost_usd: number };
}

interface ModelItem {
  model: string;
  requests: number;
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
  cost_usd: number;
}

interface RecentItem {
  time: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
  cost_usd: number;
  status_code: number;
  latency_ms: number;
}

interface TrendPoint {
  date: string;
  requests: number;
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
  cost_usd: number;
}

interface ErrorStats {
  available: boolean;
  hours: number;
  total: number;
  errors: number;
  error_rate: number;
  by_status: { status_code: number; count: number }[];
}

interface LatencyItem {
  model: string;
  requests: number;
  avg_ms: number;
  min_ms: number;
  max_ms: number;
}

const API = "http://localhost:15722/api/traffic";
const REFRESH_MS = 30_000; // 30s auto-refresh

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
  const [errors, setErrors] = useState<ErrorStats | null>(null);
  const [latency, setLatency] = useState<LatencyItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [available, setAvailable] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchAll = useCallback(() => {
    Promise.all([
      fetch(`${API}/overview`).then(r => r.json()),
      fetch(`${API}/by-model`).then(r => r.json()),
      fetch(`${API}/recent?limit=50`).then(r => r.json()),
      fetch(`${API}/daily-trend?days=14`).then(r => r.json()),
      fetch(`${API}/errors?hours=24`).then(r => r.json()),
      fetch(`${API}/latency?hours=24`).then(r => r.json()),
    ]).then(([ov, bm, rc, tr, er, la]) => {
      setOverview(ov);
      setAvailable(ov.available);
      setModels(bm.items || []);
      setRecent(rc.items || []);
      setTrend(tr.points || []);
      setErrors(er);
      setLatency((la.items || []).filter((i: LatencyItem) => i.requests > 0));
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchAll();
    if (!autoRefresh) return;
    const interval = setInterval(fetchAll, REFRESH_MS);
    return () => clearInterval(interval);
  }, [fetchAll, autoRefresh]);

  if (loading) return <div style={{ textAlign: "center", paddingTop: 120 }}><Spin size="large" /></div>;
  if (!available) return <Empty description={t("traffic.noData")} style={{ paddingTop: 120 }} />;

  const cacheToday = overview?.today.cache_read_tokens ?? 0;
  const cacheTotal = overview?.total.cache_read_tokens ?? 0;
  const todayInput = overview?.today.input_tokens ?? 0;
  const cacheHitToday = todayInput > 0
    ? (cacheToday / todayInput * 100).toFixed(1)
    : "0";

  const modelColumns = [
    { title: t("traffic.model"), dataIndex: "model", key: "model", width: 160,
      render: (m: string) => <Text strong style={{ color: "#374151", fontSize: 13 }}>{m}</Text> },
    { title: t("traffic.requests"), dataIndex: "requests", key: "requests", width: 70,
      render: (v: number) => <Text style={{ color: "#374151" }}>{v}</Text> },
    { title: "Input", dataIndex: "input_tokens", key: "it", width: 90,
      render: (v: number) => <Text style={{ color: "#6366f1" }}>{fmt(v)}</Text> },
    { title: "Output", dataIndex: "output_tokens", key: "ot", width: 90,
      render: (v: number) => <Text style={{ color: "#10b981" }}>{fmt(v)}</Text> },
    { title: t("traffic.cacheHit"), dataIndex: "cache_read_tokens", key: "crt", width: 85,
      render: (v: number) => <Text style={{ color: v > 0 ? "#8b5cf6" : "#d1d5db" }}>{v > 0 ? fmt(v) : "—"}</Text> },
    { title: t("traffic.cost"), dataIndex: "cost_usd", key: "cost", width: 90,
      render: (v: number) => <Text strong style={{ color: "#f59e0b" }}>${v.toFixed(4)}</Text> },
  ];

  const recentColumns = [
    { title: t("traffic.time"), dataIndex: "time", key: "time", width: 135,
      render: (v: string) => <Text style={{ color: "#9ca3af", fontSize: 12 }}>{v.substring(0, 16)}</Text> },
    { title: t("traffic.model"), dataIndex: "model", key: "model", width: 150,
      render: (m: string) => <Tag color="purple" style={{ fontSize: 11 }}>{m}</Tag> },
    { title: "In", dataIndex: "input_tokens", key: "in", width: 60,
      render: (v: number) => <Text style={{ color: "#6366f1", fontSize: 12 }}>{fmt(v)}</Text> },
    { title: "Out", dataIndex: "output_tokens", key: "out", width: 60,
      render: (v: number) => <Text style={{ color: "#10b981", fontSize: 12 }}>{fmt(v)}</Text> },
    { title: t("traffic.cost"), dataIndex: "cost_usd", key: "cost", width: 85,
      render: (v: number) => <Text style={{ color: "#f59e0b", fontSize: 12 }}>${v.toFixed(6)}</Text> },
    { title: t("traffic.latency"), dataIndex: "latency_ms", key: "lat", width: 70,
      render: (v: number) => <Text style={{ color: "#6b7280", fontSize: 12 }}>{v ? `${v}ms` : "—"}</Text> },
    { title: "Status", dataIndex: "status_code", key: "status", width: 65,
      render: (v: number) => <Tag color={v === 200 ? "green" : "red"} style={{ fontSize: 11 }}>{v}</Tag> },
  ];

  const latencyColumns = [
    { title: t("traffic.model"), dataIndex: "model", key: "model", width: 140,
      render: (m: string) => <Text style={{ color: "#374151", fontSize: 12 }}>{m}</Text> },
    { title: t("traffic.requests"), dataIndex: "requests", key: "requests", width: 65,
      render: (v: number) => <Text style={{ color: "#374151", fontSize: 12 }}>{v}</Text> },
    { title: t("traffic.avgLatency"), dataIndex: "avg_ms", key: "avg", width: 80,
      render: (v: number) => <Text strong style={{ color: "#6366f1", fontSize: 12 }}>{v}ms</Text> },
    { title: t("traffic.minLatency"), dataIndex: "min_ms", key: "min", width: 70,
      render: (v: number) => <Text style={{ color: "#10b981", fontSize: 12 }}>{v}ms</Text> },
    { title: t("traffic.maxLatency"), dataIndex: "max_ms", key: "max", width: 75,
      render: (v: number) => <Text style={{ color: v > 5000 ? "#ef4444" : "#f59e0b", fontSize: 12 }}>{v}ms</Text> },
  ];

  return (
    <div style={{ padding: 20 }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={4} style={{ color: "#374151", margin: 0 }}>
          <BarChartOutlined style={{ marginRight: 8 }} />
          {t("traffic.title")}
          <PageHelp page="traffic" />
          <Text type="secondary" style={{ fontSize: 12, fontWeight: 400, marginLeft: 12 }}>
            {t("traffic.source")}
          </Text>
        </Title>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Text style={{ fontSize: 11, color: "#9ca3af" }}>
            {t("traffic.autoRefresh")}
          </Text>
          <Switch size="small" checked={autoRefresh} onChange={setAutoRefresh} />
          <ReloadOutlined
            style={{ color: "#6366f1", cursor: "pointer", fontSize: 16 }}
            onClick={fetchAll}
            title={t("traffic.refresh") || "Refresh"}
          />
        </div>
      </div>

      {/* Overview cards */}
      <Row gutter={[12, 12]}>
        {[
          { label: t("traffic.todayRequests"), value: overview?.today.requests ?? 0, color: "#6366f1" },
          { label: t("traffic.todayTokens"), value: ((overview?.today.input_tokens ?? 0) + (overview?.today.output_tokens ?? 0)), color: "#10b981", fmt: true },
          { label: t("traffic.todayCost"), value: overview?.today.cost_usd ?? 0, color: "#f59e0b", prefix: "$", precision: 4 },
          { label: t("traffic.cacheHit"), value: cacheToday, color: "#8b5cf6", fmt: true,
            extra: cacheToday > 0 ? `${cacheHitToday}%` : undefined },
          { label: t("traffic.totalCost"), value: overview?.total.cost_usd ?? 0, color: "#374151", prefix: "$", precision: 2 },
          { label: t("traffic.totalRequests"), value: overview?.total.requests ?? 0, color: "#8b5cf6" },
          { label: t("traffic.totalTokens"), value: ((overview?.total.input_tokens ?? 0) + (overview?.total.output_tokens ?? 0)), color: "#06b6d4", fmt: true },
          { label: t("traffic.totalCacheHit"), value: cacheTotal, color: "#a78bfa", fmt: true },
        ].map((card, i) => (
          <Col xs={12} sm={8} md={6} lg={3} key={i}>
            <Card bordered={false} style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10 }}>
              <Statistic
                title={<span style={{ color: "#6b7280", fontSize: 11, fontWeight: 500 }}>{card.label}</span>}
                value={card.fmt ? fmt(card.value) : card.value}
                precision={card.precision}
                prefix={card.prefix}
                suffix={card.extra ? <Text style={{ fontSize: 10, color: "#8b5cf6" }}>{card.extra}</Text> : undefined}
                valueStyle={{ color: card.color, fontSize: 20, fontWeight: 700 }}
              />
            </Card>
          </Col>
        ))}
      </Row>

      {/* Error rate alert */}
      {errors && errors.error_rate > 0 && (
        <Card
          bordered={false}
          style={{
            marginTop: 12, background: errors.error_rate > 5 ? "#fef2f2" : "#fffbeb",
            border: errors.error_rate > 5 ? "1px solid #fecaca" : "1px solid #fde68a",
            borderRadius: 10,
          }}
          bodyStyle={{ padding: "10px 16px" }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <WarningOutlined style={{ color: errors.error_rate > 5 ? "#ef4444" : "#f59e0b", fontSize: 16 }} />
            <Text strong style={{ color: "#374151", fontSize: 13 }}>
              {t("traffic.errorRate")}: {errors.error_rate}% ({errors.errors}/{errors.total})
            </Text>
            <Text style={{ color: "#6b7280", fontSize: 12 }}>
              {t("traffic.lastHours", { hours: errors.hours })}
            </Text>
            {errors.by_status.map(s => (
              <Tag key={s.status_code} color={s.status_code === 200 ? "green" : "red"} style={{ fontSize: 11 }}>
                {s.status_code}: {s.count}
              </Tag>
            ))}
          </div>
        </Card>
      )}

      {/* Trend chart */}
      <Row style={{ marginTop: 12 }}>
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
                <ComposedChart data={trend}>
                  <defs>
                    <linearGradient id="trafficGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.15} />
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="tokenGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.15} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                  <XAxis dataKey="date" stroke="#9ca3af" fontSize={11} tickLine={false} />
                  <YAxis yAxisId="left" stroke="#9ca3af" fontSize={11} tickLine={false}
                    tickFormatter={(v: number) => `$${v.toFixed(2)}`} />
                  <YAxis yAxisId="right" orientation="right" stroke="#9ca3af" fontSize={11} tickLine={false}
                    tickFormatter={(v: number) => fmt(v)} />
                  <Tooltip contentStyle={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 8 }}
                    formatter={(v: any, name: string) => {
                      if (name === "cost_usd") return [`$${Number(v).toFixed(6)}`, t("traffic.cost")];
                      if (name === "tokens") return [fmt(Number(v)), "Tokens"];
                      return [fmt(Number(v)), t("traffic.requests")];
                    }} />
                  <Legend />
                  <Bar yAxisId="right" dataKey="requests" fill="#e5e7eb" radius={[4, 4, 0, 0]} name={t("traffic.requests")} />
                  <Area yAxisId="left" type="monotone" dataKey="cost_usd" stroke="#6366f1" strokeWidth={2}
                    fill="url(#trafficGrad)" name="cost_usd" />
                </ComposedChart>
              </ResponsiveContainer>
            )}
          </Card>
        </Col>
      </Row>

      {/* Model breakdown + Recent requests */}
      <Row gutter={[12, 12]} style={{ marginTop: 12 }}>
        <Col xs={24} lg={10}>
          <Card
            title={<span style={{ color: "#374151", fontSize: 14, fontWeight: 600 }}>{t("traffic.byModel")}</span>}
            bordered={false}
            style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, height: "100%" }}
            bodyStyle={{ padding: "4px 0" }}
          >
            <Table dataSource={models} columns={modelColumns} rowKey="model" size="small"
              pagination={false} scroll={{ x: 560 }}
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
              size="small" pagination={{ pageSize: 15, size: "small" }}
              scroll={{ x: 620 }}
              locale={{ emptyText: t("traffic.noData") }} />
          </Card>
        </Col>
      </Row>

      {/* Latency stats */}
      {latency.length > 0 && (
        <Row style={{ marginTop: 12 }}>
          <Col span={24}>
            <Card
              title={
                <span style={{ color: "#374151", fontSize: 14, fontWeight: 600 }}>
                  <ClockCircleOutlined style={{ marginRight: 6 }} />
                  {t("traffic.latencyStats")} (24h)
                </span>
              }
              bordered={false}
              style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10 }}
              bodyStyle={{ padding: "4px 0" }}
            >
              <Table dataSource={latency} columns={latencyColumns} rowKey="model"
                size="small" pagination={false} scroll={{ x: 430 }}
                locale={{ emptyText: t("traffic.noData") }} />
            </Card>
          </Col>
        </Row>
      )}
    </div>
  );
}
