import React from "react";
import ReactDOM from "react-dom/client";
import { ConfigProvider } from "antd";
import enUS from "antd/locale/en_US";
import zhCN from "antd/locale/zh_CN";
import App from "./App";
import "./i18n";
import "./index.css";
import i18n from "./i18n";

const antdLocales: Record<string, typeof enUS> = { en: enUS, zh: zhCN };

function Root() {
  const [locale, setLocale] = React.useState(antdLocales[i18n.language] || zhCN);

  React.useEffect(() => {
    const handler = (lng: string) => setLocale(antdLocales[lng] || zhCN);
    i18n.on("languageChanged", handler);
    return () => { i18n.off("languageChanged", handler); };
  }, []);

  return (
    <ConfigProvider
      locale={locale}
      theme={{
        token: {
          colorPrimary: "#6366f1",
          colorBgBase: "#ffffff",
          colorBgContainer: "#ffffff",
          colorBgElevated: "#f8f9fa",
          colorBorder: "#e5e7eb",
          borderRadius: 8,
          fontFamily:
            '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
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
