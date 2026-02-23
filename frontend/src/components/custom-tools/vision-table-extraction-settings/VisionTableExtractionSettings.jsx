import { Switch, Typography } from "antd";
import PropTypes from "prop-types";
import { useState } from "react";

import { useCustomToolStore } from "../../../store/custom-tool-store";
import { useAlertStore } from "../../../store/alert-store";
import { useExceptionHandler } from "../../../hooks/useExceptionHandler";
import SpaceWrapper from "../../widgets/space-wrapper/SpaceWrapper";

function VisionTableExtractionSettings({ handleUpdateTool }) {
  const { details, updateCustomTool } = useCustomToolStore();
  const { setAlertDetails } = useAlertStore();
  const handleException = useExceptionHandler();
  const [isLoading, setIsLoading] = useState(false);

  const useVisionTableExtraction =
    details?.use_vision_table_extraction ?? false;

  const handleToggle = (checked) => {
    setIsLoading(true);
    handleUpdateTool({ use_vision_table_extraction: checked })
      .then((res) => {
        const updated = res?.data;
        updateCustomTool({
          details: {
            ...details,
            use_vision_table_extraction:
              updated?.use_vision_table_extraction ?? checked,
          },
          useVisionTableExtraction:
            updated?.use_vision_table_extraction ?? checked,
        });
      })
      .catch((err) => {
        setAlertDetails(
          handleException(
            err,
            "Failed to update vision table extraction setting."
          )
        );
      })
      .finally(() => {
        setIsLoading(false);
      });
  };

  return (
    <div className="settings-body-pad-top">
      <SpaceWrapper>
        <Typography.Text strong>Use vision table extraction</Typography.Text>
        <Typography.Paragraph
          type="secondary"
          style={{ marginTop: 4, marginBottom: 12 }}
        >
          When enabled, table (and record) prompts send the raw document (e.g.
          PDF) to a vision-capable LLM (e.g. OpenAI gpt-4o) instead of using
          text extraction (x2text). Best for documents where layout matters. Use
          a vision-capable LLM in your profile.
        </Typography.Paragraph>
        <Switch
          checked={useVisionTableExtraction}
          onChange={handleToggle}
          disabled={isLoading}
          loading={isLoading}
        />
      </SpaceWrapper>
    </div>
  );
}

VisionTableExtractionSettings.propTypes = {
  handleUpdateTool: PropTypes.func.isRequired,
};

export { VisionTableExtractionSettings };
