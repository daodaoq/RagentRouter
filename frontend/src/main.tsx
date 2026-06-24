import React, { useEffect } from "react";
import ReactDOM from "react-dom/client";
import { ConfigProvider, theme } from "antd";
import enUS from "antd/locale/en_US";
import zhCN from "antd/locale/zh_CN";
import App from "./App";
import "./i18n";
import "./index.css";
import i18n from "./i18n";
import { useThemeStore } from "./stores/theme";

const antdLocales: Record<string, typeof enUS> = { en: enUS, zh: zhCN };

function Root() {
  const [locale, setLocale] = React.useState(antdLocales[i18n.language] || zhCN);
  const mode = useThemeStore((s) => s.mode);

  useEffect(() => {
    const handler = (lng: string) => setLocale(antdLocales[lng] || zhCN);
    i18n.on("languageChanged", handler);
    return () => { i18n.off("languageChanged", handler); };
  }, []);

  // Apply theme class to document
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", mode);
  }, [mode]);

  const isDark = mode === "dark";

  return (
    <ConfigProvider
      locale={locale}
      theme={{
        algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
        token: {
          colorPrimary: "#6366f1",
          colorBgBase: isDark ? "#0a0a1a" : "#ffffff",
          colorBgContainer: isDark ? "#141428" : "#ffffff",
          colorBgElevated: isDark ? "#1a1a35" : "#f8f9fa",
          colorBorder: isDark ? "#2a2a45" : "#e5e7eb",
          borderRadius: 8,
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
          fontSize: 13,
        },
      }}
    >
      <App />
    </ConfigProvider>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>
);
