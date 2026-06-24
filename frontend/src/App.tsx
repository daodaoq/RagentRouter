import { useEffect, useState } from "react";
import { Layout, Menu, Typography, Tag } from "antd";
import {
  DashboardOutlined,
  NodeIndexOutlined,
  ApiOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import Dashboard from "./pages/Dashboard";
import RuleManager from "./components/RuleManager";
import TestConsole from "./components/TestConsole";

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

type Page = "dashboard" | "rules" | "test";

export default function App() {
  const [page, setPage] = useState<Page>("dashboard");
  const [collapsed, setCollapsed] = useState(false);

  const menuItems = [
    { key: "dashboard", icon: <DashboardOutlined />, label: "Dashboard" },
    { key: "rules", icon: <NodeIndexOutlined />, label: "Route Rules" },
    { key: "test", icon: <ApiOutlined />, label: "Test Console" },
  ];

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="dark"
        style={{
          background: "linear-gradient(180deg, #0a0a2e 0%, #0d0d35 100%)",
          borderRight: "1px solid #1a1a40",
        }}
        width={220}
      >
        <div
          style={{
            padding: collapsed ? "16px 8px" : "20px 16px",
            textAlign: "center",
            borderBottom: "1px solid #1a1a40",
          }}
        >
          {collapsed ? (
            <Text strong style={{ color: "#6c5ce7", fontSize: 18 }}>
              R
            </Text>
          ) : (
            <div>
              <Text strong style={{ color: "#6c5ce7", fontSize: 20 }}>
                RAgent
              </Text>
              <Text strong style={{ color: "#a29bfe", fontSize: 20 }}>
                {" "}Router
              </Text>
              <br />
              <Tag color="purple" style={{ marginTop: 6, fontSize: 11 }}>
                v0.1.0
              </Tag>
            </div>
          )}
        </div>
        <Menu
          mode="inline"
          selectedKeys={[page]}
          onClick={({ key }) => setPage(key as Page)}
          items={menuItems}
          theme="dark"
          style={{
            background: "transparent",
            borderRight: "none",
            marginTop: 8,
          }}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: "linear-gradient(90deg, #0a0a2e 0%, #141428 100%)",
            borderBottom: "1px solid #1a1a40",
            display: "flex",
            alignItems: "center",
            paddingLeft: 24,
            height: 56,
          }}
        >
          <Text style={{ color: "#a29bfe", fontSize: 16 }}>
            {page === "dashboard" && "📊 Dashboard"}
            {page === "rules" && "🔀 Route Rules"}
            {page === "test" && "🧪 Test Console"}
          </Text>
          <div style={{ flex: 1 }} />
          <Tag color="green" style={{ marginRight: 16 }}>
            Demo Mode
          </Tag>
          <Text style={{ color: "#666", fontSize: 12 }}>
            Backend: localhost:8000
          </Text>
        </Header>
        <Content
          style={{
            padding: 24,
            background: "#0a0a1a",
            overflow: "auto",
            maxHeight: "calc(100vh - 56px)",
          }}
        >
          {page === "dashboard" && <Dashboard />}
          {page === "rules" && <RuleManager />}
          {page === "test" && <TestConsole />}
        </Content>
      </Layout>
    </Layout>
  );
}
