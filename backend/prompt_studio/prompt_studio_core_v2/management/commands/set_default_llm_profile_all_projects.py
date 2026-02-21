"""
Management command to ensure every Prompt Studio project has a default LLM profile.

For each organization, finds CustomTools that have no ProfileManager with is_default=True,
then creates a default profile (using frictionless adapters when available) for each.
"""

import logging

from django.db.models import Exists, OuterRef
from django.core.management.base import BaseCommand

from account_v2.models import Organization
from prompt_studio.prompt_profile_manager_v2.models import ProfileManager
from prompt_studio.prompt_studio_core_v2.models import CustomTool
from prompt_studio.prompt_studio_core_v2.prompt_studio_helper import PromptStudioHelper
from tenant_account_v2.models import OrganizationMember
from utils.user_context import UserContext

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Set default LLM profile for all Prompt Studio projects that don't have one. "
        "Uses frictionless adapters per organization when available."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--org",
            type=str,
            default=None,
            help="Organization ID (or name) to process. If omitted, all organizations are processed.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only list tools that would get a default profile, do not create.",
        )

    def handle(self, *args, **options):
        org_id = options["org"]
        dry_run = options["dry_run"]

        if org_id:
            try:
                orgs = [Organization.objects.get(organization_id=org_id)]
            except Organization.DoesNotExist:
                try:
                    orgs = [Organization.objects.get(name=org_id)]
                except Organization.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f'Organization "{org_id}" not found.')
                    )
                    return
        else:
            orgs = list(Organization.objects.all())

        if not orgs:
            self.stdout.write("No organizations found.")
            return

        total_created = 0
        total_skipped = 0
        total_no_adapters = 0

        for org in orgs:
            UserContext.set_organization_identifier(org.organization_id)
            # Tools in this org that have no default profile
            has_default = ProfileManager.objects.filter(
                prompt_studio_tool=OuterRef("pk"), is_default=True
            )
            tools_without_default = CustomTool.objects.filter(~Exists(has_default))
            count = tools_without_default.count()
            if count == 0:
                continue

            # Resolve a user for this org (for create_default_profile_manager)
            first_member = (
                OrganizationMember.objects.select_related("user").first()
            )
            org_user = first_member.user if first_member else None
            if not org_user:
                self.stdout.write(
                    self.style.WARNING(
                        f"Org {org.organization_id}: no members, skipping {count} tool(s)."
                    )
                )
                total_skipped += count
                continue

            self.stdout.write(
                f"Org {org.organization_id}: {count} project(s) without default profile."
            )

            if dry_run:
                for tool in tools_without_default[:10]:
                    self.stdout.write(f"  Would add default profile: {tool.tool_name} ({tool.tool_id})")
                if count > 10:
                    self.stdout.write(f"  ... and {count - 10} more.")
                total_created += count
                continue

            for tool in tools_without_default:
                user = tool.created_by or org_user
                try:
                    PromptStudioHelper.create_default_profile_manager(
                        user, tool.tool_id
                    )
                    # Helper may skip creation when no frictionless adapters exist
                    has_default_now = ProfileManager.objects.filter(
                        prompt_studio_tool=tool, is_default=True
                    ).exists()
                    if has_default_now:
                        total_created += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  Default profile set: {tool.tool_name} ({tool.tool_id})"
                            )
                        )
                    else:
                        total_no_adapters += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"  No frictionless adapters for org; skipped: {tool.tool_name} ({tool.tool_id})"
                            )
                        )
                except Exception as e:
                    logger.warning(
                        "Failed to create default profile for tool %s: %s",
                        tool.tool_id,
                        e,
                        exc_info=True,
                    )
                    total_no_adapters += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"  Skipped {tool.tool_name} ({tool.tool_id}): {e}"
                        )
                    )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created: {total_created}, skipped (no user): {total_skipped}, "
                f"skipped (no adapters/error): {total_no_adapters}"
            )
        )
