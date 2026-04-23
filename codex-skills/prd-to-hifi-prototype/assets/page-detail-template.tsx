import React from "react";
import { Button, Card, Descriptions, Space, Tabs, Tag, Timeline, Typography } from "antd";
import PrototypeShell from "./prototype-shell";
import "./prototype-shell.css";

const { Paragraph, Title } = Typography;

const PageDetailTemplate: React.FC = () => {
  return (
    <PrototypeShell
      brandTitle="模块原型工作台"
      brandSubtitle="详情页默认骨架"
      brandMark="DT"
      topNavItems={[
        { key: "home", label: "首页" },
        { key: "module", label: "当前模块" },
        { key: "detail", label: "详情页" },
      ]}
      activeTopNavKey="detail"
      sidebarTitle="详情页模板"
      sidebarBadge="Detail Archetype"
      sidebarItems={[
        { key: "summary", label: "信息概览", active: true },
        { key: "tabs", label: "分区标签" },
        { key: "audit", label: "操作留痕" },
      ]}
      breadcrumb="首页 / 当前模块 / 详情页"
      userName="prototype-owner"
      userRole="评审环境"
      userAvatarLabel="详情"
    >
      <div className="prototype-shell-hero">
        <div className="prototype-shell-hero-copy">
          <span className="prototype-shell-kicker">Detail Archetype</span>
          <Title level={2} className="prototype-shell-hero-title">
            详情页模板
          </Title>
          <Paragraph className="prototype-shell-hero-desc">
            适合承接对象概览、状态信息、主动作与留痕记录。通常搭配列表页使用，作为查看、复核、审批和继续流转的主场景。
          </Paragraph>
          <Space className="prototype-shell-hero-actions">
            <Button>返回列表</Button>
            <Button type="primary">编辑对象</Button>
          </Space>
        </div>
        <div className="prototype-shell-metrics">
          <div className="prototype-shell-metric">
            <span className="prototype-shell-metric-label">默认模块</span>
            <strong className="prototype-shell-metric-value">概览 + 分区</strong>
          </div>
          <div className="prototype-shell-metric">
            <span className="prototype-shell-metric-label">推荐动作位</span>
            <strong className="prototype-shell-metric-value">顶部右侧</strong>
          </div>
        </div>
      </div>

      <Card
        className="prototype-shell-card"
        title="对象概览"
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
      </Card>

      <Card className="prototype-shell-card" bordered={false}>
        <Tabs
          items={[
            { key: "tab1", label: "基础信息", children: <div>这里放字段说明、摘要卡片或配置表单。</div> },
            {
              key: "tab2",
              label: "操作记录",
              children: (
                <Timeline
                  items={[
                    { children: "2026-03-12 10:30 更新对象状态为启用" },
                    { children: "2026-03-12 09:20 创建对象并完成初始配置" },
                  ]}
                />
              ),
            },
          ]}
        />
      </Card>
    </PrototypeShell>
  );
};

export default PageDetailTemplate;
