import { LeftOutlined, RightOutlined } from "@ant-design/icons";
import { Button, Drawer, Layout } from "antd";
import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import PropTypes from "prop-types";
import "./PageLayout.css";

import SideNavBar from "../../components/navigations/side-nav-bar/SideNavBar.jsx";
import { TopNavBar } from "../../components/navigations/top-nav-bar/TopNavBar.jsx";
import { DisplayLogsAndNotifications } from "../../components/logs-and-notifications/DisplayLogsAndNotifications.jsx";

const MOBILE_BREAKPOINT = 768;

function useIsMobile() {
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const mql = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT}px)`);
    const update = () => setIsMobile(mql.matches);
    update();
    mql.addEventListener("change", update);
    return () => mql.removeEventListener("change", update);
  }, []);
  return isMobile;
}

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
  const isMobile = useIsMobile();
  const promptStudioOnly =
    hideSidebar || isPromptStudioRoute(location.pathname ?? "");
  const initialCollapsedValue =
    JSON.parse(localStorage.getItem("collapsed")) || false;
  const [collapsed, setCollapsed] = useState(initialCollapsedValue);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    localStorage.setItem("collapsed", JSON.stringify(collapsed));
  }, [collapsed]);

  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  const showSidebar = !promptStudioOnly;
  const showMobileMenuButton = showSidebar && isMobile;

  return (
    <div className="landingPage">
      <TopNavBar
        topNavBarOptions={topNavBarOptions}
        showMobileMenuButton={showMobileMenuButton}
        onOpenMobileMenu={() => setMobileMenuOpen(true)}
      />
      {showMobileMenuButton && (
        <Drawer
          title="Menu"
          placement="left"
          open={mobileMenuOpen}
          onClose={() => setMobileMenuOpen(false)}
          bodyStyle={{ padding: 0 }}
          width={280}
          className="page-layout-mobile-drawer"
        >
          <SideNavBar
            collapsed={false}
            onNavigate={() => setMobileMenuOpen(false)}
            {...sideBarOptions}
          />
        </Drawer>
      )}
      <Layout>
        {showSidebar && !isMobile && (
          <SideNavBar collapsed={collapsed} {...sideBarOptions} />
        )}
        <Layout>
          {showSidebar && !isMobile && (
            <Button
              shape="circle"
              size="small"
              icon={collapsed ? <RightOutlined /> : <LeftOutlined />}
              onClick={() => setCollapsed(!collapsed)}
              className="collapse_btn"
            />
          )}
          <Outlet />
          {showSidebar && <div className="height-40" />}
          {showLogsAndNotifications && showSidebar && (
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
