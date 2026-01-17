from django.db import migrations


def create_special_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.get_or_create(name='special')


def remove_special_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name='special').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0002_dietaryentry_item_dietaryentry_remarks_and_more'),
    ]

    operations = [
        migrations.RunPython(create_special_group, remove_special_group),
    ]
