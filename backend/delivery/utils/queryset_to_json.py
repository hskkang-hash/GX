from django.db.models import QuerySet
from django.forms.models import model_to_dict
from django.core.serializers import serialize
import json

def queryset_to_json(queryset):
    """
    Convert Django QuerySet to a list that can be serialized to JSON
    
    Args:
        queryset: Django QuerySet object
        
    Returns:
        List of dictionaries with model data
    """
    # If it's already a list or other non-QuerySet object, return it as is
    if not isinstance(queryset, QuerySet):
        return queryset
    
    # If QuerySet is empty, return empty list
    if not queryset.exists():
        return []
    
    # Using Django serializer
    # This creates a list of dictionaries with model fields
    serialized_data = serialize('python', queryset)
    result = [item['fields'] for item in serialized_data]
    
    # Add primary key/id to each object
    for i, item in enumerate(serialized_data):
        result[i]['id'] = item['pk']
    
    return result
    
    # Option 2: Using model_to_dict (alternative approach)
    # return [model_to_dict(obj) for obj in queryset]

def serialize_object(obj) -> dict:
    """
    Convert a single model instance to JSON.
    
    Args:
        obj: The model instance to convert.
        
    Returns:
        dict: The serialized object as a dictionary.
    """
    if obj is None:
        return None
        
    # Serialize the object
    obj_json = json.loads(serialize('json', [obj]))[0]
    
    # Build the result dictionary
    result = obj_json['fields']
    result['id'] = obj_json['pk']
    
    return result

def serialize_related(obj, related_fields: list = None) -> dict:
    """
    Convert a single model instance to JSON and include specified related fields.
    
    Args:
        obj: The model instance to convert.
        related_fields: A list of related field names to include in the output.
        
    Returns:
        dict: The serialized object as a dictionary with related fields included.
    """
    if obj is None:
        return None
        
    # Serialize the base object
    result = serialize_object(obj)
    
    # Handle specified related fields
    if related_fields:
        for field in related_fields:
            related_obj = getattr(obj, field, None)
            if related_obj:
                # Handle many-to-many relationships
                if hasattr(related_obj, 'all'):
                    result[field] = queryset_to_json(related_obj.all())
                # Handle one-to-one or many-to-one relationships
                else:
                    result[field] = serialize_object(related_obj)
    
    return result
