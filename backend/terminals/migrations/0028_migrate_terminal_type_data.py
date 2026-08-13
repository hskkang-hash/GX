# Generated manually for terminal_type to terminal_types migration
from django.db import migrations


def migrate_terminal_type_data(apps, schema_editor):
    """
    Migrate data from terminal_type (ForeignKey) to terminal_types (ManyToMany)
    """
    Terminal = apps.get_model('terminals', 'Terminal')
    
    # Get all terminals that have a terminal_type
    terminals_with_type = Terminal.objects.filter(terminal_type__isnull=False)
    
    print(f"Migrating {terminals_with_type.count()} terminals...")
    
    for terminal in terminals_with_type:
        # Add the old terminal_type to the new terminal_types many-to-many field
        terminal.terminal_types.add(terminal.terminal_type)
        
    print("Migration completed successfully!")


def reverse_migrate_terminal_type_data(apps, schema_editor):
    """
    Reverse migration: copy the first terminal_type from terminal_types back to terminal_type
    """
    Terminal = apps.get_model('terminals', 'Terminal')
    
    # Get all terminals that have terminal_types
    terminals_with_types = Terminal.objects.filter(terminal_types__isnull=False)
    
    print(f"Reverse migrating {terminals_with_types.count()} terminals...")
    
    for terminal in terminals_with_types:
        # Get the first terminal type from the many-to-many field
        first_type = terminal.terminal_types.first()
        if first_type:
            terminal.terminal_type = first_type
            terminal.save()
            
    print("Reverse migration completed!")


class Migration(migrations.Migration):

    dependencies = [
        ('terminals', '0027_add_terminal_types_field'),
    ]

    operations = [
        migrations.RunPython(
            migrate_terminal_type_data,
            reverse_migrate_terminal_type_data,
        ),
    ] 