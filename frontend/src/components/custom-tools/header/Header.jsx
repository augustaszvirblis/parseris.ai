import { SettingOutlined } from "@ant-design/icons";
import { Button, Tooltip, Typography } from "antd";
import PropTypes from "prop-types";

import config from "../../../config";
import { HeaderTitle } from "../header-title/HeaderTitle.jsx";
import { useCustomToolStore } from "../../../store/custom-tool-store";
import "./Header.css";

let SinglePassToggleSwitch;
let CloneButton;
try {
  SinglePassToggleSwitch =
    require("../../../plugins/single-pass-toggle-switch/SinglePassToggleSwitch").SinglePassToggleSwitch;
} catch {
  // The variable will remain undefined if the component is not available.
}
try {
  CloneButton =
    require("../../../plugins/prompt-studio-clone/clone-btn/CloneButton.jsx").CloneButton;
} catch {
  // The variable will remain undefined if the component is not available.
}
function Header({
  setOpenSettings,
  handleUpdateTool,
  setOpenShareModal,
  setOpenCloneModal,
}) {
  const { details, isPublicSource } = useCustomToolStore();

  return (
    <div className="custom-tools-header-layout">
      {isPublicSource ? (
        <div>
          <Typography.Text className="custom-tools-name" strong>
            {details?.tool_name}
          </Typography.Text>
        </div>
      ) : (
        <HeaderTitle />
      )}
      <div className="custom-tools-header-btns">
        {SinglePassToggleSwitch && (
          <SinglePassToggleSwitch handleUpdateTool={handleUpdateTool} />
        )}
        {config.logoText && (
          <Typography.Text
            type="secondary"
            style={{ marginRight: 8, fontSize: 13 }}
          >
            First, add a LLM profile
          </Typography.Text>
        )}
        <div>
          <Tooltip title="Settings">
            <Button
              icon={<SettingOutlined />}
              onClick={() => setOpenSettings(true)}
            />
          </Tooltip>
        </div>
        {CloneButton && <CloneButton setOpenCloneModal={setOpenCloneModal} />}
      </div>
    </div>
  );
}

Header.propTypes = {
  setOpenSettings: PropTypes.func.isRequired,
  handleUpdateTool: PropTypes.func.isRequired,
  setOpenCloneModal: PropTypes.func.isRequired,
  setOpenShareModal: PropTypes.func.isRequired,
};

export { Header };
