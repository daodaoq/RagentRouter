import { useEffect, useState } from "react";
import { Card, Tag, Typography, Spin, Empty, Row, Col, Tooltip, Button, message } from "antd";
import {
  ApiOutlined,
  LinkOutlined,
  CheckCircleFilled,
  StarFilled,
  ThunderboltOutlined,
} from "@ant-design/icons";
import { useTranslation } from "react-i18next";

const { Text, Title } = Typography;

interface Endpoint {
  app_type: string;
  url: string;
}

interface Provider {
  id: string;
  app_type: string;
  name: string;
  category: string;
  is_current: boolean;
  endpoints: Endpoint[];
  cost_multiplier: string;
  icon_color: string;
  limit_daily_usd: string | null;
  limit_monthly_usd: string | null;
}

const CATEGORY_LABELS: Record<string, { en: string; zh: string; color: string }> = {
  official: { en: "Official", zh: "官方", color: "blue" },
  cn_official: { en: "CN Official", zh: "国内官方", color: "orange" },
  custom: { en: "Custom", zh: "自定义", color: "default" },
};

const APP_TYPE_LABELS: Record<string, string> = {
  claude: "Claude",
  codex: "OpenAI",
  gemini: "Gemini",
};

export default function Providers() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language.startsWith("zh") ? "zh" : "en";
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [dbStatus, setDbStatus] = useState<{ available: boolean; path: string; db_size_mb: number } | null>(null);
  const [activating, setActivating] = useState<string | null>(null);

  const handleActivate = async (provider: Provider) => {
    if (provider.is_current) return;
    setActivating(provider.id);
    try {
      const res = await fetch(`http://localhost:8000/api/ccswitch/activate/${provider.id}`, {
        method: "POST",
      });
      const data = await res.json();
      if (data.success) {
        message.success(
          lang === "zh"
            ? `已切换到 ${data.provider_name}${data.note ? "（CC Switch 可能需要重启）" : ""}`
            : `Switched to ${data.provider_name}${data.note ? " (CC Switch may need restart)" : ""}`
        );
        // Refresh provider list
        fetch("http://localhost:8000/api/ccswitch/providers")
          .then((r) => r.json())
          .then((d) => setProviders((d.items || []).filter((p: Provider) => p.name !== "default")));
      } else {
        message.error(data.error || "Failed");
      }
    } catch {
      message.error(lang === "zh" ? "切换失败" : "Activation failed");
    }
    setActivating(null);
  };

  useEffect(() => {
    fetch("http://localhost:8000/api/ccswitch/providers")
      .then((r) => r.json())
      .then((data) => {
        // Filter out internal "default" providers
        const filtered = (data.items || []).filter(
          (p: Provider) => p.name !== "default"
        );
        setProviders(filtered);
        setDbStatus({ available: data.source !== "not_found", path: data.source, db_size_mb: 0 });
        setLoading(false);
      })
      .catch(() => setLoading(false));

    fetch("http://localhost:8000/api/ccswitch/status")
      .then((r) => r.json())
      .then(setDbStatus)
      .catch(() => {});
  }, []);

  if (loading) {
    return (
      <div style={{ textAlign: "center", paddingTop: 120 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!dbStatus?.available) {
    return (
      <Empty
        description={lang === "zh" ? "未检测到 CC Switch 数据库" : "CC Switch database not found"}
        style={{ paddingTop: 120 }}
      />
    );
  }

  return (
    <div style={{ padding: 20 }}>
      <div style={{ marginBottom: 20 }}>
        <Title level={4} style={{ color: "#374151", marginBottom: 4 }}>
          <ApiOutlined style={{ marginRight: 8 }} />
          {lang === "zh" ? "API 供应商" : "API Providers"}
        </Title>
        <Text type="secondary" style={{ fontSize: 12 }}>
          {lang === "zh" ? "数据来源: CC Switch 本地数据库" : "Data source: CC Switch local database"}
          <Text code style={{ fontSize: 11, marginLeft: 8 }}>{dbStatus.path}</Text>
        </Text>
      </div>

      <Row gutter={[16, 16]}>
        {providers.map((p) => {
          const cat = CATEGORY_LABELS[p.category] || { en: p.category, zh: p.category, color: "default" };
          const appLabel = APP_TYPE_LABELS[p.app_type] || p.app_type;
          const color = p.icon_color || "#6366f1";

          return (
            <Col xs={24} sm={12} lg={8} key={p.id}>
              <Card
                bordered={false}
                style={{
                  background: "#fff",
                  border: p.is_current ? "2px solid #6366f1" : "1px solid #e5e7eb",
                  borderRadius: 10,
                  height: "100%",
                }}
                bodyStyle={{ padding: "20px 20px 16px" }}
              >
                {/* Header */}
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
                  <div
                    style={{
                      width: 36,
                      height: 36,
                      borderRadius: 8,
                      background: color,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "#fff",
                      fontSize: 16,
                      fontWeight: 700,
                      flexShrink: 0,
                    }}
                  >
                    {p.name.charAt(0)}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <Text strong style={{ color: "#374151", fontSize: 14 }}>
                        {p.name}
                      </Text>
                      {p.is_current && (
                        <Tooltip title={lang === "zh" ? "当前使用" : "Currently active"}>
                          <StarFilled style={{ color: "#f59e0b", fontSize: 12 }} />
                        </Tooltip>
                      )}
                    </div>
                    <div style={{ display: "flex", gap: 6, marginTop: 4 }}>
                      <Tag style={{ fontSize: 10, lineHeight: "16px" }}>{appLabel}</Tag>
                      <Tag color={cat.color} style={{ fontSize: 10, lineHeight: "16px" }}>
                        {cat[lang]}
                      </Tag>
                    </div>
                  </div>
                </div>

                {/* Endpoints */}
                {p.endpoints.length > 0 && (
                  <div
                    style={{
                      background: "#f9fafb",
                      borderRadius: 6,
                      padding: "8px 10px",
                      marginBottom: 12,
                    }}
                  >
                    {p.endpoints.map((ep, i) => (
                      <div
                        key={i}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 6,
                          padding: "3px 0",
                          fontSize: 11,
                        }}
                      >
                        <LinkOutlined style={{ color: "#9ca3af", fontSize: 10 }} />
                        <Text
                          style={{ color: "#6b7280", fontSize: 11, fontFamily: "monospace" }}
                          ellipsis
                        >
                          {ep.url}
                        </Text>
                      </div>
                    ))}
                  </div>
                )}

                {/* Footer metadata + Activate */}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-end",
                    flexWrap: "wrap",
                    gap: 8,
                  }}
                >
                  <div style={{ fontSize: 11, color: "#9ca3af" }}>
                    <span>
                      {lang === "zh" ? "倍率" : "Multiplier"}: {p.cost_multiplier || "1.0"}x
                    </span>
                    {p.limit_daily_usd && (
                      <span style={{ marginLeft: 12 }}>
                        {lang === "zh" ? "日限额" : "Daily"}: ${p.limit_daily_usd}
                      </span>
                    )}
                    {p.limit_monthly_usd && (
                      <span style={{ marginLeft: 12 }}>
                        {lang === "zh" ? "月限额" : "Monthly"}: ${p.limit_monthly_usd}
                      </span>
                    )}
                  </div>

                  {p.is_current ? (
                    <Tag color="success" style={{ fontSize: 11, margin: 0 }}>
                      <CheckCircleFilled style={{ marginRight: 4 }} />
                      {lang === "zh" ? "当前使用中" : "Active"}
                    </Tag>
                  ) : (
                    <Button
                      type="primary"
                      size="small"
                      icon={<ThunderboltOutlined />}
                      loading={activating === p.id}
                      onClick={() => handleActivate(p)}
                      style={{ fontSize: 11 }}
                    >
                      {lang === "zh" ? "启用" : "Activate"}
                    </Button>
                  )}
                </div>
              </Card>
            </Col>
          );
        })}
      </Row>
    </div>
  );
}
