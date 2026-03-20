import React from "react";
import { Button, Card, List, Space, Tag, Typography } from "antd";

const { Paragraph, Text, Title } = Typography;

type PrototypePage = Readonly<{
  key: string;
  title: string;
  description: string;
  priority: "P0" | "P1" | "P2";
  onOpen?: () => void;
}>;

const pages: PrototypePage[] = [
  {
    key: "list",
    title: "列表页",
    description: "承接查询、筛选、批量操作与行级动作。",
    priority: "P0",
  },
  {
    key: "detail",
    title: "详情页",
    description: "承接信息查看、状态展示与关键操作。",
    priority: "P0",
  },
  {
    key: "flow",
    title: "流程页",
    description: "承接审批、流转、留痕与异常分支。",
    priority: "P1",
  },
];

const priorityColorMap: Record<PrototypePage["priority"], string> = {
  P0: "red",
  P1: "gold",
  P2: "blue",
};

const PrototypeHomeTemplate: React.FC = () => {
  return (
    <div style={{ padding: 24 }}>
      <Card bordered={false}>
        <Space direction="vertical" size={20} style={{ width: "100%" }}>
          <div>
            <Title level={3} style={{ marginBottom: 8 }}>
              原型首页模板
            </Title>
            <Paragraph style={{ marginBottom: 0 }}>
              用于承接一个模块下的页面入口，方便评审时快速切页、说明优先级和演示路径。
            </Paragraph>
          </div>

          <List
            dataSource={pages}
            renderItem={(page) => (
              <List.Item
                actions={[
                  <Button key="open" type="primary" onClick={page.onOpen}>
                    打开页面
                  </Button>,
                ]}
              >
                <List.Item.Meta
                  title={
                    <Space size={8}>
                      <span>{page.title}</span>
                      <Tag color={priorityColorMap[page.priority]}>{page.priority}</Tag>
                    </Space>
                  }
                  description={page.description}
                />
                <Text type="secondary">{page.key}</Text>
              </List.Item>
            )}
          />
        </Space>
      </Card>
    </div>
  );
};

export default PrototypeHomeTemplate;
