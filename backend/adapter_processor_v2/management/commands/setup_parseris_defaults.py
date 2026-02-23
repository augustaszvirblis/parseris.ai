from django.core.management.base import BaseCommand
from django.db import connection
from django.apps import apps
from account_v2.models import Organization, User

class Command(BaseCommand):
    help = 'Raw SQL Linker for Adapters'

    def handle(self, *args, **options):
        self.stdout.write("=== Raw SQL Diagnostic & Link ===")
        
        user = User.objects.first()
        org_id = 1

        # 1. Get IDs using Raw SQL because the ORM is looking at the wrong schema/table
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, adapter_name FROM unstract.adapter_instance WHERE organization_id = %s", [org_id])
            rows = cursor.fetchall()

        if not rows:
            self.stdout.write(self.style.ERROR("✗ Even Raw SQL found 0 adapters. Check schema name!"))
            return

        found_map = {}
        for row in rows:
            aid, name = row[0], row[1]
            self.stdout.write(f"Found via SQL: {name} ({aid})")
            if "GPT-4o" in name: found_map['llm_id'] = aid
            if "Embeddings" in name: found_map['emb_id'] = aid
            if "Pinecone" in name: found_map['vec_id'] = aid
            if "Native PDF" in name:
                found_map['txt_id'] = aid
            elif "Whisperer" in name and 'txt_id' not in found_map:
                found_map['txt_id'] = aid

        if len(found_map) < 4:
            self.stdout.write(self.style.ERROR(f"✗ Only found {len(found_map)}/4 adapters."))
            return

        # 2. Get Models
        try:
            ProfileManager = apps.get_model('prompt_profile_manager_v2', 'ProfileManager')
            CustomTool = apps.get_model('prompt_studio_core_v2', 'CustomTool')
            AdapterInstance = apps.get_model('adapter_processor_v2', 'AdapterInstance')
        except LookupError:
            ProfileManager = apps.get_model('prompt_profile_manager', 'ProfileManager')
            CustomTool = apps.get_model('prompt_studio_core', 'CustomTool')
            AdapterInstance = apps.get_model('adapter_processor_v2', 'AdapterInstance')

        # 3. Get or create project (vision table extraction = LLM-based PDF extraction)
        tool = CustomTool.objects.filter(organization_id=org_id).first()
        if not tool:
            self.stdout.write("Creating Tool...")
            tool, _ = CustomTool.objects.get_or_create(
                tool_name="Parseris",
                organization_id=org_id,
                defaults={
                    "created_by": user,
                    "modified_by": user,
                    "use_vision_table_extraction": True,
                },
            )
        if not getattr(tool, "use_vision_table_extraction", False):
            tool.use_vision_table_extraction = True
            tool.save(update_fields=["use_vision_table_extraction"])
            self.stdout.write("Enabled use_vision_table_extraction on Parseris tool.")

        # Ensure default prompt uses table type so vision extraction path is used
        ToolStudioPrompt = apps.get_model("prompt_studio_v2", "ToolStudioPrompt")
        first_prompt = (
            ToolStudioPrompt.objects.filter(tool_id=tool, prompt_type="PROMPT", active=True)
            .order_by("sequence_number")
            .first()
        )
        if first_prompt and first_prompt.enforce_type != "table":
            first_prompt.enforce_type = "table"
            first_prompt.save(update_fields=["enforce_type"])
            self.stdout.write("Set default prompt enforce_type to 'table' for vision extraction.")

        ProfileManager.objects.filter(prompt_studio_tool=tool).delete()
        ProfileManager.objects.create(
            profile_name='Default Profile',
            prompt_studio_tool=tool,
            llm_id=found_map['llm_id'],
            embedding_model_id=found_map['emb_id'],
            vector_store_id=found_map['vec_id'],
            x2text_id=found_map['txt_id'],
            is_default=True,
            chunk_size=1024,
            chunk_overlap=200,
            retrieval_strategy='similarity',
            similarity_top_k=5,
            created_by=user,
            modified_by=user
        )
        self.stdout.write(self.style.SUCCESS("✓ SUCCESS: Profile linked using Raw SQL IDs!"))

