# Generated manually for terminal_type to terminal_types migration
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('terminals', '0028_migrate_terminal_type_data'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='terminal',
            name='terminal_type',
        ),
        migrations.RemoveField(
            model_name='terminal',
            name='parent_terminal',
        ),
    ] 