import logging
import uuid
from functools import wraps

from django.db import IntegrityError
from django.http import HttpRequest
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from account_v2.models import Organization, User
from prompt_studio.prompt_profile_manager_v2.models import ProfileManager
from prompt_studio.prompt_studio_core_v2.models import CustomTool
from prompt_studio.prompt_studio_core_v2.prompt_studio_helper import (
    PromptStudioHelper,
)
from prompt_studio.prompt_studio_document_manager_v2.models import DocumentManager
from prompt_studio.prompt_studio_document_manager_v2.prompt_studio_document_helper import (
    PromptStudioDocumentHelper,
)
from prompt_studio.prompt_studio_output_manager_v2.output_manager_helper import (
    OutputManagerHelper,
)
from prompt_studio.prompt_studio_v2.models import ToolStudioPrompt
from utils.file_storage.helpers.prompt_studio_file_helper import (
    PromptStudioFileHelper,
)
from utils.user_context import UserContext

logger = logging.getLogger(__name__)

DEFAULT_EXTRACTION_PROMPT = (
    "Extract ALL data from this document into a structured JSON object. "
    "Include every field, label, value, table, and piece of information you "
    "can find. Return the result as a flat JSON object with descriptive keys. "
    "For tables, return them as arrays of objects."
)


def _get_defaults():
    """Return the first organization and user, and set the UserContext so
    that Django managers filtered by organization work correctly."""
    org = Organization.objects.first()
    if not org:
        return None, None
    user = User.objects.first()
    if not user:
        return org, None
    UserContext.set_organization_identifier(org.organization_id)
    return org, user


def _normalize_tool_for_vision(tool):
    """Ensure the tool is configured for LLM vision extraction (no x2text).
    Idempotent: safe to call on every request so the user never has to manage projects.
    """
    update_fields = []
    if getattr(tool, "tool_name", None) != "Parseris":
        tool.tool_name = "Parseris"
        update_fields.append("tool_name")
    if not getattr(tool, "use_vision_table_extraction", False):
        tool.use_vision_table_extraction = True
        update_fields.append("use_vision_table_extraction")
    if update_fields:
        tool.save(update_fields=update_fields)


def _get_or_create_project(user, org):
    """Return the single internal project (create if none). Always vision-ready.
    User never sees or chooses a project; they just upload and download.
    """
    existing = CustomTool.objects.order_by("created_at").first()
    if existing:
        _normalize_tool_for_vision(existing)
        _ensure_profile(existing, user)
        return existing

    tool = CustomTool.objects.create(
        tool_name="Parseris",
        description="Default Prompt Studio project",
        author=user.email or user.username or "User",
        organization=org,
        created_by=user,
        modified_by=user,
        use_vision_table_extraction=True,
    )
    _ensure_profile(tool, user)
    return tool


def _ensure_profile(tool, user):
    """Make sure the tool has a default LLM profile (vision-capable when possible)."""
    try:
        ProfileManager.get_default_llm_profile(tool)
    except Exception:
        try:
            PromptStudioHelper.create_default_profile_manager(
                user, tool.tool_id, prefer_vision_capable=True
            )
        except Exception as e:
            logger.warning(
                "Default profile creation failed for %s: %s", tool.tool_id, e
            )


def _ensure_default_prompt(tool, user):
    """Return the extraction prompt for the tool, creating one if needed.
    Ensures existing prompts use enforce_type=table and prompt_key=extracted_data
    so the vision path is always used (user never manages project settings).
    """
    existing = ToolStudioPrompt.objects.filter(
        tool_id=tool, prompt_type="PROMPT", active=True
    ).first()
    if existing:
        update_fields = []
        if getattr(existing, "enforce_type", None) not in ("table", "record"):
            existing.enforce_type = "table"
            update_fields.append("enforce_type")
        if getattr(existing, "prompt_key", None) != "extracted_data":
            existing.prompt_key = "extracted_data"
            update_fields.append("prompt_key")
        if update_fields:
            existing.save(update_fields=update_fields)
        return existing

    profile = None
    try:
        profile = ProfileManager.get_default_llm_profile(tool)
    except Exception:
        pass

    prompt = ToolStudioPrompt.objects.create(
        tool_id=tool,
        prompt_key="extracted_data",
        prompt=DEFAULT_EXTRACTION_PROMPT,
        enforce_type="table",  # Use vision table extraction (LLM-based PDF → table)
        prompt_type="PROMPT",
        sequence_number=1,
        active=True,
        profile_manager=profile,
        created_by=user,
        modified_by=user,
    )
    return prompt


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def sps_upload(request: HttpRequest) -> Response:
    """Upload a PDF, auto-create project, index the document."""
    org, user = _get_defaults()
    if not org or not user:
        return Response(
            {"error": "System not initialised – run the setup first."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    uploaded_file = request.FILES.get("file")
    if not uploaded_file:
        return Response(
            {"error": "No file provided. Send a PDF as the 'file' field."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    tool = _get_or_create_project(user, org)
    tool_id = str(tool.tool_id)
    org_id = org.organization_id
    user_id = user.user_id
    file_name = uploaded_file.name

    PromptStudioFileHelper.upload_for_ide(
        org_id=org_id,
        user_id=user_id,
        tool_id=tool_id,
        file_name=file_name,
        file_data=uploaded_file,
    )

    try:
        document = PromptStudioDocumentHelper.create(
            tool_id=tool_id, document_name=file_name
        )
    except IntegrityError:
        document = DocumentManager.objects.get(tool=tool, document_name=file_name)

    _ensure_default_prompt(tool, user)

    result = {
        "tool_id": tool_id,
        "document_id": str(document.document_id),
        "document_name": document.document_name,
    }

    run_id = str(uuid.uuid4())
    try:
        unique_id = PromptStudioHelper.index_document(
            tool_id=tool_id,
            file_name=file_name,
            org_id=org_id,
            user_id=user_id,
            document_id=document.document_id,
            run_id=run_id,
        )
        result["indexed"] = bool(unique_id)
        if not unique_id:
            result["indexing_error"] = "Indexing did not return an index id."
    except Exception as e:
        result["indexed"] = False
        result["indexing_error"] = str(e)
        logger.exception("SPS indexing failed for %s: %s", file_name, e)

    return Response(result)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def sps_extract(request: HttpRequest) -> Response:
    """Run the extraction prompt and return JSON results.
    document_id is required (from upload response). tool_id is optional;
    if omitted, the tool is resolved from the document so the user never deals with projects.
    """
    tool_id = request.data.get("tool_id")
    document_id = request.data.get("document_id")

    if not document_id:
        return Response(
            {"error": "document_id is required (returned from upload)."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    org, user = _get_defaults()
    if not org or not user:
        return Response(
            {"error": "System not initialised – run the setup first."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    org_id = org.organization_id
    user_id = user.user_id

    if tool_id:
        try:
            tool = CustomTool.objects.get(pk=tool_id)
        except CustomTool.DoesNotExist:
            return Response(
                {"error": "Project not found."}, status=status.HTTP_404_NOT_FOUND
            )
    else:
        try:
            document = DocumentManager.objects.get(document_id=document_id)
            tool = document.tool
            tool_id = str(tool.tool_id)
        except DocumentManager.DoesNotExist:
            return Response(
                {"error": "Document not found."}, status=status.HTTP_404_NOT_FOUND
            )

    # Ensure this tool and its prompt use vision extraction (no project setup for user)
    _normalize_tool_for_vision(tool)
    prompt = _ensure_default_prompt(tool, user)
    run_id = str(uuid.uuid4())

    try:
        response = PromptStudioHelper.prompt_responder(
            id=str(prompt.prompt_id),
            tool_id=tool_id,
            org_id=org_id,
            user_id=user_id,
            document_id=document_id,
            run_id=run_id,
        )
        return Response({"status": "ok", "data": response})
    except Exception as e:
        logger.exception("SPS extraction failed: %s", e)
        return Response(
            {"error": f"Extraction failed: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def sps_status(request: HttpRequest) -> Response:
    """Health-check that also returns the default project info if it exists."""
    org, user = _get_defaults()
    if not org or not user:
        return Response({"ready": False, "error": "System not initialised."})

    tool = _get_or_create_project(user, org)
    has_profile = False
    if tool:
        try:
            ProfileManager.get_default_llm_profile(tool)
            has_profile = True
        except Exception:
            pass

    return Response(
        {
            "ready": True,
            "has_project": tool is not None,
            "tool_id": str(tool.tool_id) if tool else None,
            "has_profile": has_profile,
        }
    )
