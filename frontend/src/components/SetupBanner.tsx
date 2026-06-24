import { useEffect, useState } from "react";
import { Alert, Button, Space, Spin, message, Typography } from "antd";
import {
  SettingOutlined, CheckCircleOutlined, RollbackOutlined, ExclamationCircleOutlined,
} from "@ant-design/icons";
import { useTranslation } from "react-i18next";

const { Text } = Typography;

const SETUP_DONE_KEY = "ragent-setup-done";

interface Status {
  ccswitch_available: boolean;
  proxy_configured: boolean;
  current_provider: string | null;
  proxy_base_url: string;
}

export default function SetupBanner() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language.startsWith("zh") ? "zh" : "en";
  const [status, setStatus] = useState<Status | null>(null);
  const [loading, setLoading] = useState(true);
  const [applying, setApplying] = useState(false);
  const [reverting, setReverting] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [justCompleted, setJustCompleted] = useState(false);

  useEffect(() => {
    fetch("http://localhost:15722/api/setup/status")
      .then(r => r.json())
      .then(data => {
        setStatus(data);
        setLoading(false);
        // Show banner if not configured OR if user hasn't dismissed it
        if (data.proxy_configured && localStorage.getItem(SETUP_DONE_KEY)) {
          setDismissed(true);
        }
      })
      .catch(() => setLoading(false));
  }, []);

  const handleApply = async () => {
    setApplying(true);
    try {
      const res = await fetch("http://localhost:15722/api/setup/apply", { method: "POST" });
      const data = await res.json();
      if (data.success) {
        setJustCompleted(true);
        localStorage.setItem(SETUP_DONE_KEY, "true");
        setStatus(prev => prev ? { ...prev, proxy_configured: true } : null);
        message.success(
          lang === "zh" ? "配置成功！Claude Code 将通过 RAgent Router 转发" : "Setup complete! Claude Code now routes through RAgent Router"
        );
      } else {
        message.error(data.detail || "Setup failed");
      }
    } catch {
      message.error(lang === "zh" ? "配置失败" : "Setup failed");
    }
    setApplying(false);
  };

  const handleRevert = async () => {
    setReverting(true);
    try {
      const res = await fetch("http://localhost:15722/api/setup/revert", { method: "POST" });
      const data = await res.json();
      if (data.success) {
        localStorage.removeItem(SETUP_DONE_KEY);
        setJustCompleted(false);
        setDismissed(false);
        setStatus(prev => prev ? { ...prev, proxy_configured: false, current_provider: data.restored_provider } : null);
        message.success(
          lang === "zh"
            ? `已恢复到 ${data.restored_provider}`
            : `Reverted to ${data.restored_provider}`
        );
      } else {
        message.error(data.detail || "Revert failed");
      }
    } catch {
      message.error(lang === "zh" ? "回退失败" : "Revert failed");
    }
    setReverting(false);
  };

  const handleDismiss = () => {
    localStorage.setItem(SETUP_DONE_KEY, "true");
    setDismissed(true);
  };

  if (loading) {
    return (
      <div style={{ padding: "8px 20px", background: "#fff3cd", borderBottom: "1px solid #ffc107" }}>
        <Spin size="small" /> <Text style={{ color: "#856404", fontSize: 12 }}>
          {lang === "zh" ? "正在检查配置..." : "Checking configuration..."}
        </Text>
      </div>
    );
  }

  if (!status?.ccswitch_available || dismissed) return null;

  // Not yet configured — show setup prompt
  if (!status.proxy_configured && !justCompleted) {
    return (
      <Alert
        type="warning"
        showIcon
        icon={<ExclamationCircleOutlined />}
        message={
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
            <span style={{ fontSize: 13 }}>
              {lang === "zh"
                ? "检测到您是第一次使用 RAgent Router，需要配置 CC Switch 才能正常工作。"
                : "First-time setup: CC Switch needs to be configured for RAgent Router to work."}
            </span>
            <Space size={8}>
              <Button size="small" onClick={handleDismiss}>
                {lang === "zh" ? "跳过" : "Skip"}
              </Button>
              <Button type="primary" size="small" icon={<SettingOutlined />} loading={applying} onClick={handleApply}>
                {lang === "zh" ? "一键配置" : "One-Click Setup"}
              </Button>
            </Space>
          </div>
        }
        style={{
          borderRadius: 0, borderLeft: "none", borderRight: "none",
          background: "#fffbeb", borderColor: "#fde68a",
        }}
      />
    );
  }

  // Just completed — show success with revert option
  if (justCompleted || status.proxy_configured) {
    return (
      <Alert
        type="success"
        showIcon
        icon={<CheckCircleOutlined />}
        message={
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
            <span style={{ fontSize: 13 }}>
              {lang === "zh"
                ? `配置完成！Claude Code 请求通过 RAgent Router (${status.proxy_base_url}) 转发。`
                : `Setup complete! Claude Code routes through RAgent Router (${status.proxy_base_url}).`}
            </span>
            <Space size={8}>
              <Button size="small" onClick={handleDismiss}>
                {lang === "zh" ? "知道了" : "Got it"}
              </Button>
              <Button size="small" icon={<RollbackOutlined />} loading={reverting} onClick={handleRevert} danger>
                {lang === "zh" ? "撤回修改" : "Revert"}
              </Button>
            </Space>
          </div>
        }
        description={
          <Text type="secondary" style={{ fontSize: 11 }}>
            {lang === "zh"
              ? "如需恢复原始配置，请点击「撤回修改」按钮，或在 CC Switch 中手动切换回之前的供应商。"
              : "To restore original config, click 'Revert' or switch provider manually in CC Switch."}
          </Text>
        }
        style={{
          borderRadius: 0, borderLeft: "none", borderRight: "none",
          background: "#f0fdf4", borderColor: "#bbf7d0",
        }}
      />
    );
  }

  return null;
}
