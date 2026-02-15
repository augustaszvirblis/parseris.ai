from django.core.management.base import BaseCommand
from adapter_processor_v2.models import AdapterInstance
from account_v2.models import Organization


class Command(BaseCommand):
    help = 'Delete all adapters for mock_org'

    def handle(self, *args, **options):
        try:
            org = Organization.objects.get(name='mock_org')
            count = AdapterInstance.objects.filter(organization=org).count()
            self.stdout.write(f'Found {count} adapters')
            
            AdapterInstance.objects.filter(organization=org).delete()
            self.stdout.write(self.style.SUCCESS(f'✓ Deleted {count} adapters'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
