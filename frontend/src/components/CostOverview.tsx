import { Card, Row, Col, Statistic } from "antd";
import {
  DollarOutlined,
  RiseOutlined,
  SaveOutlined,
  BarChartOutlined,
} from "@ant-design/icons";
import type { CostOverview as CostOverviewType } from "../api";

interface Props {
  overview: CostOverviewType;
}

export default function CostOverview({ overview }: Props) {
  const cards = [
    {
      title: "Today's Cost",
      value: overview.today_cost,
      prefix: "$",
      icon: <DollarOutlined />,
      color: "#6c5ce7",
      precision: 2,
    },
    {
      title: "Month Cost",
      value: overview.month_cost,
      prefix: "$",
      icon: <BarChartOutlined />,
      color: "#00b894",
      precision: 2,
    },
    {
      title: "Saved",
      value: overview.saved_amount,
      prefix: "$",
      icon: <SaveOutlined />,
      color: "#00cec9",
      precision: 2,
    },
    {
      title: "Saving Rate",
      value: overview.saving_rate,
      suffix: "%",
      icon: <RiseOutlined />,
      color: "#fd79a8",
      precision: 1,
    },
  ];

  return (
    <Row gutter={[16, 16]}>
      {cards.map((card) => (
        <Col xs={24} sm={12} lg={6} key={card.title}>
          <Card
            bordered={false}
            style={{
              background: "#ffffff",
              border: "1px solid #e5e7eb",
              borderRadius: 10,
              boxShadow: "0 1px 2px rgba(0,0,0,0.04)",
            }}
          >
            <Statistic
              title={
                <span style={{ color: "#6b7280", fontSize: 12, fontWeight: 500 }}>{card.title}</span>
              }
              value={card.value}
              precision={card.precision}
              suffix={card.suffix}
              valueStyle={{
                color: card.color,
                fontSize: 28,
                fontWeight: 700,
              }}
              prefix={
                <span style={{ color: card.color, fontSize: 22 }}>
                  {card.prefix}
                </span>
              }
            />
            <div
              style={{
                position: "absolute",
                top: 16,
                right: 16,
                color: card.color,
                opacity: 0.3,
                fontSize: 28,
              }}
            >
              {card.icon}
            </div>
          </Card>
        </Col>
      ))}
      <Col xs={24} sm={12} lg={6}>
        <Card
          bordered={false}
          style={{
            background: "#ffffff",
            border: "1px solid #e5e7eb",
            borderRadius: 10,
            boxShadow: "0 1px 2px rgba(0,0,0,0.04)",
          }}
        >
          <Statistic
            title={
              <span style={{ color: "#6b7280", fontSize: 12, fontWeight: 500 }}>Total Requests</span>
            }
            value={overview.total_requests}
            valueStyle={{
              color: "#ffeaa7",
              fontSize: 28,
              fontWeight: 700,
            }}
          />
        </Card>
      </Col>
    </Row>
  );
}
