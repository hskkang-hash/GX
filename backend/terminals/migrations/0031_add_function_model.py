# Generated manually for Function model migration

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('terminals', '0030_alter_routeterminal_options'),
        ('user', '0020_alter_timezone_code'),
    ]

    operations = [
        migrations.CreateModel(
            name='Function',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255)),
                ('code', models.CharField(blank=True, max_length=100, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('function_type', models.CharField(
                    blank=True, 
                    choices=[
                        ('infrastructure', 'Infrastructure'), 
                        ('terminal_base', 'Terminal Base'), 
                        ('docking_station', 'Docking Station')
                    ], 
                    help_text='Type of function for data migration purposes', 
                    max_length=50, 
                    null=True
                )),
                ('group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='user.usergroup')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='terminal',
            name='functions',
            field=models.ManyToManyField(
                blank=True, 
                help_text='Unified functions replacing infrastructure_type, terminal_base_type, and docking_station_type', 
                related_name='terminals', 
                to='terminals.function'
            ),
        ),
    ] 