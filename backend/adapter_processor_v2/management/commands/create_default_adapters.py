"""
Django management command to create default adapters
Usage: python manage.py create_default_adapters
"""
import os
import json
import sys
from django.core.management.base import BaseCommand
from django.conf import settings
from cryptography.fernet import Fernet
from adapter_processor_v2.models import AdapterInstance
from account_v2.models import Organization
from account_v2.models import User
from unstract.sdk1.constants import AdapterTypes


class Command(BaseCommand):
    help = 'Create default adapters for Parseris.ai'

    def handle(self, *args, **options):
        self.stdout.write('=== Creating Default Adapters ===\n')
        
        # Configuration - EDIT THESE VALUES
        ORG_SCHEMA = os.getenv("ORG_SCHEMA", "mock_org")
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
        PINECONE_ENV = os.getenv("PINECONE_ENV", "us-east-1")
        PINECONE_INDEX = os.getenv("PINECONE_INDEX", "grand-beech")
        LLMWHISPERER_KEY = os.getenv("LLMWHISPERER_KEY")
        LLMWHISPERER_URL = os.getenv(
            "LLMWHISPERER_URL",
            "http://localhost:8080",  # default; use hostname reachable from prompt-service
        )

        if not OPENAI_API_KEY:
            self.stderr.write(
                "Error: OPENAI_API_KEY not found in environment variables."
            )
            return
 
        try:
            # Get organization
            org = Organization.objects.get(name=ORG_SCHEMA)
            self.stdout.write(f'✓ Found organization: {org.display_name}')
        except Organization.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'✗ Organization "{ORG_SCHEMA}" not found'))
            return
        
        # Get user
        user = User.objects.first()
        if not user:
            self.stdout.write(self.style.ERROR('✗ No users found'))
            return
        self.stdout.write(f'✓ Using user: {user.email}')
        
        # Check for placeholder keys
        if "YOUR_" in OPENAI_API_KEY:
            self.stdout.write(self.style.WARNING('\n⚠ WARNING: API keys still contain placeholders!'))
            self.stdout.write('Please edit this file and add your real API keys:')
            self.stdout.write(f'  nano {__file__}\n')
            return
        
        # Encryption
        f = Fernet(settings.ENCRYPTION_KEY.encode('utf-8'))
        
        # Adapter configurations
        adapters_config = [
            {
                'name': 'OpenAI GPT-4o',
                'id': 'openai|openai',
                'type': AdapterTypes.LLM.value,
                'metadata': {
                    'adapter_name': 'OpenAI',
                    'model': 'gpt-4o',
                    'api_key': OPENAI_API_KEY,
                }
            },
            {
                'name': 'OpenAI Embeddings',
                'id': 'openai|openai_embedding',
                'type': AdapterTypes.EMBEDDING.value,
                'metadata': {
                    'adapter_name': 'OpenAI',
                    'model': 'text-embedding-3-small',
                    'api_key': OPENAI_API_KEY,
                }
            },
            {
                'name': 'Pinecone',
                'id': 'pinecone|pinecone',
                'type': AdapterTypes.VECTOR_DB.value,
                'metadata': {
                    'adapter_name': 'Pinecone',
                    'api_key': PINECONE_API_KEY,
                    'environment': PINECONE_ENV,
                    'index_name': PINECONE_INDEX,
                }
            },
        ]

        # Add LLMWhisperer V2 only when URL and key are set (so indexing can reach it)
        if LLMWHISPERER_URL and LLMWHISPERER_KEY:
            adapters_config.append({
                'name': 'LLMWhisperer V2',
                'id': 'llmwhisperer|llmwhisperer_v2',
                'type': AdapterTypes.X2TEXT.value,
                'metadata': {
                    'adapter_name': 'LLMWhisperer',
                    'url': LLMWHISPERER_URL.rstrip('/'),
                    'unstract_key': LLMWHISPERER_KEY,
                }
            })
        else:
            self.stdout.write(
                self.style.WARNING(
                    '  ⚠ Skipping LLMWhisperer V2: set LLMWHISPERER_URL and '
                    'LLMWHISPERER_KEY for indexing with LLMWhisperer.'
                )
            )
        
        self.stdout.write('\nCreating adapters...')
        created_count = 0
        
        for config in adapters_config:
            # Check if adapter already exists
            existing = AdapterInstance.objects.filter(
                organization=org,
                adapter_name=config['name'],
                adapter_type=config['type']
            ).first()
            
            if existing:
                self.stdout.write(self.style.WARNING(f'  ⚠ {config["name"]} already exists'))
                continue
            
            try:
                # Encrypt metadata
                encrypted = f.encrypt(json.dumps(config['metadata']).encode('utf-8'))
                
                # Create adapter
                adapter = AdapterInstance(
                    adapter_name=config['name'],
                    adapter_id=config['id'],
                    adapter_type=config['type'],
                    adapter_metadata=config['metadata'],
                    adapter_metadata_b=encrypted,
                    organization=org,
                    created_by=user,
                    modified_by=user,
                    is_active=True,
                    shared_to_org=True,
                )
                adapter.save()
                
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created: {config["name"]}'))
                created_count += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Failed to create {config["name"]}: {e}'))
        
        self.stdout.write(self.style.SUCCESS(f'\n✓ Created {created_count} adapters successfully!'))
