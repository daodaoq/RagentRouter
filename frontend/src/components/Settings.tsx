import { useEffect, useState } from "react";
import {
  Card, Button, Typography, Divider, Switch, message, Space, Tag, Descriptions, Segmented,
} from "antd";
import {
  ReloadOutlined, RollbackOutlined, BulbOutlined, GlobalOutlined,
  SettingOutlined, InfoCircleOutlined,
} from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { useThemeStore } from "../stores/theme";
import i18n from "../i18n";
import PageHelp from "./PageHelp";

const { Text, Title } = Typography;

// @ts-ignore
const api = window.electronAPI;

export default function Settings() {
  const { t } = useTranslation();
  const lang = i18n.language.startsWith("zh") ? "zh" : "en";
  const { mode: themeMode, setMode } = useThemeStore();

  // Electron settings
  const [backendPort, setBackendPort] = useState(15722);
  const [closeToTray, setCloseToTray] = useState(true);
  const [autoStartBackend, setAutoStartBackend] = useState(true);
  const [saving, setSaving] = useState(false);

  // CC Switch setup
  const [ccswitchSetup, setCcswitchSetup] = useState(false);
  const [reverting, setReverting] = useState(false);

  // App info
  const [appInfo, setAppInfo] = useState<any>(null);

  useEffect(() => {
    if (api) {
      api.getSettings().then((s: any) => {
        if (s) {
          setBackendPort(s.backendPort || 15722);
          setCloseToTray(s.closeToTray !== false);
          setAutoStartBackend(s.autoStartBackend !== false);
        }
      });
      api.getAppInfo().then(setAppInfo);
    }
    // Check CC Switch setup status
    fetch("http://localhost:15722/api/setup/status")
      .then(r => r.json())
      .then(d => setCcswitchSetup(d.proxy_configured))
      .catch(() => {});
  }, []);

  const saveElectronSettings = async () => {
    if (!api) return;
    setSaving(true);
    try {
      await api.saveSettings({ backendPort, closeToTray, autoStartBackend });
      message.success(t("settings.saveSuccess"));
    } catch { message.error(t("settings.saveFail")); }
    setSaving(false);
  };

  const handleRevert = async () => {
    setReverting(true);
    try {
      const res = await fetch("http://localhost:15722/api/setup/revert", { method: "POST" });
      const data = await res.json();
      if (data.success) {
        setCcswitchSetup(false);
        message.success(
          lang === "zh" ? `已恢复到 ${data.restored_provider}` : `Reverted to ${data.restored_provider}`
        );
      }
    } catch { message.error(lang === "zh" ? "回退失败" : "Revert failed"); }
    setReverting(false);
  };

  return (
    <div style={{ padding: 24, maxWidth: 680 }}>
      <Title level={4} style={{ color: "var(--text-primary)", marginBottom: 24 }}>
        <SettingOutlined style={{ marginRight: 8 }} />
        {t("settings.title")}
        <PageHelp page="settings" />
      </Title>

      {/* ── CC Switch Proxy ────────────────────────────────────── */}
      <Card
        title={<Text strong style={{ color: "var(--text-primary)" }}>{lang === "zh" ? "CC Switch 代理" : "CC Switch Proxy"}</Text>}
        size="small" bordered={false}
        style={{ marginBottom: 16, background: "var(--bg-card)", border: "1px solid var(--border-light)" }}
      >
        {ccswitchSetup ? (
          <div>
            <Text style={{ color: "var(--text-secondary)", fontSize: 12 }}>
              {lang === "zh"
                ? "RAgent Router 已配置为 CC Switch 的代理，Claude Code 请求通过 RAgent Router 转发。"
                : "RAgent Router is configured as CC Switch proxy. Claude Code requests route through RAgent Router."}
            </Text>
            <div style={{ marginTop: 10 }}>
              <Button icon={<RollbackOutlined />} loading={reverting} onClick={handleRevert} danger size="small">
                {lang === "zh" ? "撤回代理配置" : "Revert Proxy Setup"}
              </Button>
              <Text type="secondary" style={{ marginLeft: 12, fontSize: 11 }}>
                {lang === "zh"
                  ? "将恢复 CC Switch 原始配置"
                  : "Restores CC Switch to original config"}
              </Text>
            </div>
          </div>
        ) : (
          <Text type="secondary" style={{ fontSize: 12 }}>
            {lang === "zh"
              ? "尚未配置。请在首页提示条中点击「一键配置」。"
              : "Not configured yet. Use the setup banner on the home page."}
          </Text>
        )}
      </Card>

      {/* ── Appearance ─────────────────────────────────────────── */}
      <Card
        title={<Text strong style={{ color: "var(--text-primary)" }}>
          <BulbOutlined style={{ marginRight: 6 }} />
          {lang === "zh" ? "外观" : "Appearance"}
        </Text>}
        size="small" bordered={false}
        style={{ marginBottom: 16, background: "var(--bg-card)", border: "1px solid var(--border-light)" }}
      >
        {/* Theme */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 0" }}>
          <Text style={{ color: "var(--text-secondary)", fontSize: 12 }}>
            {lang === "zh" ? "主题模式" : "Theme Mode"}
          </Text>
          <Segmented
            size="small"
            value={themeMode}
            onChange={(v) => setMode(v as "light" | "dark")}
            options={[
              { label: lang === "zh" ? "☀️ 浅色" : "☀️ Light", value: "light" },
              { label: lang === "zh" ? "🌙 深色" : "🌙 Dark", value: "dark" },
            ]}
          />
        </div>

        <Divider style={{ margin: "8px 0", borderColor: "var(--border-color)" }} />

        {/* Language */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 0" }}>
          <Text style={{ color: "var(--text-secondary)", fontSize: 12 }}>
            <GlobalOutlined style={{ marginRight: 6 }} />
            {lang === "zh" ? "界面语言" : "Language"}
          </Text>
          <Segmented
            size="small"
            value={i18n.language.startsWith("zh") ? "zh" : "en"}
            onChange={(v) => i18n.changeLanguage(v as string)}
            options={[
              { label: "🇨🇳 中文", value: "zh" },
              { label: "🇺🇸 English", value: "en" },
            ]}
          />
        </div>
      </Card>

      {/* ── Backend ────────────────────────────────────────────── */}
      <Card
        title={<Text strong style={{ color: "var(--text-primary)" }}>{t("settings.backend")}</Text>}
        size="small" bordered={false}
        style={{ marginBottom: 16, background: "var(--bg-card)", border: "1px solid var(--border-light)" }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "6px 0" }}>
          <div>
            <Text style={{ color: "var(--text-secondary)", fontSize: 12 }}>{t("settings.backendPort")}</Text>
            <br />
            <Text code style={{ fontSize: 13 }}>:{backendPort}</Text>
          </div>
          <div style={{ display: "flex", gap: 12 }}>
            <Button
              size="small"
              onClick={() => {
                const newPort = backendPort === 15722 ? 15723 : 15722;
                setBackendPort(newPort);
                if (api) api.saveSettings({ backendPort: newPort });
              }}
            >
              {backendPort === 15722 ? "15723" : "15722"}
            </Button>
          </div>
        </div>

        <Divider style={{ margin: "8px 0", borderColor: "var(--border-color)" }} />

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "6px 0" }}>
          <Text style={{ color: "var(--text-secondary)", fontSize: 12 }}>{t("settings.autoStart")}</Text>
          <Switch size="small" checked={autoStartBackend} onChange={(v) => { setAutoStartBackend(v); if (api) api.saveSettings({ autoStartBackend: v }); }} />
        </div>

        <Divider style={{ margin: "8px 0", borderColor: "var(--border-color)" }} />

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "6px 0" }}>
          <Text style={{ color: "var(--text-secondary)", fontSize: 12 }}>{t("settings.closeToTray")}</Text>
          <Switch size="small" checked={closeToTray} onChange={(v) => { setCloseToTray(v); if (api) api.saveSettings({ closeToTray: v }); }} />
        </div>

        {api && (
          <div style={{ marginTop: 12 }}>
            <Button icon={<ReloadOutlined />} size="small" onClick={async () => {
              await api.restartBackend();
              message.info(t("settings.restarting"));
            }}>
              {t("settings.restartBackend")}
            </Button>
          </div>
        )}
      </Card>

      {/* ── About ──────────────────────────────────────────────── */}
      {appInfo && (
        <Card
          title={<Text strong style={{ color: "var(--text-primary)" }}>
            <InfoCircleOutlined style={{ marginRight: 6 }} />
            {t("settings.about")}
          </Text>}
          size="small" bordered={false}
          style={{ background: "var(--bg-card)", border: "1px solid var(--border-light)" }}
        >
          <Descriptions size="small" column={1} colon={false}>
            <Descriptions.Item label={<Text style={{ color: "var(--text-muted)", fontSize: 11 }}>{t("settings.version")}</Text>}>
              <Text style={{ color: "var(--text-primary)", fontSize: 12 }}>{appInfo.version}</Text>
            </Descriptions.Item>
            <Descriptions.Item label={<Text style={{ color: "var(--text-muted)", fontSize: 11 }}>{t("settings.platform")}</Text>}>
              <Text style={{ color: "var(--text-primary)", fontSize: 12 }}>{appInfo.platform} ({appInfo.arch})</Text>
            </Descriptions.Item>
            <Descriptions.Item label={<Text style={{ color: "var(--text-muted)", fontSize: 11 }}>{t("settings.electron")}</Text>}>
              <Text style={{ color: "var(--text-primary)", fontSize: 12 }}>{appInfo.electronVersion}</Text>
            </Descriptions.Item>
            <Descriptions.Item label={<Text style={{ color: "var(--text-muted)", fontSize: 11 }}>{t("settings.nodejs")}</Text>}>
              <Text style={{ color: "var(--text-primary)", fontSize: 12 }}>{appInfo.nodeVersion}</Text>
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}
    </div>
  );
}
