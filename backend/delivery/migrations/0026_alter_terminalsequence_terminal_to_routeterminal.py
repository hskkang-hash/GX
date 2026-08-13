# Generated manually to fix TerminalSequence field reference

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delivery', '0025_terminalsequence'),
        ('terminals', '0047_remove_routeterminal_takeoff_support'),
    ]

    operations = [
        # Remove the old index that references 'terminal'
        migrations.RemoveIndex(
            model_name='terminalsequence',
            name='delivery_te_termina_769716_idx',
        ),
        # Remove the old unique constraint that references 'terminal'
        migrations.AlterUniqueTogether(
            name='terminalsequence',
            unique_together={('delivery_operation', 'sequence_order')},
        ),
        # Add the new routeterminal field
        migrations.AddField(
            model_name='terminalsequence',
            name='routeterminal',
            field=models.ForeignKey(
                blank=True,
                help_text='The route terminal in the sequence',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to='terminals.routeterminal'
            ),
        ),
        # Add new index for routeterminal
        migrations.AddIndex(
            model_name='terminalsequence',
            index=models.Index(
                fields=['routeterminal', 'is_visited'],
                name='delivery_te_routete_81b1b7_idx'
            ),
        ),
        # Remove the old terminal field
        migrations.RemoveField(
            model_name='terminalsequence',
            name='terminal',
        ),
        # Add new unique constraint with routeterminal
        migrations.AlterUniqueTogether(
            name='terminalsequence',
            unique_together={
                ('delivery_operation', 'sequence_order'),
                ('delivery_operation', 'routeterminal')
            },
        ),
    ]
