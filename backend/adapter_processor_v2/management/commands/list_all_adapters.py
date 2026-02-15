from django.core.management.base import BaseCommand
from adapter_processor_v2.models import AdapterInstance
from account_v2.models import Organization


class Command(BaseCommand):
    help = 'List all organizations and their adapters'

    def handle(self, *args, **options):
        orgs = Organization.objects.all()
        self.stdout.write(f'\n=== Organizations ===')
        for org in orgs:
            self.stdout.write(f'\nOrg: {org.name} (ID: {org.id}, Display: {org.display_name})')
            adapters = AdapterInstance.objects.filter(organization=org)
            self.stdout.write(f'  Adapters: {adapters.count()}')
            for adapter in adapters:
                self.stdout.write(f'    - {adapter.adapter_name} ({adapter.adapter_type})')
