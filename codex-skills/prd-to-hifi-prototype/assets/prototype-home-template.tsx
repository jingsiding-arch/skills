import React from "react";
import { Button, Card, Col, Row, Space, Tag, Typography } from "antd";
import PrototypeShell from "./prototype-shell";
import "./prototype-shell.css";

const { Paragraph, Text, Title } = Typography;

type PrototypeRoute = Readonly<{
  key: string;
  title: string;
  description: string;
  priority: "P0" | "P1" | "P2";
}>;

const desktopRoutes: PrototypeRoute[] = [
  { key: "list", title: "列表页", description: "承接查询、筛选、批量操作与行级动作。", priority: "P0" },
  { key: "detail", title: "详情页", description: "承接信息查看、状态展示与关键操作。", priority: "P0" },
  { key: "flow", title: "流程页", description: "承接审批、流转、留痕与异常分支。", priority: "P1" },
];

const mobileRoutes: PrototypeRoute[] = [
  { key: "mobile-list", title: "移动端列表", description: "承接任务列表、轻筛选、状态切换。", priority: "P0" },
  { key: "mobile-detail", title: "移动端详情", description: "承接卡片式信息展示与底部动作。", priority: "P1" },
];

const priorityColorMap: Record<PrototypeRoute["priority"], string> = {
  P0: "blue",
  P1: "gold",
  P2: "default",
};

const topNavItems = [
  { key: "home", label: "首页" },
  { key: "student", label: "学工" },
  { key: "attendance", label: "课堂考勤" },
  { key: "prototype", label: "原型导航" },
];

const sidebarItems = [
  { key: "scope", label: "P0 演示闭环", active: true },
  { key: "desktop", label: "PC 管理端页面" },
  { key: "mobile", label: "移动端页面" },
];

const renderRouteGroup = (title: string, routes: PrototypeRoute[]) => (
  <Card title={title} className="prototype-shell-card">
    <div className="prototype-shell-route-grid">
      {routes.map((route, index) => (
        <button key={route.key} type="button" className="prototype-shell-route-link">
          <div className="prototype-shell-route-main">
            <span className="prototype-shell-route-index">{String(index + 1).padStart(2, "0")}</span>
            <div className="prototype-shell-route-copy">
              <Text strong>{route.title}</Text>
              <p>{route.description}</p>
            </div>
          </div>
          <div className="prototype-shell-route-meta">
            <Tag color={priorityColorMap[route.priority]}>{route.priority}</Tag>
            <span className="prototype-shell-route-arrow" aria-hidden="true">
              ↗
            </span>
          </div>
        </button>
      ))}
    </div>
  </Card>
);

const PrototypeHomeTemplate: React.FC = () => {
  return (
    <PrototypeShell
      brandTitle="模块原型工作台"
      brandSubtitle="可复用的管理端/移动端原型导航壳层"
      brandMark="PT"
      topNavItems={topNavItems}
      activeTopNavKey="prototype"
      sidebarTitle="原型首页"
      sidebarBadge="Shared Prototype Shell"
      sidebarItems={sidebarItems}
      sidebarLinks={[
        { key: "p0", title: "首页导航", note: "汇总各页面入口，便于评审切页。", active: true },
        { key: "style", title: "通用样式", note: "顶部导航、侧边栏、Hero、工具条。", active: false },
      ]}
      breadcrumb="首页 / 模块原型 / 原型导航"
      userName="prototype-owner"
      userRole="评审环境"
      userAvatarLabel="原型"
    >
      <div className="prototype-shell-hero">
        <div className="prototype-shell-hero-copy">
          <span className="prototype-shell-kicker">Prototype Shell</span>
          <Title level={2} className="prototype-shell-hero-title">
            原型首页模板
          </Title>
          <Paragraph className="prototype-shell-hero-desc">
            这套首页模板抽出了课堂考勤里已经验证过的导航壳层、信息面板和路由卡片，适合用来承接一个模块下的页面入口、优先级和演示路径。
          </Paragraph>
          <Space className="prototype-shell-hero-actions">
            <Button type="primary">打开 P0 页面</Button>
            <Button>查看路由规划</Button>
          </Space>
        </div>
        <div className="prototype-shell-metrics">
          <div className="prototype-shell-metric">
            <span className="prototype-shell-metric-label">默认页面群组</span>
            <strong className="prototype-shell-metric-value">2 组</strong>
          </div>
          <div className="prototype-shell-metric">
            <span className="prototype-shell-metric-label">推荐首页结构</span>
            <strong className="prototype-shell-metric-value">导航 + 路由</strong>
          </div>
          <div className="prototype-shell-metric">
            <span className="prototype-shell-metric-label">适用场景</span>
            <strong className="prototype-shell-metric-value">管理端原型</strong>
          </div>
          <div className="prototype-shell-metric">
            <span className="prototype-shell-metric-label">来源</span>
            <strong className="prototype-shell-metric-value">课堂考勤抽取</strong>
          </div>
        </div>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={12}>
          {renderRouteGroup("PC 管理端页面", desktopRoutes)}
        </Col>
        <Col xs={24} xl={12}>
          {renderRouteGroup("移动端功能页", mobileRoutes)}
        </Col>
      </Row>
    </PrototypeShell>
  );
};

export default PrototypeHomeTemplate;
