from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def create_profiles_for_existing_users(apps, schema_editor):
    """Create UserProfile for existing users."""
    User = apps.get_model('auth', 'User')
    UserProfile = apps.get_model('tracker', 'UserProfile')
    for user in User.objects.all():
        UserProfile.objects.get_or_create(user=user)


def reverse_func(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tracker', '0003_create_special_group'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('partner', models.ForeignKey(blank=True, help_text="Link to partner's account for couples mode", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='partner_of', to=settings.AUTH_USER_MODEL)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.RunPython(create_profiles_for_existing_users, reverse_func),
    ]
