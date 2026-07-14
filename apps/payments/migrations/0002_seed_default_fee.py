from django.db import migrations


def seed_fee(apps, schema_editor):
    PlatformFeeSetting = apps.get_model('payments', 'PlatformFeeSetting')
    if not PlatformFeeSetting.objects.exists():
        PlatformFeeSetting.objects.create(percentage=10)


def unseed_fee(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_fee, unseed_fee),
    ]
