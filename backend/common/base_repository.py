"""
Base repository class for common functionality across repositories.
"""

from typing import TypeVar, Generic, List, Type, Optional, Dict, Any
from django.db.models import Model, QuerySet

# Type variable for model classes
T = TypeVar('T', bound=Model)


class BaseRepository(Generic[T]):
    """
    Base repository class with common methods for accessing models.
    
    This class provides a standard set of methods for working with
    Django models, following the repository pattern.
    
    Type Parameters:
        T: A Django model class
    """
    model_class: Type[T] = None
    
    @classmethod
    def get_all(cls) -> QuerySet:
        """
        Get all instances of the model.
        
        Returns:
            QuerySet: All model instances
        """
        return cls.model_class.objects.all()
    
    @classmethod
    def get_by_id(cls, id: int) -> T:
        """
        Get a model instance by its ID.
        
        Args:
            id: The ID of the model instance
            
        Returns:
            T: The model instance with the given ID
            
        Raises:
            model_class.DoesNotExist: If no instance with the given ID exists
        """
        return cls.model_class.objects.get(id=id)
    
    @classmethod
    def create(cls, **kwargs) -> T:
        """
        Create a new model instance.
        
        Args:
            **kwargs: Attributes for the new model instance
            
        Returns:
            T: The created model instance
        """
        instance = cls.model_class(**kwargs)
        instance.save()
        return instance
    
    @classmethod
    def update(cls, instance: T, **kwargs) -> T:
        """
        Update an existing model instance.
        
        Args:
            instance: The model instance to update
            **kwargs: New attribute values
            
        Returns:
            T: The updated model instance
        """
        for key, value in kwargs.items():
            if hasattr(instance, key) and value is not None:
                setattr(instance, key, value)
        
        instance.save()
        return instance
    
    @classmethod
    def delete(cls, instance: T) -> None:
        """
        Delete a model instance.
        
        Args:
            instance: The model instance to delete
        """
        instance.delete()
    
    @classmethod
    def get_or_create(cls, defaults: Optional[Dict[str, Any]] = None, **kwargs) -> tuple[T, bool]:
        """
        Get an existing instance or create a new one.
        
        Args:
            defaults: Values to use for creating the model if it doesn't exist
            **kwargs: Lookup parameters
            
        Returns:
            tuple: (instance, created) where created is a boolean specifying
                   whether a new instance was created
        """
        return cls.model_class.objects.get_or_create(defaults=defaults or {}, **kwargs)
    
    @classmethod
    def filter(cls, **kwargs) -> QuerySet:
        """
        Filter model instances by the given parameters.
        
        Args:
            **kwargs: Filter parameters
            
        Returns:
            QuerySet: Filtered model instances
        """
        return cls.model_class.objects.filter(**kwargs) 