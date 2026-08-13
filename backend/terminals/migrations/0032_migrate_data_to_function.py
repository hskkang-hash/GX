# Generated manually for data migration to Function model

from django.db import migrations


def migrate_types_to_functions(apps, schema_editor):
    """
    Migrate data from InfrastructureType, TerminalBaseType, DockingStationType to Function
    """
    # Get models
    Function = apps.get_model('terminals', 'Function')
    InfrastructureType = apps.get_model('terminals', 'InfrastructureType')
    TerminalBaseType = apps.get_model('terminals', 'TerminalBaseType')
    DockingStationType = apps.get_model('terminals', 'DockingStationType')
    Terminal = apps.get_model('terminals', 'Terminal')
    
    # Dictionary to track created functions for later use
    function_mapping = {}
    
    # Migrate InfrastructureType data
    for infrastructure_type in InfrastructureType.objects.all():
        function = Function.objects.create(
            name=infrastructure_type.name,
            code=infrastructure_type.code,
            description=infrastructure_type.description,
            function_type='infrastructure',
            group=infrastructure_type.group,
            created_on=infrastructure_type.created_on,
            updated_on=infrastructure_type.modified_on,
        )
        function_mapping[f'infrastructure_{infrastructure_type.id}'] = function
        print(f"Migrated InfrastructureType '{infrastructure_type.name}' to Function ID {function.id}")
    
    # Migrate TerminalBaseType data
    for terminal_base_type in TerminalBaseType.objects.all():
        function = Function.objects.create(
            name=terminal_base_type.name,
            code=terminal_base_type.code,
            description=terminal_base_type.description,
            function_type='delivery_hub',
            group=terminal_base_type.group,
            created_on=terminal_base_type.created_on,
            updated_on=terminal_base_type.modified_on,
        )
        function_mapping[f'delivery_hub_{terminal_base_type.id}'] = function
        print(f"Migrated TerminalBaseType '{terminal_base_type.name}' to Function ID {function.id}")
    
    # Migrate DockingStationType data
    for docking_station_type in DockingStationType.objects.all():
        function = Function.objects.create(
            name=docking_station_type.name,
            code=docking_station_type.code,
            description=docking_station_type.description,
            function_type='docking_station',
            group=docking_station_type.group,
            created_on=docking_station_type.created_on,
            updated_on=docking_station_type.modified_on,
        )
        function_mapping[f'docking_station_{docking_station_type.id}'] = function
        print(f"Migrated DockingStationType '{docking_station_type.name}' to Function ID {function.id}")
    
    # Now establish ManyToMany relationships for terminals
    terminals_updated = 0
    for terminal in Terminal.objects.all():
        functions_to_add = []
        
        # Check infrastructure_type
        if terminal.infrastructure_type_id:
            function_key = f'infrastructure_{terminal.infrastructure_type_id}'
            if function_key in function_mapping:
                functions_to_add.append(function_mapping[function_key])
        
        # Check terminal_base_type
        if terminal.terminal_base_type_id:
            function_key = f'delivery_hub_{terminal.terminal_base_type_id}'
            if function_key in function_mapping:
                functions_to_add.append(function_mapping[function_key])
        
        # Check docking_station_type
        if terminal.docking_station_type_id:
            function_key = f'docking_station_{terminal.docking_station_type_id}'
            if function_key in function_mapping:
                functions_to_add.append(function_mapping[function_key])
        
        # Add functions to terminal
        if functions_to_add:
            terminal.functions.set(functions_to_add)
            terminals_updated += 1
            function_names = [f.name for f in functions_to_add]
            print(f"Terminal '{terminal.name}' linked to functions: {', '.join(function_names)}")
    
    print(f"Data migration completed: {terminals_updated} terminals updated with new function relationships")


def reverse_migrate_functions_to_types(apps, schema_editor):
    """
    Reverse migration - not implemented as we want to keep the data
    """
    print("Reverse migration not implemented - keeping Function data intact")


class Migration(migrations.Migration):

    dependencies = [
        ('terminals', '0031_add_function_model'),
    ]

    operations = [
        migrations.RunPython(
            migrate_types_to_functions,
            reverse_migrate_functions_to_types,
        ),
    ] 