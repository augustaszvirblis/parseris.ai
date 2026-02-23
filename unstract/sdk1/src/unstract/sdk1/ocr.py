import logging
from typing import Any

from unstract.sdk1.adapters.constants import Common
from unstract.sdk1.adapters.ocr import adapters
from unstract.sdk1.adapters.ocr.ocr_adapter import OCRAdapter
from unstract.sdk1.constants import LogLevel
from unstract.sdk1.exceptions import SdkError
from unstract.sdk1.file_storage import FileStorage, FileStorageProvider
from unstract.sdk1.platform import PlatformHelper
from unstract.sdk1.tool.base import BaseTool

logger = logging.getLogger(__name__)


class OCR:
    """Wrapper for OCR adapters, following the same pattern as X2Text."""

    def __init__(
        self,
        tool: BaseTool,
        adapter_instance_id: str | None = None,
    ) -> None:
        self._tool = tool
        self._ocr_adapters = adapters
        self._adapter_instance_id = adapter_instance_id
        self._ocr_instance: OCRAdapter | None = None
        self._initialise()

    @property
    def ocr_instance(self) -> OCRAdapter | None:
        return self._ocr_instance

    def _initialise(self) -> None:
        if self._adapter_instance_id:
            self._ocr_instance = self._get_ocr()

    def _get_ocr(self) -> OCRAdapter:
        try:
            if not self._adapter_instance_id:
                raise SdkError("OCR adapter instance ID not set.")

            ocr_config = PlatformHelper.get_adapter_config(
                self._tool, self._adapter_instance_id
            )
            ocr_adapter_id = ocr_config.get(Common.ADAPTER_ID)
            if ocr_adapter_id in self._ocr_adapters:
                ocr_adapter_class = self._ocr_adapters[ocr_adapter_id][
                    Common.METADATA
                ][Common.ADAPTER]
                ocr_metadata = ocr_config.get(Common.ADAPTER_METADATA)
                self._ocr_instance = ocr_adapter_class(ocr_metadata)
                return self._ocr_instance
            else:
                raise SdkError(
                    f"Unknown or unsupported OCR adapter_id: {ocr_adapter_id}."
                )
        except Exception as e:
            self._tool.stream_log(
                log=f"Unable to get OCR adapter {self._adapter_instance_id}: {e}",
                level=LogLevel.ERROR,
            )
            raise SdkError(f"Error getting OCR adapter: {e}") from e

    def process(
        self,
        input_file_path: str,
        output_file_path: str | None = None,
        fs: FileStorage | None = None,
    ) -> str:
        if self._ocr_instance is None:
            raise SdkError("OCR adapter not initialized.")
        if fs is None:
            fs = FileStorage(provider=FileStorageProvider.LOCAL)
        return self._ocr_instance.process(
            input_file_path=input_file_path,
            output_file_path=output_file_path,
            fs=fs,
        )
