from django.core.management.base import BaseCommand
from adapter_processor_v2.models import AdapterInstance


class Command(BaseCommand):
    help = 'Purge ALL adapters from database'

    def handle(self, *args, **options):
        count = AdapterInstance.objects.all().count()
        self.stdout.write(f'Found {count} total adapters in database')
        
        AdapterInstance.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'✓ Purged all {count} adapters'))
        
        remaining = AdapterInstance.objects.all().count()
        self.stdout.write(f'Remaining: {remaining}')
