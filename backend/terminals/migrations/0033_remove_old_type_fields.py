# Generated manually to remove old type fields

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('terminals', '0032_migrate_data_to_function'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='terminal',
            name='infrastructure_type',
        ),
        migrations.RemoveField(
            model_name='terminal',
            name='terminal_base_type',
        ),
        migrations.RemoveField(
            model_name='terminal',
            name='docking_station_type',
        ),
        migrations.DeleteModel(
            name='InfrastructureType',
        ),
        migrations.DeleteModel(
            name='TerminalBaseType',
        ),
        migrations.DeleteModel(
            name='DockingStationType',
        ),
    ] 