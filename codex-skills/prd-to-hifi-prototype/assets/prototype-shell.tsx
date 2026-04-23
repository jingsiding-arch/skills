import React from "react";
import type { ReactNode } from "react";

export type PrototypeTopNavItem = {
  key: string;
  label: string;
  onClick?: () => void;
};

export type PrototypeSidebarItem = {
  key: string;
  label: string;
  active?: boolean;
  onClick?: () => void;
};

export type PrototypeSidebarLink = {
  key: string;
  title: string;
  note?: string;
  active?: boolean;
  onClick?: () => void;
};

type PrototypeShellProps = {
  brandTitle: string;
  brandSubtitle?: string;
  brandMark?: string;
  topNavItems?: PrototypeTopNavItem[];
  activeTopNavKey?: string;
  sidebarTitle: string;
  sidebarBadge?: string;
  sidebarItems?: PrototypeSidebarItem[];
  sidebarLinks?: PrototypeSidebarLink[];
  breadcrumb: string;
  userName?: string;
  userRole?: string;
  userAvatarLabel?: string;
  children: ReactNode;
};

const renderAvatarLabel = (userAvatarLabel?: string, userName?: string) => {
  if (userAvatarLabel) return userAvatarLabel;
  return (userName || "原型").slice(0, 2);
};

export const PrototypeShell: React.FC<PrototypeShellProps> = ({
  brandTitle,
  brandSubtitle = "Prototype Workspace",
  brandMark = "PR",
  topNavItems = [],
  activeTopNavKey,
  sidebarTitle,
  sidebarBadge,
  sidebarItems = [],
  sidebarLinks = [],
  breadcrumb,
  userName = "prototype-owner",
  userRole = "评审环境",
  userAvatarLabel,
  children,
}) => {
  return (
    <div className="prototype-shell">
      <header className="prototype-shell-header">
        <div className="prototype-shell-brand">
          <div className="prototype-shell-brand-mark" aria-hidden="true">
            {brandMark}
          </div>
          <div className="prototype-shell-brand-copy">
            <p className="prototype-shell-brand-title">{brandTitle}</p>
            <p className="prototype-shell-brand-subtitle">{brandSubtitle}</p>
          </div>
        </div>

        <nav className="prototype-shell-top-menu" aria-label="模块导航">
          {topNavItems.map((item) => (
            <button
              key={item.key}
              type="button"
              className={item.key === activeTopNavKey ? "prototype-shell-top-menu-item is-active" : "prototype-shell-top-menu-item"}
              onClick={item.onClick}
            >
              {item.label}
            </button>
          ))}
        </nav>

        <div className="prototype-shell-user">
          <div className="prototype-shell-user-avatar">{renderAvatarLabel(userAvatarLabel, userName)}</div>
          <div className="prototype-shell-user-copy">
            <span className="prototype-shell-user-name">{userName}</span>
            <span className="prototype-shell-user-role">{userRole}</span>
          </div>
        </div>
      </header>

      <div className="prototype-shell-main">
        <aside className="prototype-shell-sidebar">
          <h2 className="prototype-shell-sidebar-title">{sidebarTitle}</h2>
          {sidebarBadge ? <div className="prototype-shell-sidebar-badge">{sidebarBadge}</div> : null}

          {sidebarItems.length ? (
            <div className="prototype-shell-sidebar-section">
              {sidebarItems.map((item) => (
                <button
                  key={item.key}
                  type="button"
                  className={item.active ? "prototype-shell-sidebar-item is-active" : "prototype-shell-sidebar-item"}
                  onClick={item.onClick}
                >
                  {item.label}
                </button>
              ))}
            </div>
          ) : null}

          {sidebarLinks.length ? (
            <div className="prototype-shell-sidebar-links">
              {sidebarLinks.map((item) => (
                <button
                  key={item.key}
                  type="button"
                  className={item.active ? "prototype-shell-sidebar-link is-active" : "prototype-shell-sidebar-link"}
                  onClick={item.onClick}
                >
                  <span className="prototype-shell-sidebar-link-title">{item.title}</span>
                  {item.note ? <span className="prototype-shell-sidebar-link-note">{item.note}</span> : null}
                </button>
              ))}
            </div>
          ) : null}
        </aside>

        <main className="prototype-shell-content">
          <div className="prototype-shell-panel">
            <div className="prototype-shell-breadcrumb">{breadcrumb}</div>
            <div className="prototype-shell-stack">{children}</div>
          </div>
        </main>
      </div>
    </div>
  );
};

export default PrototypeShell;
