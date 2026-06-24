import { useEffect, useState } from "react";
import {
  Card,
  Table,
  Tag,
  Button,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  Switch,
  Space,
  Popconfirm,
  Typography,
  message,
} from "antd";
import { PlusOutlined, DeleteOutlined } from "@ant-design/icons";
import { useDashboardStore } from "../stores/dashboard";
import type { RouteRule } from "../api";
import type { ColumnsType } from "antd/es/table";

const { TextArea } = Input;
const { Text } = Typography;

const columns: ColumnsType<RouteRule> = [
  {
    title: "Name",
    dataIndex: "name",
    key: "name",
    width: 180,
    render: (text: string) => (
      <Text strong style={{ color: "#ccc" }}>
        {text}
      </Text>
    ),
  },
  {
    title: "Keywords",
    dataIndex: "keywords",
    key: "keywords",
    width: 260,
    render: (tags: string[]) => (
      <Space size={[4, 4]} wrap>
        {tags.map((tag) => (
          <Tag key={tag} color="purple" style={{ fontSize: 11 }}>
            {tag}
          </Tag>
        ))}
      </Space>
    ),
  },
  {
    title: "Target Model",
    dataIndex: "target_model",
    key: "target_model",
    width: 120,
    render: (model: string) => (
      <Tag color={model === "claude" ? "purple" : "green"}>{model}</Tag>
    ),
  },
  {
    title: "Priority",
    dataIndex: "priority",
    key: "priority",
    width: 80,
    sorter: (a: RouteRule, b: RouteRule) => b.priority - a.priority,
  },
  {
    title: "Status",
    dataIndex: "enabled",
    key: "enabled",
    width: 80,
    render: (enabled: boolean) => (
      <Tag color={enabled ? "green" : "default"}>
        {enabled ? "ON" : "OFF"}
      </Tag>
    ),
  },
  {
    title: "Action",
    key: "action",
    width: 80,
    render: (_: any, record: RouteRule) => (
      <Popconfirm
        title="Delete this rule?"
        onConfirm={() => {
          useDashboardStore.getState().deleteRule(record.id);
          message.success("Rule deleted");
        }}
      >
        <Button type="text" danger icon={<DeleteOutlined />} size="small" />
      </Popconfirm>
    ),
  },
];

export default function RuleManager() {
  const { rules, fetchRules, createRule } = useDashboardStore();
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchRules();
  }, [fetchRules]);

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      const kwText: string = values.keywords || "";
      const keywords = kwText
        .split(/[,，\s]+/)
        .map((k: string) => k.trim())
        .filter(Boolean);
      await createRule({ ...values, keywords });
      message.success("Rule created successfully!");
      setModalOpen(false);
      form.resetFields();
    } catch (err: any) {
      if (err.errorFields) return; // Form validation error
      message.error("Failed to create rule");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <Card
        title={
          <span style={{ color: "#ccc", fontSize: 15 }}>
            Routing Rules ({rules.length})
          </span>
        }
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setModalOpen(true)}
            size="small"
          >
            Add Rule
          </Button>
        }
        bordered={false}
        style={{
          background: "linear-gradient(135deg, #141428 0%, #1a1a35 100%)",
          border: "1px solid #2a2a45",
          borderRadius: 10,
        }}
        bodyStyle={{ padding: "8px 0" }}
      >
        <Text
          type="secondary"
          style={{ padding: "0 16px", display: "block", marginBottom: 8 }}
        >
          Rules are checked in priority order. The first matching rule wins.
          Unmatched requests default to DeepSeek (cheapest).
        </Text>
        <Table
          dataSource={rules}
          columns={columns}
          rowKey="id"
          size="small"
          pagination={false}
          locale={{ emptyText: "No rules defined yet" }}
          style={{ background: "transparent" }}
          rowClassName={() => "dark-row"}
        />
      </Card>

      <Modal
        title="Create Routing Rule"
        open={modalOpen}
        onOk={handleCreate}
        onCancel={() => {
          setModalOpen(false);
          form.resetFields();
        }}
        confirmLoading={saving}
        okText="Create"
        styles={{
          header: { background: "#141428", color: "#ccc" },
          body: { background: "#141428" },
          content: { background: "#141428" },
        }}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            target_model: "deepseek",
            priority: 50,
            enabled: true,
          }}
        >
          <Form.Item
            name="name"
            label="Rule Name"
            rules={[{ required: true, message: "Please enter a name" }]}
          >
            <Input placeholder="e.g., Architecture Tasks" />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <TextArea rows={2} placeholder="What this rule matches..." />
          </Form.Item>
          <Form.Item
            name="keywords"
            label="Keywords (comma-separated)"
            rules={[
              { required: true, message: "At least one keyword required" },
            ]}
          >
            <TextArea
              rows={2}
              placeholder="architecture, design, refactor, 架构"
            />
          </Form.Item>
          <Form.Item name="target_model" label="Target Model">
            <Select
              options={[
                { label: "Claude (high quality)", value: "claude" },
                { label: "DeepSeek (cost efficient)", value: "deepseek" },
              ]}
            />
          </Form.Item>
          <Form.Item name="priority" label="Priority (higher = checked first)">
            <InputNumber min={0} max={1000} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="enabled" label="Enabled" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      <style>{`
        .dark-row td { background: transparent !important; border-bottom: 1px solid #1a1a35 !important; }
        .ant-table { background: transparent !important; color: #ccc !important; }
        .ant-table-thead > tr > th { background: #1a1a35 !important; color: #888 !important; border-bottom: 1px solid #2a2a45 !important; font-size: 12px; }
      `}</style>
    </div>
  );
}
