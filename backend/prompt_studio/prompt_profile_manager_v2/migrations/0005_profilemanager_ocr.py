import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("adapter_processor_v2", "0001_initial"),
        ("prompt_profile_manager_v2", "0004_merge_20250805_1025"),
    ]

    operations = [
        migrations.AddField(
            model_name="profilemanager",
            name="ocr",
            field=models.ForeignKey(
                blank=True,
                db_comment="Optional OCR adapter used as fallback when x2text returns empty text (scanned PDFs)",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="profiles_ocr",
                to="adapter_processor_v2.adapterinstance",
            ),
        ),
    ]
