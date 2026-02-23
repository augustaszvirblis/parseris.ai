import logging
from pathlib import Path
from typing import Any

from unstract.prompt_service.constants import ExecutionSource

logger = logging.getLogger(__name__)
from unstract.prompt_service.constants import IndexingConstants as IKeys
from unstract.prompt_service.exceptions import ExtractionError
from unstract.prompt_service.helpers.prompt_ide_base_tool import PromptServiceBaseTool
from unstract.prompt_service.utils.file_utils import FileUtils
from unstract.sdk1.adapters.exceptions import AdapterError
from unstract.sdk1.adapters.x2text.constants import X2TextConstants
from unstract.sdk1.exceptions import SdkError, X2TextError
from unstract.sdk1.adapters.x2text.llm_whisperer.src import LLMWhisperer
from unstract.sdk1.adapters.x2text.llm_whisperer_v2.src import LLMWhispererV2
from unstract.sdk1.ocr import OCR
from unstract.sdk1.utils.common import log_elapsed
from unstract.sdk1.utils.tool import ToolUtils
from unstract.sdk1.x2txt import TextExtractionResult, X2Text

MIN_EXTRACTED_TEXT_LENGTH = 50

EXTRACTION_HINT_SCANNED_PDF = (
    "No text was extracted from this PDF. If it is a scanned document (image-based), "
    "add an OCR adapter in the tool profile and try again. Native PDF extraction only "
    "works for PDFs with selectable text."
)


class ExtractionService:
    @staticmethod
    @log_elapsed(operation="EXTRACTION")
    def perform_extraction(
        x2text_instance_id: str,
        file_path: str,
        run_id: str,
        platform_key: str,
        ocr_instance_id: str = "",
        output_file_path: str | None = None,
        enable_highlight: bool = False,
        usage_kwargs: dict[Any, Any] = {},
        tags: list[str] | None = None,
        execution_source: str | None = None,
        tool_exec_metadata: dict[str, Any] | None = None,
        execution_run_data_folder: str | None = None,
    ) -> str:
        extracted_text = ""
        try:
            util = PromptServiceBaseTool(platform_key=platform_key)
            x2text = X2Text(
                tool=util,
                adapter_instance_id=x2text_instance_id,
                usage_kwargs=usage_kwargs,
            )
            fs = FileUtils.get_fs_instance(execution_source=execution_source)
        except (X2TextError, ValueError) as e:
            msg = str(e) if str(e) else "Text extractor or storage config error."
            raise ExtractionError(msg, code=400) from e
        except Exception as e:
            msg = str(e) if str(e) else "Failed to initialize extractor."
            raise ExtractionError(msg, code=500) from e

        try:
            if enable_highlight and (
                isinstance(x2text.x2text_instance, LLMWhisperer)
                or isinstance(x2text.x2text_instance, LLMWhispererV2)
            ):
                process_response: TextExtractionResult = x2text.process(
                    input_file_path=file_path,
                    output_file_path=output_file_path,
                    enable_highlight=enable_highlight,
                    tags=tags,
                    fs=fs,
                )
                ExtractionService.update_exec_metadata(
                    fs,
                    execution_source,
                    tool_exec_metadata,
                    execution_run_data_folder,
                    process_response,
                )
            else:
                process_response: TextExtractionResult = x2text.process(
                    input_file_path=file_path,
                    output_file_path=output_file_path,
                    tags=tags,
                    fs=fs,
                )
            extracted_text = process_response.extracted_text

            if (
                ocr_instance_id
                and len((extracted_text or "").strip()) < MIN_EXTRACTED_TEXT_LENGTH
            ):
                logger.info(
                    "X2Text returned near-empty text (%d chars), "
                    "falling back to OCR adapter %s",
                    len((extracted_text or "").strip()),
                    ocr_instance_id,
                )
                extracted_text = ExtractionService._ocr_fallback(
                    util=util,
                    ocr_instance_id=ocr_instance_id,
                    file_path=file_path,
                    output_file_path=output_file_path,
                    fs=fs,
                )

            return extracted_text
        except X2TextError as e:
            msg = str(e) if str(e) else "Text extractor error."
            raise ExtractionError(msg, code=400) from e
        except AdapterError as e:
            adapter_name = x2text.x2text_instance.get_name()
            msg = f"Error from text extractor '{adapter_name}'. {str(e)}"
            if isinstance(x2text.x2text_instance, LLMWhispererV2):
                msg += (
                    " Ensure the LLMWhisperer V2 adapter URL is reachable from this "
                    "service (prompt-service), the API key is set, and the service "
                    "returns result_text."
                )
                logger.error(
                    "Extraction failed for LLMWhisperer V2 (indexing may be affected): %s",
                    e,
                    exc_info=True,
                )
            code = e.status_code if e.status_code != -1 else 500
            raise ExtractionError(msg, code=code) from e
        except (FileNotFoundError, OSError) as e:
            msg = f"File not found or not readable: {file_path}. {e}"
            raise ExtractionError(msg, code=404) from e
        except Exception as e:
            msg = str(e) if str(e) else "Extraction failed."
            raise ExtractionError(msg, code=500) from e

    @staticmethod
    def _ocr_fallback(
        util: PromptServiceBaseTool,
        ocr_instance_id: str,
        file_path: str,
        output_file_path: str | None,
        fs: Any,
    ) -> str:
        try:
            ocr = OCR(tool=util, adapter_instance_id=ocr_instance_id)
            ocr_text = ocr.process(
                input_file_path=file_path,
                output_file_path=output_file_path,
                fs=fs,
            )
            logger.info(
                "OCR fallback produced %d chars of text",
                len((ocr_text or "").strip()),
            )
            return ocr_text
        except (SdkError, AdapterError) as e:
            logger.warning("OCR fallback failed: %s", e)
            raise ExtractionError(
                f"OCR fallback failed: {e}", code=500
            ) from e
        except Exception as e:
            logger.warning("OCR fallback unexpected error: %s", e)
            raise ExtractionError(
                f"OCR fallback failed: {e}", code=500
            ) from e

    @staticmethod
    def get_extraction_hint(
        file_path: str,
        extracted_text: str,
        ocr_instance_id: str,
    ) -> str | None:
        """Return a user-facing hint when extraction is empty/short for a PDF.

        Used to suggest enabling OCR for scanned PDFs.
        """
        if not file_path or not (file_path.lower().endswith(".pdf")):
            return None
        text_len = len((extracted_text or "").strip())
        if text_len >= MIN_EXTRACTED_TEXT_LENGTH:
            return None
        return EXTRACTION_HINT_SCANNED_PDF

    @staticmethod
    def update_exec_metadata(
        fs,
        execution_source,
        tool_exec_metadata,
        execution_run_data_folder,
        process_response,
    ):
        if execution_source == ExecutionSource.TOOL.value:
            whisper_hash_value = process_response.extraction_metadata.whisper_hash
            metadata = {X2TextConstants.WHISPER_HASH: whisper_hash_value}
            for key, value in metadata.items():
                tool_exec_metadata[key] = value
            metadata_path = str(Path(execution_run_data_folder) / IKeys.METADATA_FILE)
            ToolUtils.dump_json(
                file_to_dump=metadata_path,
                json_to_dump=metadata,
                fs=fs,
            )
