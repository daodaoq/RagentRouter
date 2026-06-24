import { useState } from "react";
import {
  Card,
  Input,
  Button,
  Typography,
  Space,
  Tag,
  Spin,
  Divider,
  Row,
  Col,
} from "antd";
import { SendOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { useDashboardStore } from "../stores/dashboard";

const { TextArea } = Input;
const { Text, Paragraph } = Typography;

const QUICK_TESTS = [
  { label: "Architecture", text: "Design a distributed task scheduling system" },
  { label: "Simple Q&A", text: "Explain how Redis transactions work" },
  { label: "Bug Fix", text: "Debug this NullPointerException in my Java code" },
  { label: "Generate", text: "Generate a REST API controller for user CRUD" },
  { label: "Docs", text: "Write documentation for the payment module API" },
];

export default function TestConsole() {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<
    { prompt: string; model: string; text: string; timestamp: number }[]
  >([]);
  const { fetchAll } = useDashboardStore();

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
    // Refresh dashboard data after a test
    setTimeout(() => fetchAll(), 500);
  };

  return (
    <div>
      {/* Input Area */}
      <Card
        bordered={false}
        style={{
          background: "linear-gradient(135deg, #141428 0%, #1a1a35 100%)",
          border: "1px solid #2a2a45",
          borderRadius: 10,
          marginBottom: 16,
        }}
      >
        <Text style={{ color: "#ccc", fontSize: 15, marginBottom: 12, display: "block" }}>
          🧪 Test the Router
        </Text>
        <Text type="secondary" style={{ fontSize: 12, display: "block", marginBottom: 12 }}>
          Type a message to see how RAgent Router selects the model. Try different prompts to test the rules.
        </Text>

        {/* Quick test buttons */}
        <div style={{ marginBottom: 12 }}>
          <Text type="secondary" style={{ fontSize: 12, marginRight: 8 }}>
            Quick tests:
          </Text>
          <Space wrap size={[4, 8]}>
            {QUICK_TESTS.map((t) => (
              <Button
                key={t.label}
                size="small"
                onClick={() => {
                  setInput(t.text);
                }}
              >
                {t.label}
              </Button>
            ))}
          </Space>
        </div>

        <Row gutter={12}>
          <Col flex="auto">
            <TextArea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onPressEnter={(e) => {
                if (!e.shiftKey) {
                  e.preventDefault();
                  sendMessage(input);
                }
              }}
              placeholder="Type a message (e.g., 'Design a microservice architecture') and press Enter..."
              rows={3}
              style={{ background: "#0a0a1a", color: "#ccc", border: "1px solid #2a2a45" }}
            />
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={() => sendMessage(input)}
              loading={loading}
              style={{ height: "100%" }}
              size="large"
            >
              Send
            </Button>
          </Col>
        </Row>
      </Card>

      {/* Results */}
      <Card
        title={
          <span style={{ color: "#ccc", fontSize: 15 }}>
            Response History ({results.length})
          </span>
        }
        bordered={false}
        style={{
          background: "linear-gradient(135deg, #141428 0%, #1a1a35 100%)",
          border: "1px solid #2a2a45",
          borderRadius: 10,
        }}
        bodyStyle={{ padding: "8px 16px", maxHeight: 520, overflow: "auto" }}
      >
        {loading && (
          <div style={{ textAlign: "center", padding: 20 }}>
            <Spin tip="Routing & generating response..." />
          </div>
        )}

        {results.length === 0 && !loading && (
          <Text type="secondary" style={{ display: "block", textAlign: "center", padding: 40 }}>
            Send a message to see the router in action.
          </Text>
        )}

        {results.map((r, i) => (
          <div
            key={r.timestamp}
            style={{
              padding: "12px 0",
              borderBottom: i < results.length - 1 ? "1px solid #1a1a35" : "none",
            }}
          >
            <div style={{ marginBottom: 6 }}>
              <Tag color="purple" style={{ fontSize: 11 }}>
                <ThunderboltOutlined /> {r.model}
              </Tag>
              <Text type="secondary" style={{ fontSize: 11, marginLeft: 8 }}>
                {new Date(r.timestamp).toLocaleTimeString()}
              </Text>
            </div>
            <Paragraph
              ellipsis={{ rows: 1, expandable: true, symbol: "more" }}
              style={{ color: "#aaa", fontSize: 13, marginBottom: 4 }}
            >
              <Text type="secondary" style={{ fontSize: 12 }}>
                Q:{" "}
              </Text>
              {r.prompt}
            </Paragraph>
            <Paragraph
              ellipsis={{ rows: 2, expandable: true, symbol: "more" }}
              style={{ color: "#ccc", fontSize: 13, marginBottom: 0 }}
            >
              <Text style={{ color: "#6c5ce7", fontSize: 12 }}>A: </Text>
              {r.text}
            </Paragraph>
          </div>
        ))}
      </Card>
    </div>
  );
}
