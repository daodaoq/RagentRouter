import { useEffect, useState } from "react";
import { Card, Form, InputNumber, Switch, Button, Typography, Divider, message, Space, Tag, Descriptions } from "antd";
import { ReloadOutlined, SaveOutlined, InfoCircleOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";

const { Text, Title } = Typography;

// @ts-ignore
const api = window.electronAPI;

interface AppSettings {
  backendPort: number;
  closeToTray: boolean;
  autoStartBackend: boolean;
}

interface AppInfo {
  version: string; platform: string; arch: string;
  electronVersion: string; nodeVersion: string; dataPath: string;
}

export default function Settings() {
  const { t } = useTranslation();
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
      message.success(t("settings.saveSuccess"));
    } catch { message.error(t("settings.saveFail")); }
    setSaving(false);
  };

  if (!api) {
    return (
      <div style={{ padding: 24 }}>
        <Card bordered={false} style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10 }}>
          <InfoCircleOutlined style={{ fontSize: 48, color: "#9ca3af", marginBottom: 16 }} />
          <Title level={4} style={{ color: "#374151" }}>{t("settings.unavailable")}</Title>
          <Text type="secondary">{t("settings.onlyDesktop")}</Text>
        </Card>
      </div>
    );
  }

  return (
    <div style={{ padding: 24, maxWidth: 640 }}>
      <Title level={4} style={{ color: "#374151", marginBottom: 24 }}>{t("settings.title")}</Title>

      {settings && (
        <Form layout="vertical" initialValues={settings} onFinish={handleSave} style={{ maxWidth: 420 }}>
          <Card title={t("settings.backend")} size="small" bordered={false}
            style={{ marginBottom: 16, background: "#fff", border: "1px solid #e5e7eb" }}>
            <Form.Item name="backendPort" label={<Text style={{ color: "#6b7280", fontSize: 12 }}>{t("settings.backendPort")}</Text>}>
              <InputNumber min={1024} max={65535} style={{ width: 160 }} />
            </Form.Item>
            <Form.Item name="autoStartBackend" label={<Text style={{ color: "#6b7280", fontSize: 12 }}>{t("settings.autoStart")}</Text>} valuePropName="checked">
              <Switch size="small" />
            </Form.Item>
          </Card>

          <Card title={t("settings.window")} size="small" bordered={false}
            style={{ marginBottom: 16, background: "#fff", border: "1px solid #e5e7eb" }}>
            <Form.Item name="closeToTray" label={<Text style={{ color: "#6b7280", fontSize: 12 }}>{t("settings.closeToTray")}</Text>} valuePropName="checked">
              <Switch size="small" />
            </Form.Item>
          </Card>

          <Space>
            <Button type="primary" htmlType="submit" icon={<SaveOutlined />} loading={saving}>{t("settings.saveSettings")}</Button>
            <Button icon={<ReloadOutlined />} onClick={async () => { await api.restartBackend(); message.info(t("settings.restarting")); }}>
              {t("settings.restartBackend")}
            </Button>
          </Space>
        </Form>
      )}

      <Divider style={{ borderColor: "#e5e7eb", margin: "24px 0" }} />

      {appInfo && (
        <Card title={<Text style={{ color: "#6b7280", fontSize: 13 }}>{t("settings.about")}</Text>} size="small" bordered={false}
          style={{ background: "#fff", border: "1px solid #e5e7eb", maxWidth: 420 }}>
          <Descriptions size="small" column={1} colon={false}>
            <Descriptions.Item label={<Text style={{ color: "#9ca3af", fontSize: 11 }}>{t("settings.version")}</Text>}>
              <Text style={{ color: "#374151", fontSize: 12 }}>{appInfo.version}</Text>
            </Descriptions.Item>
            <Descriptions.Item label={<Text style={{ color: "#9ca3af", fontSize: 11 }}>{t("settings.platform")}</Text>}>
              <Text style={{ color: "#374151", fontSize: 12 }}>{appInfo.platform} ({appInfo.arch})</Text>
            </Descriptions.Item>
            <Descriptions.Item label={<Text style={{ color: "#9ca3af", fontSize: 11 }}>{t("settings.electron")}</Text>}>
              <Text style={{ color: "#374151", fontSize: 12 }}>{appInfo.electronVersion}</Text>
            </Descriptions.Item>
            <Descriptions.Item label={<Text style={{ color: "#9ca3af", fontSize: 11 }}>{t("settings.nodejs")}</Text>}>
              <Text style={{ color: "#374151", fontSize: 12 }}>{appInfo.nodeVersion}</Text>
            </Descriptions.Item>
            <Descriptions.Item label={<Text style={{ color: "#9ca3af", fontSize: 11 }}>{t("settings.dataPath")}</Text>}>
              <Text style={{ color: "#9ca3af", fontSize: 10 }}>{appInfo.dataPath}</Text>
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}
    </div>
  );
}
