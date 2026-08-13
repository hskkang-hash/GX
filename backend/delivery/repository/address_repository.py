from common.base_repository import BaseRepository
from delivery.models import Address
from typing import List, Dict, Any, Optional, Tuple
from django.db.models import QuerySet


class AddressRepository(BaseRepository[Address]):
    """
    Repository for the Address model.
    Implements specific queries and operations related to addresses.
    """
    model_class = Address
    
    @classmethod
    def get_by_coordinates(cls, lat: float, lng: float, distance: float = 0.01) -> QuerySet:
        """
        Find addresses within a certain distance of given coordinates.
        
        Args:
            lat: Latitude
            lng: Longitude
            distance: Distance in decimal degrees (approximate)
            
        Returns:
            QuerySet of Address objects
        """
        return cls.model_class.objects.filter(
            lat__gte=lat-distance, 
            lat__lte=lat+distance,
            lng__gte=lng-distance, 
            lng__lte=lng+distance
        )
    
    @classmethod
    def get_by_city_and_district(cls, city: str, district: Optional[str] = None) -> QuerySet:
        """
        Find addresses by city and optionally district.
        
        Args:
            city: City name
            district: Optional district name
            
        Returns:
            QuerySet of Address objects
        """
        query = {'city__iexact': city}
        if district:
            query['district__iexact'] = district
        
        return cls.model_class.objects.filter(**query)
    
    @classmethod
    def create_or_update(cls, data: Dict[str, Any]) -> Tuple[Address, bool]:
        """
        Create a new address or update if it already exists with the same coordinates.
        
        Args:
            data: Address data
            
        Returns:
            Tuple of (address, created) where created is a boolean
        """
        lat = data.get('lat')
        lng = data.get('lng')
        
        if lat and lng:
            # Try to find an existing address with these coordinates
            try:
                existing = cls.model_class.objects.get(lat=lat, lng=lng)
                # Update fields
                for key, value in data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                existing.save()
                return existing, False
            except cls.model_class.DoesNotExist:
                # Create new address
                pass
        
        # Create new address
        return cls.create(**data), True 