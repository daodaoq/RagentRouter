import { useEffect, useState } from "react";
import {
  Card, Table, Tag, Button, Modal, Form, Input, Select, InputNumber, Switch,
  Space, Popconfirm, Typography, message,
} from "antd";
import { PlusOutlined, DeleteOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { useDashboardStore } from "../stores/dashboard";
import PageHelp from "./PageHelp";
import type { RouteRule } from "../api";
import type { ColumnsType } from "antd/es/table";

const { TextArea } = Input;
const { Text } = Typography;

export default function RuleManager() {
  const { t } = useTranslation();
  const { rules, fetchRules, createRule, deleteRule } = useDashboardStore();
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);

  useEffect(() => { fetchRules(); }, [fetchRules]);

  const columns: ColumnsType<RouteRule> = [
    {
      title: t("rules.name"), dataIndex: "name", key: "name", width: 180,
      render: (text: string) => <Text strong style={{ color: "#374151" }}>{text}</Text>,
    },
    {
      title: t("rules.keywords"), dataIndex: "keywords", key: "keywords", width: 240,
      render: (tags: string[]) => (
        <Space size={[4, 4]} wrap>
          {tags.map((tag) => <Tag key={tag} color="purple" style={{ fontSize: 11 }}>{tag}</Tag>)}
        </Space>
      ),
    },
    {
      title: t("rules.targetModel"), dataIndex: "target_model", key: "target_model", width: 120,
      render: (model: string) => <Tag color={model === "claude" ? "purple" : "green"}>{model}</Tag>,
    },
    {
      title: t("rules.priority"), dataIndex: "priority", key: "priority", width: 80,
      sorter: (a: RouteRule, b: RouteRule) => b.priority - a.priority,
    },
    {
      title: t("rules.status"), dataIndex: "enabled", key: "enabled", width: 80,
      render: (enabled: boolean) => <Tag color={enabled ? "green" : "default"}>{enabled ? t("rules.on") : t("rules.off")}</Tag>,
    },
    {
      title: t("rules.action"), key: "action", width: 80,
      render: (_: any, record: RouteRule) => (
        <Popconfirm title={t("rules.deleteConfirm")} onConfirm={() => { deleteRule(record.id); message.success(t("rules.deleted")); }}>
          <Button type="text" danger icon={<DeleteOutlined />} size="small" />
        </Popconfirm>
      ),
    },
  ];

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      const kwText: string = values.keywords || "";
      const keywords = kwText.split(/[,，\s]+/).map((k: string) => k.trim()).filter(Boolean);
      await createRule({ ...values, keywords });
      message.success(t("rules.createSuccess"));
      setModalOpen(false);
      form.resetFields();
    } catch (err: any) {
      if (err.errorFields) return;
      message.error(t("rules.createFail"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ padding: 20 }}>
      <Card
        title={<span style={{ color: "#374151", fontSize: 14, fontWeight: 600 }}>{t("rules.title")} ({rules.length})<PageHelp page="rules" /></span>}
        extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)} size="small">{t("rules.addRule")}</Button>}
        bordered={false}
        style={{ background: "#ffffff", border: "1px solid #e5e7eb", borderRadius: 10 }}
        bodyStyle={{ padding: "8px 0" }}
      >
        <Text type="secondary" style={{ padding: "0 16px", display: "block", marginBottom: 8, fontSize: 12 }}>
          {t("rules.description")}
        </Text>
        <Table
          dataSource={rules}
          columns={columns}
          rowKey="id"
          size="small"
          scroll={{ x: 780 }}
          pagination={false}
          locale={{ emptyText: t("rules.empty") }}
        />
      </Card>

      <Modal
        title={t("rules.createRule")}
        open={modalOpen}
        onOk={handleCreate}
        onCancel={() => { setModalOpen(false); form.resetFields(); }}
        confirmLoading={saving}
        okText={t("rules.creating")}
      >
        <Form form={form} layout="vertical" initialValues={{ target_model: "deepseek", priority: 50, enabled: true }}>
          <Form.Item name="name" label={t("rules.name")} rules={[{ required: true }]}>
            <Input placeholder={t("rules.namePlaceholder")} />
          </Form.Item>
          <Form.Item name="description" label={t("rules.desc")}>
            <TextArea rows={2} placeholder={t("rules.descPlaceholder")} />
          </Form.Item>
          <Form.Item name="keywords" label={t("rules.keywords")} rules={[{ required: true }]}>
            <TextArea rows={2} placeholder={t("rules.keywordsPlaceholder")} />
          </Form.Item>
          <Form.Item name="target_model" label={t("rules.targetModel")}>
            <Select options={[
              { label: t("rules.claude"), value: "claude" },
              { label: t("rules.deepseek"), value: "deepseek" },
            ]} />
          </Form.Item>
          <Form.Item name="priority" label={t("rules.priority")}>
            <InputNumber min={0} max={1000} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="enabled" label={t("rules.enabled")} valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
