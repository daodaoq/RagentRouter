import { useEffect, useState } from "react";
import {
  Card,
  Form,
  InputNumber,
  Switch,
  Button,
  Typography,
  Divider,
  message,
  Space,
  Tag,
  Descriptions,
} from "antd";
import {
  ReloadOutlined,
  SaveOutlined,
  InfoCircleOutlined,
} from "@ant-design/icons";

const { Text, Title } = Typography;

// @ts-ignore
const api = window.electronAPI;

interface AppSettings {
  backendPort: number;
  closeToTray: boolean;
  autoStartBackend: boolean;
  theme: string;
}

interface AppInfo {
  version: string;
  platform: string;
  arch: string;
  electronVersion: string;
  nodeVersion: string;
  dataPath: string;
  isDev: boolean;
}

export default function Settings() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [appInfo, setAppInfo] = useState<AppInfo | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!api) return;
    api.getSettings().then(setSettings);
    api.getAppInfo().then(setAppInfo);
  }, []);

  const handleSave = async (values: AppSettings) => {
    if (!api) return;
    setSaving(true);
    try {
      await api.saveSettings(values);
      setSettings(values);
      message.success("Settings saved");
    } catch {
      message.error("Failed to save settings");
    }
    setSaving(false);
  };

  if (!api) {
    return (
      <Card bordered={false} style={{ margin: 24 }}>
        <InfoCircleOutlined style={{ fontSize: 48, color: "#555", marginBottom: 16 }} />
        <Title level={4} style={{ color: "#ccc" }}>
          Settings Unavailable
        </Title>
        <Text type="secondary">
          Settings are only available in the desktop (Electron) app. Please launch via <Tag>npm start</Tag>
        </Text>
      </Card>
    );
  }

  return (
    <div style={{ padding: 24, maxWidth: 640 }}>
      <Title level={4} style={{ color: "#ccc", marginBottom: 24 }}>
        Settings
      </Title>

      {settings && (
        <Form
          layout="vertical"
          initialValues={settings}
          onFinish={handleSave}
          style={{ maxWidth: 420 }}
        >
          <Card
            title="Backend"
            size="small"
            bordered={false}
            style={{ marginBottom: 16, background: "var(--bg-card)", border: "1px solid var(--border-light)" }}
          >
            <Form.Item
              name="backendPort"
              label={<Text style={{ color: "#888", fontSize: 12 }}>Port</Text>}
            >
              <InputNumber min={1024} max={65535} style={{ width: 160 }} />
            </Form.Item>
            <Form.Item
              name="autoStartBackend"
              label={<Text style={{ color: "#888", fontSize: 12 }}>Auto-start backend on launch</Text>}
              valuePropName="checked"
            >
              <Switch size="small" />
            </Form.Item>
          </Card>

          <Card
            title="Window"
            size="small"
            bordered={false}
            style={{ marginBottom: 16, background: "var(--bg-card)", border: "1px solid var(--border-light)" }}
          >
            <Form.Item
              name="closeToTray"
              label={<Text style={{ color: "#888", fontSize: 12 }}>Close to system tray instead of quitting</Text>}
              valuePropName="checked"
            >
              <Switch size="small" />
            </Form.Item>
          </Card>

          <Space>
            <Button type="primary" htmlType="submit" icon={<SaveOutlined />} loading={saving}>
              Save Settings
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={async () => {
                await api.restartBackend();
                message.info("Backend restarting...");
              }}
            >
              Restart Backend
            </Button>
          </Space>
        </Form>
      )}

      <Divider style={{ borderColor: "#1a1a40", margin: "24px 0" }} />

      {appInfo && (
        <Card
          title={<Text style={{ color: "#888", fontSize: 13 }}>About</Text>}
          size="small"
          bordered={false}
          style={{ background: "var(--bg-card)", border: "1px solid var(--border-light)", maxWidth: 420 }}
        >
          <Descriptions size="small" column={1} colon={false}>
            <Descriptions.Item label={<Text style={{ color: "#666", fontSize: 11 }}>Version</Text>}>
              <Text style={{ color: "#ccc", fontSize: 12 }}>{appInfo.version}</Text>
            </Descriptions.Item>
            <Descriptions.Item label={<Text style={{ color: "#666", fontSize: 11 }}>Platform</Text>}>
              <Text style={{ color: "#ccc", fontSize: 12 }}>{appInfo.platform} ({appInfo.arch})</Text>
            </Descriptions.Item>
            <Descriptions.Item label={<Text style={{ color: "#666", fontSize: 11 }}>Electron</Text>}>
              <Text style={{ color: "#ccc", fontSize: 12 }}>{appInfo.electronVersion}</Text>
            </Descriptions.Item>
            <Descriptions.Item label={<Text style={{ color: "#666", fontSize: 11 }}>Node.js</Text>}>
              <Text style={{ color: "#ccc", fontSize: 12 }}>{appInfo.nodeVersion}</Text>
            </Descriptions.Item>
            <Descriptions.Item label={<Text style={{ color: "#666", fontSize: 11 }}>Data Path</Text>}>
              <Text style={{ color: "#666", fontSize: 10, fontFamily: "monospace" }}>{appInfo.dataPath}</Text>
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}
    </div>
  );
}
