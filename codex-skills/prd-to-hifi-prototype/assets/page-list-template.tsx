import React, { useMemo, useState } from "react";
import { Button, Card, Form, Input, Space, Table, Tag } from "antd";

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
  const filters = Form.useWatch([], form) as { keyword?: string } | undefined;

  const data = useMemo(() => {
    const keyword = (filters?.keyword || "").trim();
    if (!keyword) return rows;
    return rows.filter((r) => r.name.includes(keyword));
  }, [filters?.keyword, rows]);

  return (
    <div style={{ padding: 24 }}>
      <Card title="列表页模板" extra={<Button type="primary">新增</Button>}>
        <Form form={form} layout="inline" style={{ marginBottom: 12 }}>
          <Form.Item name="keyword" label="关键字">
            <Input placeholder="输入关键字" allowClear style={{ width: 260 }} />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary">查询</Button>
              <Button onClick={() => form.resetFields()}>重置</Button>
            </Space>
          </Form.Item>
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
      </Card>
    </div>
  );
};

export default PageListTemplate;
