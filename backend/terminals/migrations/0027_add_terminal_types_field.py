# Generated manually for terminal_type to terminal_types migration
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('terminals', '0026_alter_terminal_options_terminal_parent_terminal'),
    ]

    operations = [
        # First rename the old field's related_name to avoid conflicts
        migrations.AlterField(
            model_name='terminal',
            name='terminal_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.CASCADE, related_name='terminals_old', to='terminals.terminaltype'),
        ),
        # Then add the new many-to-many field
        migrations.AddField(
            model_name='terminal',
            name='terminal_types',
            field=models.ManyToManyField(blank=True, related_name='terminals', to='terminals.terminaltype'),
        ),
    ] 