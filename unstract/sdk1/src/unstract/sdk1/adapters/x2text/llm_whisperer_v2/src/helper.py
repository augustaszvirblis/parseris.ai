import json
import logging
import time
from io import BytesIO
from pathlib import Path
from typing import Any

import requests
from requests import Response
from requests.exceptions import ConnectionError, HTTPError, Timeout
from unstract.llmwhisperer.client_v2 import (
    LLMWhispererClientException,
    LLMWhispererClientV2,
)
from unstract.sdk1.adapters.exceptions import ExtractorError
from unstract.sdk1.adapters.utils import AdapterUtils
from unstract.sdk1.adapters.x2text.constants import X2TextConstants
from unstract.sdk1.adapters.x2text.llm_whisperer_v2.src.constants import (
    Modes,
    OutputModes,
    WhispererConfig,
    WhispererDefaults,
    WhispererHeader,
    WhispererRetry,
    WhisperStatus,
)
from unstract.sdk1.adapters.x2text.llm_whisperer_v2.src.dto import (
    WhispererRequestParams,
)
from unstract.sdk1.constants import MimeType
from unstract.sdk1.file_storage import FileStorage, FileStorageProvider

logger = logging.getLogger(__name__)


class LLMWhispererHelper:
    @staticmethod
    def get_request_headers(config: dict[str, Any]) -> dict[str, Any]:
        """Obtains the request headers to authenticate with LLMWhisperer.

        Returns:
            str: Request headers
        """
        return {
            "accept": MimeType.JSON,
            WhispererHeader.UNSTRACT_KEY: config.get(WhispererConfig.UNSTRACT_KEY),
        }

    @staticmethod
    def test_connection_request(
        config: dict[str, Any], request_endpoint: str
    ) -> Response:
        llm_whisperer_svc_url = f"{config.get(WhispererConfig.URL)}/api/v2"
        headers = LLMWhispererHelper.get_request_headers(config=config)

        try:
            response: Response
            url = f"{llm_whisperer_svc_url}/{request_endpoint}"
            response = requests.get(url=url, headers=headers)
            response.raise_for_status()
        except ConnectionError as e:
            logger.error("LLMWhisperer V2 test_connection failed: %s", e)
            raise ExtractorError(
                "Unable to connect to LLMWhisperer service. "
                "Check the adapter URL (must be reachable from this service) and API key.",
                actual_err=e,
                status_code=503,
            ) from e
        except Timeout as e:
            msg = "LLMWhisperer test connection timed out. Check URL and service availability."
            logger.error("%s: %s", msg, e)
            raise ExtractorError(msg, actual_err=e, status_code=504) from e
        except HTTPError as e:
            logger.error("LLMWhisperer V2 test_connection HTTP error: %s", e)
            default_err = "Error calling LLMWhisperer service. Check URL and API key."
            msg = AdapterUtils.get_msg_from_request_exc(
                err=e, message_key="message", default_err=default_err
            )
            raise ExtractorError(
                msg, status_code=e.response.status_code, actual_err=e
            ) from e

    @staticmethod
    def make_request(
        config: dict[str, Any],
        headers: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        data: BytesIO | None = None,
        type: str = "whisper",
    ) -> Response:
        """Makes a request to LLMWhisperer service.

        Args:
            config (dict[str, Any]): LLMWhisperer config to use
            headers (Optional[dict[str, Any]], optional): Headers to pass.
                Defaults to None.
            params (Optional[dict[str, Any]], optional): Query params to pass.
                Defaults to None.
            data (Optional[BytesIO], optional): Data to pass in case of POST.
                Defaults to None.
            type (str, optional): Type of request / endpoint in LLMWhisperer.
                Defaults to "whisper".

        Returns:
            Response: Response from the request
        """
        llm_whisperer_svc_url = f"{config.get(WhispererConfig.URL)}/api/v2"
        if not headers:
            headers = LLMWhispererHelper.get_request_headers(config=config)

        try:
            response: dict[str, Any]
            client = LLMWhispererClientV2(
                base_url=llm_whisperer_svc_url,
                api_key=config.get(WhispererConfig.UNSTRACT_KEY),
                logging_level=WhispererDefaults.LOGGING_LEVEL,
            )
            if type == "whisper":
                response = client.whisper(**params, stream=data)
                whisper_hash = response.get(X2TextConstants.WHISPER_HASH_V2, "")
                if whisper_hash:
                    logger.info(f"LLMWhisperer responded, whisper_hash: {whisper_hash}")
                if response["status_code"] == 200:
                    response["extraction"][X2TextConstants.WHISPER_HASH_V2] = (
                        response.get(X2TextConstants.WHISPER_HASH_V2, "")
                    )
                    return response["extraction"]
                else:
                    response["message"] += (
                        ". Whisper hash: "
                        f"{response.get(X2TextConstants.WHISPER_HASH_V2, '')}"
                    )
                    raise ExtractorError(
                        response["message"],
                        response["status_code"],
                        actual_err=response,
                    )
            elif type == "highlight":
                response = client.get_highlight_data(**params)
                return response

        except ConnectionError as e:
            logger.error("LLMWhisperer V2 connection error: %s", e)
            raise ExtractorError(
                "Unable to connect to LLMWhisperer service. "
                "Ensure the adapter URL is reachable from this service (e.g. prompt-service) and the API key is set.",
                actual_err=e,
                status_code=503,
            ) from e
        except Timeout as e:
            msg = (
                "Request to LLMWhisperer has timed out. "
                "Ensure the service is up and consider increasing wait_timeout."
            )
            logger.error("%s: %s", msg, e)
            raise ExtractorError(msg, actual_err=e, status_code=504) from e
        except LLMWhispererClientException as e:
            logger.error("LLM Whisperer error: %s", e)
            raise ExtractorError(
                message=(
                    f"LLM Whisperer error: {e}. "
                    "Check adapter URL and API key (unstract_key)."
                ),
                actual_err=e,
                status_code=500,
            ) from e

        return response

    @staticmethod
    def get_whisperer_params(
        config: dict[str, Any], extra_params: WhispererRequestParams
    ) -> dict[str, Any]:
        """Gets query params meant for /whisper endpoint.

        The params is filled based on the configuration passed.

        Returns:
            dict[str, Any]: Query params
        """
        params = {
            WhispererConfig.MODE: config.get(WhispererConfig.MODE, Modes.FORM.value),
            WhispererConfig.OUTPUT_MODE: config.get(
                WhispererConfig.OUTPUT_MODE, OutputModes.LAYOUT_PRESERVING.value
            ),
            WhispererConfig.LINE_SPLITTER_TOLERANCE: config.get(
                WhispererConfig.LINE_SPLITTER_TOLERANCE,
                WhispererDefaults.LINE_SPLITTER_TOLERANCE,
            ),
            WhispererConfig.LINE_SPLITTER_STRATEGY: config.get(
                WhispererConfig.LINE_SPLITTER_STRATEGY,
                WhispererDefaults.LINE_SPLITTER_STRATEGY,
            ),
            WhispererConfig.HORIZONTAL_STRETCH_FACTOR: config.get(
                WhispererConfig.HORIZONTAL_STRETCH_FACTOR,
                WhispererDefaults.HORIZONTAL_STRETCH_FACTOR,
            ),
            WhispererConfig.PAGES_TO_EXTRACT: config.get(
                WhispererConfig.PAGES_TO_EXTRACT,
                WhispererDefaults.PAGES_TO_EXTRACT,
            ),
            WhispererConfig.MARK_VERTICAL_LINES: config.get(
                WhispererConfig.MARK_VERTICAL_LINES,
                WhispererDefaults.MARK_VERTICAL_LINES,
            ),
            WhispererConfig.MARK_HORIZONTAL_LINES: config.get(
                WhispererConfig.MARK_HORIZONTAL_LINES,
                WhispererDefaults.MARK_HORIZONTAL_LINES,
            ),
            WhispererConfig.PAGE_SEPARATOR: config.get(
                WhispererConfig.PAGE_SEPARATOR,
                WhispererDefaults.PAGE_SEPARATOR,
            ),
            WhispererConfig.ADD_LINE_NOS: extra_params.enable_highlight,
            WhispererConfig.INCLUDE_LINE_CONFIDENCE: extra_params.enable_highlight,
            # Not providing default value to maintain legacy compatablity
            # these are optional params and identifiers for audit
            WhispererConfig.TAG: extra_params.tag
            or config.get(
                WhispererConfig.TAG,
                WhispererDefaults.TAG,
            ),
            WhispererConfig.USE_WEBHOOK: config.get(WhispererConfig.USE_WEBHOOK, ""),
            WhispererConfig.WEBHOOK_METADATA: config.get(
                WhispererConfig.WEBHOOK_METADATA
            ),
            WhispererConfig.WAIT_TIMEOUT: config.get(
                WhispererConfig.WAIT_TIMEOUT,
                WhispererDefaults.WAIT_TIMEOUT,
            ),
            WhispererConfig.WAIT_FOR_COMPLETION: WhispererDefaults.WAIT_FOR_COMPLETION,
        }
        if params[WhispererConfig.MODE] == Modes.LOW_COST.value:
            params.update(
                {
                    WhispererConfig.MEDIAN_FILTER_SIZE: config.get(
                        WhispererConfig.MEDIAN_FILTER_SIZE,
                        WhispererDefaults.MEDIAN_FILTER_SIZE,
                    ),
                    WhispererConfig.GAUSSIAN_BLUR_RADIUS: config.get(
                        WhispererConfig.GAUSSIAN_BLUR_RADIUS,
                        WhispererDefaults.GAUSSIAN_BLUR_RADIUS,
                    ),
                }
            )
        return params

    @staticmethod
    def send_whisper_request(
        input_file_path: str,
        config: dict[str, Any],
        extra_params: WhispererRequestParams,
        fs: FileStorage | None = None,
    ) -> requests.Response:
        if fs is None:
            fs = FileStorage(provider=FileStorageProvider.LOCAL)
        params = LLMWhispererHelper.get_whisperer_params(
            config=config, extra_params=extra_params
        )
        last_error = None
        for attempt in range(1, WhispererRetry.MAX_ATTEMPTS + 1):
            try:
                input_file_data = BytesIO(fs.read(path=input_file_path, mode="rb"))
                enable_highlight = extra_params.enable_highlight
                response = LLMWhispererHelper.make_request(
                    config=config,
                    params=params,
                    data=input_file_data,
                )
                if enable_highlight:
                    whisper_hash = response.get(X2TextConstants.WHISPER_HASH_V2, "")
                    highlight_data = LLMWhispererHelper.make_highlight_data_request(
                        config,
                        whisper_hash,
                        enable_highlight,
                    )
                    response["line_metadata"] = highlight_data
                return response
            except OSError as e:
                logger.error("OS error while reading %s: %s", input_file_path, e)
                raise ExtractorError(str(e)) from e
            except (ConnectionError, Timeout) as e:
                last_error = e
                if attempt < WhispererRetry.MAX_ATTEMPTS:
                    delay = WhispererRetry.BACKOFF_SEC * attempt
                    logger.warning(
                        "LLMWhisperer V2 attempt %s/%s failed (%s), retrying in %ss",
                        attempt,
                        WhispererRetry.MAX_ATTEMPTS,
                        e,
                        delay,
                    )
                    time.sleep(delay)
                else:
                    if isinstance(e, ConnectionError):
                        raise ExtractorError(
                            "Unable to connect to LLMWhisperer after %s attempts. "
                            "Ensure the adapter URL is reachable from this service and the API key is set."
                            % WhispererRetry.MAX_ATTEMPTS,
                            actual_err=e,
                            status_code=503,
                        ) from e
                    raise ExtractorError(
                        "LLMWhisperer request timed out after %s attempts. "
                        "Ensure the service is up and consider increasing wait_timeout."
                        % WhispererRetry.MAX_ATTEMPTS,
                        actual_err=e,
                        status_code=504,
                    ) from e
        if last_error is not None:
            raise last_error
        return None  # unreachable

    @staticmethod
    def make_highlight_data_request(
        config: dict[str, Any], whisper_hash: str, enable_highlight: bool
    ) -> dict[Any, Any]:
        """Makes a call to get highlight data from LLMWhisperer.

        Args:
            config (dict[str, Any]): LLMWhisperer config to use
            whisper_hash (str): Identifier of the extraction
            enable_highlight (bool): Whether to enable highlight

        Returns:
            dict[Any, Any]: Highlight data
        """
        logger.info(f"Extracting async for whisper hash: {whisper_hash}")

        headers: dict[str, Any] = LLMWhispererHelper.get_request_headers(config)
        params = {
            WhisperStatus.WHISPER_HASH: whisper_hash,
            WhispererConfig.EXTRACT_ALL_LINES: enable_highlight,
            WhispererConfig.LINES: "",
        }

        retrieve_response = LLMWhispererHelper.make_request(
            config=config,
            headers=headers,
            params=params,
            type="highlight",
        )
        return retrieve_response

    @staticmethod
    def extract_text_from_response(
        output_file_path: str | None,
        response: dict[str, Any],
        fs: FileStorage | None = None,
    ) -> str:
        if fs is None:
            fs = FileStorage(provider=FileStorageProvider.LOCAL)
        if not response:
            raise ExtractorError(
                "LLMWhisperer V2 returned an empty response. "
                "Ensure the service is up and returning the expected format.",
                status_code=500,
            )
        output_json = response
        if "result_text" not in output_json:
            logger.error(
                "LLMWhisperer V2 response missing 'result_text'. Keys: %s",
                list(output_json.keys()),
            )
            raise ExtractorError(
                "LLMWhisperer V2 did not return 'result_text'. "
                "Ensure the service is running and returning the expected response format so indexing can succeed.",
                status_code=502,
            )
        if output_file_path:
            LLMWhispererHelper.write_output_to_file(
                output_json=output_json,
                output_file_path=Path(output_file_path),
                fs=fs,
            )
        return output_json.get("result_text", "")

    @staticmethod
    def write_output_to_file(
        output_json: dict,
        output_file_path: Path,
        fs: FileStorage | None = None,
    ) -> None:
        """Write LLMW outputs to file.

        Writes the extracted text and metadata to the specified output file
        and metadata file.

        Args:
            output_json (dict): The dictionary containing the extracted data,
                with "text" as the key for the main content.
            output_file_path (Path): The file path where the extracted text
                should be written.
            fs (FileStorage): File storage instance to use for writing

        Raises:
            ExtractorError: If there is an error while writing the output file.
        """
        if fs is None:
            fs = FileStorage(provider=FileStorageProvider.LOCAL)
        try:
            text_output = output_json.get("result_text", "")
            logger.info(f"Writing output to {output_file_path}")
            fs.write(
                path=str(output_file_path),
                mode="w",
                data=text_output,
                encoding="utf-8",
            )
        except Exception as e:
            logger.error(f"Error while writing {output_file_path}: {e}")
            raise ExtractorError(str(e)) from e
        try:
            # Define the directory of the output file and metadata paths
            output_dir = output_file_path.parent
            metadata_dir = output_dir / "metadata"
            metadata_file_name = output_file_path.with_suffix(".json").name
            metadata_file_path = metadata_dir / metadata_file_name
            # Ensure the metadata directory exists
            fs.mkdir(create_parents=True, path=str(metadata_dir))
            # Remove the "result_text" key from the metadata
            metadata = {
                key: value for key, value in output_json.items() if key != "result_text"
            }
            metadata_json = json.dumps(metadata, ensure_ascii=False, indent=4)
            logger.info(f"Writing metadata to {metadata_file_path}")
            fs.write(
                path=str(metadata_file_path),
                mode="w",
                data=metadata_json,
                encoding="utf-8",
            )
        except Exception as e:
            logger.warn(f"Error while writing metadata to {metadata_file_path}: {e}")
