import React, { useMemo, useState } from "react";
import { Button, Card, Form, Input, Select, Space, Table, Tag, Typography } from "antd";
import PrototypeShell from "./prototype-shell";
import "./prototype-shell.css";

const { Text, Title } = Typography;

type Row = {
  id: string;
  name: string;
  status: "active" | "inactive";
  updatedAt: string;
};

const seedRows: Row[] = [
  { id: "r1", name: "示例记录 1", status: "active", updatedAt: "2026-03-12 10:00" },
  { id: "r2", name: "示例记录 2", status: "inactive", updatedAt: "2026-03-12 11:00" },
];

const PageListTemplate: React.FC = () => {
  const [form] = Form.useForm();
  const [rows] = useState<Row[]>(seedRows);
  const filters = Form.useWatch([], form) as { keyword?: string; status?: Row["status"] } | undefined;

  const data = useMemo(() => {
    const keyword = (filters?.keyword || "").trim();
    const status = filters?.status;
    return rows.filter((r) => {
      if (keyword && !r.name.includes(keyword)) return false;
      if (status && r.status !== status) return false;
      return true;
    });
  }, [filters?.keyword, filters?.status, rows]);

  return (
    <PrototypeShell
      brandTitle="模块原型工作台"
      brandSubtitle="列表页默认骨架"
      brandMark="LB"
      topNavItems={[
        { key: "home", label: "首页" },
        { key: "module", label: "当前模块" },
        { key: "list", label: "列表页" },
      ]}
      activeTopNavKey="list"
      sidebarTitle="列表页模板"
      sidebarBadge="P0 Archetype"
      sidebarItems={[
        { key: "search", label: "搜索与筛选", active: true },
        { key: "table", label: "表格与工具条" },
        { key: "actions", label: "行级动作" },
      ]}
      breadcrumb="首页 / 当前模块 / 列表页"
      userName="prototype-owner"
      userRole="评审环境"
      userAvatarLabel="列表"
    >
      <div className="prototype-shell-hero">
        <div className="prototype-shell-hero-copy">
          <span className="prototype-shell-kicker">List Archetype</span>
          <Title level={2} className="prototype-shell-hero-title">
            列表页模板
          </Title>
          <Typography.Paragraph className="prototype-shell-hero-desc">
            适合承接中后台模块的查询、筛选、批量操作与行级动作。后续替换字段、状态字典和按钮文案即可快速转成业务页。
          </Typography.Paragraph>
        </div>
        <div className="prototype-shell-metrics">
          <div className="prototype-shell-metric">
            <span className="prototype-shell-metric-label">默认操作区</span>
            <strong className="prototype-shell-metric-value">查询 + 工具条</strong>
          </div>
          <div className="prototype-shell-metric">
            <span className="prototype-shell-metric-label">默认数据量</span>
            <strong className="prototype-shell-metric-value">{data.length} 条</strong>
          </div>
        </div>
      </div>

      <Card className="prototype-shell-card" bordered={false}>
        <div className="prototype-shell-stack">
          <div className="prototype-shell-toolbar">
            <div className="prototype-shell-toolbar-meta">
              <Text strong>结果列表</Text>
              <Text className="prototype-shell-toolbar-note">建议把主操作放在表格上方，避免分散到行内。</Text>
            </div>
            <Space>
              <Button>导出</Button>
              <Button type="primary">新增</Button>
            </Space>
          </div>

          <Form form={form} layout="vertical" className="prototype-shell-query-grid">
            <Form.Item name="keyword" label="关键字">
              <Input placeholder="输入关键字" allowClear />
            </Form.Item>
            <Form.Item name="status" label="状态">
              <Select
                allowClear
                placeholder="全部状态"
                options={[
                  { value: "active", label: "启用" },
                  { value: "inactive", label: "停用" },
                ]}
              />
            </Form.Item>
            <div className="prototype-shell-query-actions">
              <Space>
                <Button type="primary">查询</Button>
                <Button onClick={() => form.resetFields()}>重置</Button>
              </Space>
            </div>
          </Form>

          <Table<Row>
            rowKey="id"
            dataSource={data}
            pagination={{ pageSize: 10 }}
            columns={[
              { title: "名称", dataIndex: "name" },
              {
                title: "状态",
                dataIndex: "status",
                render: (v: Row["status"]) =>
                  v === "active" ? <Tag color="green">启用</Tag> : <Tag>停用</Tag>,
              },
              { title: "更新时间", dataIndex: "updatedAt" },
              {
                title: "操作",
                key: "actions",
                render: () => (
                  <Space>
                    <Button type="link">查看</Button>
                    <Button type="link">编辑</Button>
                    <Button type="link" danger>
                      删除
                    </Button>
                  </Space>
                ),
              },
            ]}
          />
        </div>
      </Card>
    </PrototypeShell>
  );
};

export default PageListTemplate;
