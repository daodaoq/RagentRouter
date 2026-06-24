import { Popover } from "antd";
import { QuestionCircleOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";

interface Props {
  page: "providers" | "traffic" | "dashboard" | "rules" | "test" | "settings";
}

export default function PageHelp({ page }: Props) {
  const { t } = useTranslation();
  const content = t(`help.${page}`, "");

  if (!content) return null;

  return (
    <Popover
      content={
        <div style={{ maxWidth: 300, fontSize: 12, lineHeight: 1.6, color: "#374151" }}>
          {content}
        </div>
      }
      title={null}
      trigger="click"
      placement="bottom"
    >
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          width: 18,
          height: 18,
          borderRadius: "50%",
          border: "1px solid #d1d5db",
          color: "#9ca3af",
          fontSize: 11,
          cursor: "pointer",
          transition: "all 0.15s",
          marginLeft: 6,
          verticalAlign: "middle",
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = "#6366f1";
          e.currentTarget.style.color = "#6366f1";
          e.currentTarget.style.background = "#eef2ff";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = "#d1d5db";
          e.currentTarget.style.color = "#9ca3af";
          e.currentTarget.style.background = "transparent";
        }}
      >
        ?
      </span>
    </Popover>
  );
}
