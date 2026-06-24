import { useEffect } from "react";
import { Row, Col, Spin, Empty, Button } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import { useDashboardStore } from "../stores/dashboard";
import CostOverview from "../components/CostOverview";
import ModelDistribution from "../components/ModelDistribution";
import RecentRoutes from "../components/RecentRoutes";
import CostTrend from "../components/CostTrend";

export default function Dashboard() {
  const { overview, loading, fetchAll } = useDashboardStore();

  useEffect(() => {
    fetchAll();
    // Refresh every 30s
    const interval = setInterval(fetchAll, 30000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  if (loading && !overview) {
    return (
      <div style={{ textAlign: "center", paddingTop: 120 }}>
        <Spin size="large" tip="Loading dashboard..." />
      </div>
    );
  }

  if (!overview) {
    return (
      <Empty
        description="No data available. Make sure the backend is running."
        style={{ paddingTop: 120 }}
      >
        <Button type="primary" icon={<ReloadOutlined />} onClick={fetchAll}>
          Retry
        </Button>
      </Empty>
    );
  }

  return (
    <div>
      <Row justify="end" style={{ marginBottom: 16 }}>
        <Button icon={<ReloadOutlined />} onClick={fetchAll} size="small">
          Refresh
        </Button>
      </Row>

      {/* Row 1: Cost Overview Cards */}
      <CostOverview overview={overview} />

      {/* Row 2: Model Distribution + Recent Routes */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={10}>
          <ModelDistribution />
        </Col>
        <Col xs={24} lg={14}>
          <RecentRoutes />
        </Col>
      </Row>

      {/* Row 3: Cost Trend */}
      <Row style={{ marginTop: 16 }}>
        <Col span={24}>
          <CostTrend />
        </Col>
      </Row>
    </div>
  );
}
