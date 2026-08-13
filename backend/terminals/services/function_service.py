from django.db import transaction
from django.core.exceptions import ValidationError
from terminals.models import Function
from common.constant import MESSAGE_ENUM


class FunctionService:
    def get_functions(self):
        """
        Get all functions
        """
        return Function.objects.all().order_by('name')

    def get_function(self, function_id):
        """
        Get single function by ID
        """
        try:
            return Function.objects.get(id=function_id)
        except Function.DoesNotExist:
            return None

    def get_functions_by_type(self, function_type):
        """
        Get functions by type
        """
        return Function.objects.filter(function_type__in=function_type).order_by('name')

    @transaction.atomic
    def create_function(self, data):
        """
        Create a new function
        
        Args:
            data: FunctionInSchema data
            
        Returns:
            tuple: (success, result)
        """
        try:
            # Validate required fields
            if not data.get('name'):
                return False, "Name is required"
            
            function = Function.objects.create(**data.dict())
            return True, function
        except ValidationError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)

    @transaction.atomic
    def update_function(self, function_id, data):
        """
        Update an existing function
        
        Args:
            function_id: Function ID
            data: FunctionInSchema data
            
        Returns:
            tuple: (success, result)
        """
        try:
            function = Function.objects.get(id=function_id)
            
            # Update fields
            for key, value in data.dict(exclude_unset=True).items():
                if hasattr(function, key):
                    setattr(function, key, value)
            
            function.save()
            return True, function
        except Function.DoesNotExist:
            return False, "Function not found"
        except ValidationError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)

    @transaction.atomic
    def delete_function(self, function_id):
        """
        Delete a function
        
        Args:
            function_id: Function ID
            
        Returns:
            tuple: (success, result)
        """
        try:
            function = Function.objects.get(id=function_id)
            
            # Check if function is being used by any terminals
            if function.terminals.exists():
                return False, f"Cannot delete function '{function.name}' because it is being used by {function.terminals.count()} terminals"
            
            function.delete()
            return True, None
        except Function.DoesNotExist:
            return False, "Function not found"
        except Exception as e:
            return False, str(e) 