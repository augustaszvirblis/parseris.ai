"""Vision-based table extraction: document (PDF) -> OpenAI vision -> structured table.

Uses the raw document (no x2text). Converts PDF pages to images and calls
a vision-capable LLM to extract tabular data as JSON.
"""

import base64
import json
import logging
from typing import Any

import litellm

from unstract.core.flask.exceptions import APIError
from unstract.prompt_service.constants import PromptServiceConstants as PSKeys

logger = logging.getLogger(__name__)


class VisionTableExtractionService:
    """Extract table data from a document using a vision-capable LLM (e.g. OpenAI)."""

    SYSTEM_PROMPT = (
        "You are an expert at extracting structured tabular data from documents. "
        "Return only valid JSON. If the document contains a table, return an array of "
        "row objects. If there are multiple tables, return a JSON object with keys "
        "identifying each table and values as arrays of row objects. "
        "Do not include any explanation, only the JSON."
    )

    @staticmethod
    def _pdf_to_base64_images(file_bytes: bytes) -> list[str]:
        """Convert PDF bytes to a list of base64 data URLs (one per page)."""
        try:
            import fitz  # PyMuPDF
        except ImportError as e:
            raise APIError(
                message="Vision table extraction requires pymupdf. Install with: pip install pymupdf",
                code=500,
            ) from e
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        images = []
        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                pix = page.get_pixmap(dpi=150, alpha=False)
                img_bytes = pix.tobytes("png")
                b64 = base64.standard_b64encode(img_bytes).decode("ascii")
                images.append(f"data:image/png;base64,{b64}")
        finally:
            doc.close()
        return images

    @staticmethod
    def _build_vision_messages(
        instruction: str, image_data_urls: list[str]
    ) -> list[dict[str, Any]]:
        """Build messages for vision completion: text instruction + image(s)."""
        content: list[dict[str, Any]] = [{"type": "text", "text": instruction}]
        for url in image_data_urls:
            content.append({"type": "image_url", "image_url": {"url": url}})
        return [
            {"role": "system", "content": VisionTableExtractionService.SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ]

    @staticmethod
    def _parse_json_from_response(text: str) -> Any:
        """Extract and parse JSON from LLM response (may be wrapped in markdown)."""
        text = (text or "").strip()
        # Try to find JSON block
        start = text.find("[")
        if start == -1:
            start = text.find("{")
        if start == -1:
            raise APIError(
                message="Vision extraction did not return valid JSON.",
                code=500,
            )
        depth = 0
        open_char = text[start]
        close_char = "]" if open_char == "[" else "}"
        end = start
        for i in range(start, len(text)):
            if text[i] == open_char:
                depth += 1
            elif text[i] == close_char:
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        json_str = text[start:end]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning("JSON parse failed, trying json_repair: %s", e)
            try:
                from unstract.prompt_service.utils.json_repair_helper import (
                    repair_json_with_best_structure,
                )
                return repair_json_with_best_structure(json_str)
            except Exception as repair_e:
                raise APIError(
                    message=f"Vision extraction returned invalid JSON: {repair_e}",
                    code=500,
                ) from repair_e

    @staticmethod
    def run(
        file_path: str,
        fs_instance: Any,
        llm: Any,
        prompt: str,
        tool_settings: dict[str, Any],
        execution_source: str,
    ) -> Any:
        """Run vision-based table extraction on the document at file_path.

        Args:
            file_path: Path to the raw document (e.g. PDF).
            fs_instance: File storage instance to read the file.
            llm: SDK LLM instance (adapter must be vision-capable, e.g. OpenAI gpt-4o).
            prompt: User prompt/schema describing what to extract.
            tool_settings: Dict with preamble, postamble, etc.
            execution_source: Execution source for logging.

        Returns:
            Extracted data as list or dict (parsed JSON).
        """
        if not fs_instance.exists(file_path):
            raise FileNotFoundError(f"Document not found: {file_path}")

        file_bytes = fs_instance.read(path=file_path, mode="rb")
        if not file_bytes or len(file_bytes) == 0:
            raise APIError(message="Document is empty.", code=400)

        # Support PDF only for now
        if not file_path.lower().endswith(".pdf"):
            raise APIError(
                message="Vision table extraction currently supports PDF only.",
                code=400,
            )

        image_urls = VisionTableExtractionService._pdf_to_base64_images(file_bytes)
        if not image_urls:
            raise APIError(message="PDF produced no pages.", code=400)

        preamble = tool_settings.get(PSKeys.PREAMBLE, "")
        postamble = tool_settings.get(PSKeys.POSTAMBLE, "")
        instruction_parts = [p for p in (preamble, prompt, postamble) if p]
        instruction = "\n\n".join(instruction_parts).strip() or "Extract all tabular data from this document as JSON."

        messages = VisionTableExtractionService._build_vision_messages(
            instruction, image_urls
        )

        # Call litellm with the same adapter config as the SDK LLM
        completion_kwargs = dict(llm.kwargs)
        # litellm expects 'model' and provider-specific keys
        try:
            response = litellm.completion(
                messages=messages,
                **completion_kwargs,
            )
        except Exception as e:
            logger.exception("Vision table extraction LLM call failed: %s", e)
            raise APIError(
                message=f"Vision extraction failed: {getattr(e, 'message', str(e))}",
                code=getattr(e, "status_code", 500),
            ) from e

        response_text = (
            response.get("choices", [{}])[0].get("message", {}).get("content") or ""
        )
        return VisionTableExtractionService._parse_json_from_response(response_text)
