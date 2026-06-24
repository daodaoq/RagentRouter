import { useState } from "react";
import { Card, Input, Button, Typography, Space, Tag, Spin, Row, Col } from "antd";
import { SendOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { useDashboardStore } from "../stores/dashboard";

const { TextArea } = Input;
const { Text, Paragraph } = Typography;

export default function TestConsole() {
  const { t } = useTranslation();
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<
    { prompt: string; model: string; text: string; timestamp: number }[]
  >([]);
  const { fetchAll } = useDashboardStore();

  const QUICK_TESTS = [
    { label: t("test.quickArchitecture"), text: "Design a distributed task scheduling system" },
    { label: t("test.quickQa"), text: "Explain how Redis transactions work" },
    { label: t("test.quickBug"), text: "Debug this NullPointerException in my Java code" },
    { label: t("test.quickGenerate"), text: "Generate a REST API controller for user CRUD" },
    { label: t("test.quickDocs"), text: "Write documentation for the payment module API" },
  ];

  const sendMessage = async (content: string) => {
    if (!content.trim()) return;
    setLoading(true);
    const res = await useDashboardStore.getState().sendTestMessage(content.trim());
    if (res) {
      setResults((prev) => [
        { prompt: content, model: res.model, text: res.text, timestamp: Date.now() },
        ...prev.slice(0, 19),
      ]);
    }
    setLoading(false);
    setInput("");
    setTimeout(() => fetchAll(), 500);
  };

  return (
    <div style={{ padding: 20 }}>
      <Card
        bordered={false}
        style={{ marginBottom: 16, background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10 }}
      >
        <Text style={{ color: "#374151", fontSize: 14, fontWeight: 600, marginBottom: 8, display: "block" }}>
          🧪 {t("test.title")}
        </Text>
        <Text type="secondary" style={{ fontSize: 12, display: "block", marginBottom: 12 }}>
          {t("test.description")}
        </Text>

        <div style={{ marginBottom: 12 }}>
          <Text type="secondary" style={{ fontSize: 12, marginRight: 8 }}>{t("test.quickTests")}</Text>
          <Space wrap size={[4, 8]}>
            {QUICK_TESTS.map((test) => (
              <Button key={test.label} size="small" onClick={() => setInput(test.text)}>
                {test.label}
              </Button>
            ))}
          </Space>
        </div>

        <Row gutter={12}>
          <Col flex="auto">
            <TextArea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onPressEnter={(e) => { if (!e.shiftKey) { e.preventDefault(); sendMessage(input); } }}
              placeholder={t("test.placeholder")}
              rows={3}
            />
          </Col>
          <Col>
            <Button type="primary" icon={<SendOutlined />} onClick={() => sendMessage(input)} loading={loading} style={{ height: "100%" }} size="large">
              {t("test.send")}
            </Button>
          </Col>
        </Row>
      </Card>

      <Card
        title={<span style={{ color: "#374151", fontSize: 14, fontWeight: 600 }}>{t("test.responseHistory")} ({results.length})</span>}
        bordered={false}
        style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10 }}
        bodyStyle={{ padding: "8px 16px", maxHeight: 520, overflow: "auto" }}
      >
        {loading && <div style={{ textAlign: "center", padding: 20 }}><Spin tip={t("test.routing")} /></div>}
        {results.length === 0 && !loading && (
          <Text type="secondary" style={{ display: "block", textAlign: "center", padding: 40 }}>{t("test.emptyHint")}</Text>
        )}
        {results.map((r, i) => (
          <div key={r.timestamp} style={{ padding: "12px 0", borderBottom: i < results.length - 1 ? "1px solid #f3f4f6" : "none" }}>
            <div style={{ marginBottom: 6 }}>
              <Tag color="purple" style={{ fontSize: 11 }}><ThunderboltOutlined /> {r.model}</Tag>
              <Text type="secondary" style={{ fontSize: 11, marginLeft: 8 }}>{new Date(r.timestamp).toLocaleTimeString()}</Text>
            </div>
            <Paragraph ellipsis={{ rows: 1, expandable: true, symbol: "more" }} style={{ color: "#6b7280", fontSize: 13, marginBottom: 4 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>Q: </Text>{r.prompt}
            </Paragraph>
            <Paragraph ellipsis={{ rows: 2, expandable: true, symbol: "more" }} style={{ color: "#374151", fontSize: 13, marginBottom: 0 }}>
              <Text style={{ color: "#6366f1", fontSize: 12 }}>A: </Text>{r.text}
            </Paragraph>
          </div>
        ))}
      </Card>
    </div>
  );
}
