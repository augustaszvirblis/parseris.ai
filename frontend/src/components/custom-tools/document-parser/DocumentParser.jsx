import PropTypes from "prop-types";
import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { Button, Space } from "antd";
import { DownloadOutlined } from "@ant-design/icons";
import { saveAs } from "file-saver";
import * as XLSX from "xlsx";

import "./DocumentParser.css";
import {
  normalizeTableDataForExcel,
  promptType,
} from "../../../helpers/GetStaticData";
import { useAxiosPrivate } from "../../../hooks/useAxiosPrivate";
import { useAlertStore } from "../../../store/alert-store";
import { useCustomToolStore } from "../../../store/custom-tool-store";
import { useSessionStore } from "../../../store/session-store";
import { EmptyState } from "../../widgets/empty-state/EmptyState";
import { useExceptionHandler } from "../../../hooks/useExceptionHandler";
import { PromptCardWrapper } from "../prompt-card/PromptCardWrapper";
import { usePromptOutputStore } from "../../../store/prompt-output-store";

let promptCardService;
let promptPatchApiSps;
let SpsPromptsEmptyState;
try {
  promptCardService =
    require("../../../plugins/prompt-card/prompt-card-service").promptCardService;
  promptPatchApiSps =
    require("../../../plugins/simple-prompt-studio/helper").promptPatchApiSps;
  SpsPromptsEmptyState =
    require("../../../plugins/simple-prompt-studio/SpsPromptsEmptyState").SpsPromptsEmptyState;
} catch {
  // The component will remain null of it is not available
}

function isTableLikeData(data) {
  return (
    Array.isArray(data) &&
    data.length > 0 &&
    data.every(
      (item) =>
        item !== null &&
        item !== undefined &&
        typeof item === "object" &&
        !Array.isArray(item)
    )
  );
}

function getTableDataFromOutput(parsedOutput) {
  let data = parsedOutput;
  if (typeof data === "string") {
    try {
      data = JSON.parse(data);
    } catch {
      return null;
    }
  }
  if (isTableLikeData(data)) return data;
  if (
    typeof data === "object" &&
    data !== null &&
    !Array.isArray(data) &&
    Object.keys(data).length === 1
  ) {
    const val = Object.values(data)[0];
    if (isTableLikeData(val)) return val;
  }
  return null;
}

function DocumentParser({
  addPromptInstance,
  scrollToBottom,
  setScrollToBottom,
}) {
  const [enforceTypeList, setEnforceTypeList] = useState([]);
  const [updatedPromptsCopy, setUpdatedPromptsCopy] = useState({});
  const [isChallenge, setIsChallenge] = useState(false);
  const [allTableSettings, setAllTableSettings] = useState([]);
  const bottomRef = useRef(null);
  const {
    details,
    isSimplePromptStudio,
    updateCustomTool,
    getDropdownItems,
    isChallengeEnabled,
    isPublicSource,
    selectedDoc,
  } = useCustomToolStore();
  const { sessionDetails } = useSessionStore();
  const { setAlertDetails } = useAlertStore();
  const axiosPrivate = useAxiosPrivate();
  const handleException = useExceptionHandler();
  const { promptOutputs } = usePromptOutputStore();
  const { pathname } = useLocation();
  let promptCardApiService;

  useEffect(() => {
    const isSimpleRoute =
      pathname.startsWith("/simple-prompt-studio") ||
      pathname.includes("simple-prompt-studio");
    if (isSimpleRoute) {
      updateCustomTool({ isSimplePromptStudio: true });
    }
  }, [pathname, updateCustomTool]);

  if (promptCardService && !isPublicSource) {
    promptCardApiService = promptCardService();
  }

  useEffect(() => {
    const outputTypeData = getDropdownItems("output_type") || {};
    const dropdownList1 = Object.keys(outputTypeData)?.map((item) => {
      return { value: outputTypeData[item] };
    });
    setEnforceTypeList(dropdownList1);
    setIsChallenge(isChallengeEnabled);
    if (promptCardApiService) {
      promptCardApiService
        .getAllTableSettings()
        .then((res) => {
          const data = res?.data;
          setAllTableSettings(data || []);
        })
        .catch((err) => {
          setAlertDetails(handleException(err));
        });
    }
    return () => {
      // Set the prompts with updated changes when the component is unmounted
      const modifiedDetails = { ...useCustomToolStore.getState()?.details };
      const modifiedPrompts = [...(modifiedDetails?.prompts || [])]?.map(
        (item) => {
          const itemPromptId = item?.prompt_id;
          if (itemPromptId && updatedPromptsCopy[itemPromptId]) {
            return updatedPromptsCopy[itemPromptId];
          }
          return item;
        }
      );
      modifiedDetails["prompts"] = modifiedPrompts;
      updateCustomTool({ details: modifiedDetails });
    };
  }, []);

  useEffect(() => {
    setIsChallenge(details.enable_challenge);
  }, [details.enable_challenge]);

  useEffect(() => {
    if (scrollToBottom) {
      // Scroll down to the lastest chat.
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
      setScrollToBottom(false);
    }
  }, [scrollToBottom]);

  const promptUrl = (urlPath) => {
    return `/api/v1/unstract/${sessionDetails?.orgId}/prompt-studio/prompt/${urlPath}`;
  };

  const handleChangePromptCard = async (name, value, promptId) => {
    const promptsAndNotes = details?.prompts || [];

    if (name === "prompt_key") {
      // Return if the prompt or the prompt key is empty
      if (!value) {
        return;
      }
    }

    // Mark that changes have been made when any prompt field is modified
    const { setHasUnsavedChanges } = useCustomToolStore.getState();
    setHasUnsavedChanges(true);

    const index = promptsAndNotes.findIndex(
      (item) => item?.prompt_id === promptId
    );

    if (index === -1) {
      setAlertDetails({
        type: "error",
        content: "Prompt not found",
      });
      return;
    }

    const promptDetails = promptsAndNotes[index];

    const body = {
      [`${name}`]: value,
    };

    let url = promptUrl(promptDetails?.prompt_id + "/");
    if (isSimplePromptStudio) {
      url = promptPatchApiSps(promptDetails?.prompt_id);
    }
    const requestOptions = {
      method: "PATCH",
      url,
      headers: {
        "X-CSRFToken": sessionDetails?.csrfToken,
        "Content-Type": "application/json",
      },
      data: body,
    };

    return axiosPrivate(requestOptions)
      .then((res) => {
        // Update the store with the modified prompt
        const updatedPrompt = res?.data;
        if (updatedPrompt) {
          const modifiedDetails = { ...details };
          const modifiedPrompts = [...(modifiedDetails?.prompts || [])];
          const promptIndex = modifiedPrompts.findIndex(
            (item) => item?.prompt_id === promptId
          );
          if (promptIndex !== -1) {
            modifiedPrompts[promptIndex] = updatedPrompt;
            modifiedDetails["prompts"] = modifiedPrompts;
            updateCustomTool({ details: modifiedDetails });
          }
        }
        return res;
      })
      .catch((err) => {
        setAlertDetails(handleException(err, "Failed to update"));
      });
  };

  const handleDelete = (promptId) => {
    let url = promptUrl(promptId + "/");
    if (isSimplePromptStudio) {
      url = promptPatchApiSps(promptId);
    }
    const requestOptions = {
      method: "DELETE",
      url,
      headers: {
        "X-CSRFToken": sessionDetails?.csrfToken,
      },
    };

    axiosPrivate(requestOptions)
      .then(() => {
        const modifiedDetails = { ...details };
        const modifiedPrompts = [...(modifiedDetails?.prompts || [])].filter(
          (item) => item?.prompt_id !== promptId
        );
        modifiedDetails["prompts"] = modifiedPrompts;
        updateCustomTool({ details: modifiedDetails });
      })
      .catch((err) => {
        setAlertDetails(handleException(err, "Failed to delete"));
      });
  };

  const getPromptOutputs = (promptId) => {
    const keys = Object.keys(promptOutputs || {});

    if (!keys?.length) return {};

    const outputs = {};
    keys.forEach((key) => {
      if (key.startsWith(promptId)) {
        outputs[key] = promptOutputs[key];
      }
    });
    return outputs;
  };

  // Collect table-like data from all prompt outputs for the selected document (for Export to Excel)
  const getAggregatedTableData = () => {
    const docId = selectedDoc?.document_id;
    if (!docId || !promptOutputs) return null;
    const allRows = [];
    (details?.prompts || []).forEach((prompt) => {
      const outputs = getPromptOutputs(prompt?.prompt_id);
      Object.entries(outputs || {}).forEach(([key, entry]) => {
        const keyParts = key.split("__");
        if (keyParts[1] !== docId) return;
        const tableData = getTableDataFromOutput(entry?.output);
        if (tableData?.length) allRows.push(...tableData);
      });
    });
    return allRows.length ? allRows : null;
  };

  const aggregatedTableData = getAggregatedTableData();

  const handleExportExcel = () => {
    const wb = XLSX.utils.book_new();
    const rawData =
      aggregatedTableData && aggregatedTableData.length > 0
        ? aggregatedTableData
        : [
            {
              "No data": "Run prompts and ensure JSON/table output to export.",
            },
          ];
    const data = normalizeTableDataForExcel(rawData);
    const ws = XLSX.utils.json_to_sheet(data);
    XLSX.utils.book_append_sheet(wb, ws, "Sheet1");
    const wbout = XLSX.write(wb, { bookType: "xlsx", type: "array" });
    const blob = new Blob([wbout], {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    saveAs(blob, "prompt-export.xlsx");
  };

  if (!details?.prompts?.length) {
    if (isSimplePromptStudio && SpsPromptsEmptyState) {
      return <SpsPromptsEmptyState />;
    }

    return (
      <EmptyState
        text="Add prompt or a note and choose the LLM profile"
        btnText="Add Prompt"
        handleClick={() => addPromptInstance(promptType.prompt)}
      />
    );
  }

  return (
    <>
      <div className="doc-parser-export-header">
        <Space>
          <Button
            type="primary"
            icon={<DownloadOutlined />}
            onClick={handleExportExcel}
            size="small"
          >
            Export to Excel
          </Button>
        </Space>
      </div>
      <div className="doc-parser-layout">
        {details?.prompts?.map((item) => {
          return (
            <div key={item.prompt_id}>
              <div className="doc-parser-pad-top" />
              <PromptCardWrapper
                item={item}
                handleChangePromptCard={handleChangePromptCard}
                handleDelete={handleDelete}
                outputs={getPromptOutputs(item?.prompt_id)}
                enforceTypeList={enforceTypeList}
                allTableSettings={allTableSettings}
                setAllTableSettings={setAllTableSettings}
                setUpdatedPromptsCopy={setUpdatedPromptsCopy}
                coverageCountData={item?.coverage}
                isChallenge={isChallenge}
              />
              <div ref={bottomRef} className="doc-parser-pad-bottom" />
            </div>
          );
        })}
      </div>
    </>
  );
}

DocumentParser.propTypes = {
  addPromptInstance: PropTypes.func.isRequired,
  scrollToBottom: PropTypes.bool.isRequired,
  setScrollToBottom: PropTypes.func.isRequired,
};

export { DocumentParser };
