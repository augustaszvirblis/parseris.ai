import { LeftOutlined, RightOutlined } from "@ant-design/icons";
import { Button, Layout } from "antd";
import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import PropTypes from "prop-types";
import "./PageLayout.css";

import SideNavBar from "../../components/navigations/side-nav-bar/SideNavBar.jsx";
import { TopNavBar } from "../../components/navigations/top-nav-bar/TopNavBar.jsx";
import { DisplayLogsAndNotifications } from "../../components/logs-and-notifications/DisplayLogsAndNotifications.jsx";

/**
 * True when current route is Prompt Studio (tools or agentic-prompt-studio).
 * @param {string} pathname - Current location pathname
 * @return {boolean}
 */
function isPromptStudioRoute(pathname) {
  const segments = pathname.split("/").filter(Boolean);
  const secondSegment = segments[1];
  return secondSegment === "tools" || secondSegment === "agentic-prompt-studio";
}

function PageLayout({
  sideBarOptions,
  topNavBarOptions,
  showLogsAndNotifications = true,
  hideSidebar = false,
}) {
  const location = useLocation();
  const promptStudioOnly =
    hideSidebar || isPromptStudioRoute(location.pathname ?? "");
  const initialCollapsedValue =
    JSON.parse(localStorage.getItem("collapsed")) || false;
  const [collapsed, setCollapsed] = useState(initialCollapsedValue);
  useEffect(() => {
    localStorage.setItem("collapsed", JSON.stringify(collapsed));
  }, [collapsed]);
  return (
    <div className="landingPage">
      <TopNavBar topNavBarOptions={topNavBarOptions} />
      <Layout>
        {!promptStudioOnly && (
          <SideNavBar collapsed={collapsed} {...sideBarOptions} />
        )}
        <Layout>
          {!promptStudioOnly && (
            <Button
              shape="circle"
              size="small"
              icon={collapsed ? <RightOutlined /> : <LeftOutlined />}
              onClick={() => setCollapsed(!collapsed)}
              className="collapse_btn"
            />
          )}
          <Outlet />
          {!promptStudioOnly && <div className="height-40" />}
          {showLogsAndNotifications && !promptStudioOnly && (
            <DisplayLogsAndNotifications />
          )}
        </Layout>
      </Layout>
    </div>
  );
}
PageLayout.propTypes = {
  sideBarOptions: PropTypes.any,
  topNavBarOptions: PropTypes.any,
  showLogsAndNotifications: PropTypes.bool,
  hideSidebar: PropTypes.bool,
};

export { PageLayout };
