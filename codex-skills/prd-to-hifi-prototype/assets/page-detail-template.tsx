import React from "react";
import { Button, Card, Descriptions, Space, Tabs, Tag } from "antd";

const PageDetailTemplate: React.FC = () => {
  return (
    <div style={{ padding: 24 }}>
      <Card
        title="详情页模板"
        extra={
          <Space>
            <Button>返回</Button>
            <Button type="primary">编辑</Button>
          </Space>
        }
      >
        <Descriptions bordered size="middle" column={2}>
          <Descriptions.Item label="名称">示例对象</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color="green">启用</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">2026-03-12 09:00</Descriptions.Item>
          <Descriptions.Item label="更新时间">2026-03-12 10:30</Descriptions.Item>
        </Descriptions>

        <Tabs
          style={{ marginTop: 16 }}
          items={[
            { key: "tab1", label: "基础信息", children: <div>这里放表单/字段展示</div> },
            { key: "tab2", label: "操作记录", children: <div>这里放时间线/日志</div> },
          ]}
        />
      </Card>
    </div>
  );
};

export default PageDetailTemplate;
