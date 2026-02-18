"""Native PDF x2text adapter: extracts text from PDFs using pdfplumber (no external service)."""

import io
import logging
from typing import Any

import pdfplumber
from unstract.sdk1.adapters.exceptions import AdapterError
from unstract.sdk1.adapters.x2text.dto import TextExtractionResult
from unstract.sdk1.adapters.x2text.x2text_adapter import X2TextAdapter
from unstract.sdk1.file_storage import FileStorage, FileStorageProvider

logger = logging.getLogger(__name__)


class NativePdfX2Text(X2TextAdapter):
    """Extract text from PDF files using pdfplumber (built-in, no external API)."""

    def __init__(self, settings: dict[str, Any]) -> None:
        super().__init__("Native PDF")
        self.config = settings or {}

    @staticmethod
    def get_id() -> str:
        return "unstract|native_pdf"

    @staticmethod
    def get_name() -> str:
        return "Native PDF"

    @staticmethod
    def get_description() -> str:
        return "Extract text from PDFs using built-in pdfplumber (no external service)."

    @staticmethod
    def get_icon() -> str:
        return "/icons/adapter-icons/native-pdf.png"

    def process(
        self,
        input_file_path: str,
        output_file_path: str | None = None,
        fs: FileStorage | None = None,
        **kwargs: dict[Any, Any],
    ) -> TextExtractionResult:
        if fs is None:
            fs = FileStorage(provider=FileStorageProvider.LOCAL)
        try:
            content = fs.read(path=input_file_path, mode="rb")
        except OSError as e:
            raise AdapterError(f"Failed to read file {input_file_path}: {e}") from e
        try:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                parts = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        parts.append(text)
                extracted_text = "\n".join(parts) if parts else ""
        except Exception as e:
            logger.exception("Native PDF extraction failed for %s", input_file_path)
            raise AdapterError(f"PDF extraction failed: {e}") from e
        if output_file_path:
            try:
                fs.write(
                    path=output_file_path,
                    mode="w",
                    data=extracted_text,
                    encoding="utf-8",
                )
            except OSError as e:
                logger.warning("Could not write output file %s: %s", output_file_path, e)
        return TextExtractionResult(extracted_text=extracted_text)

    def test_connection(self) -> bool:
        return True
