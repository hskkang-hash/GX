"""
Partner Utilities

Pure utility functions for partner operations.
These functions should be stateless and not contain business logic.
"""

import re
import secrets
import string
import random
import hashlib
import hmac
import base64
import json
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from urllib.parse import urlparse
from core.user.models import UserGroup

class PartnerUtils:
    """
    Utility functions for Partner operations
    
    This class contains only pure utility functions that:
    - Don't interact with database
    - Don't contain business logic
    - Are stateless and reusable
    """
    
    @staticmethod
    def validate_api_key_format(api_key: str) -> bool:
        """
        Validate API key format
        
        Args:
            api_key: API key to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not api_key or len(api_key.strip()) < 16:  # MIN_API_KEY_LENGTH
            return False
        
        # API key should contain only alphanumeric characters and some special chars
        pattern = r'^[A-Za-z0-9_-]+$'
        return bool(re.match(pattern, api_key.strip()))
    
    @staticmethod
    def validate_url_format(url: str) -> bool:
        """
        Validate URL format
        
        Args:
            url: URL to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not url:
            return True  # URL is optional
        
        try:
            result = urlparse(url.strip())
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    @staticmethod
    def validate_partner_code(code: str) -> bool:
        """
        Validate partner code format
        
        Args:
            code: Code to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not code or len(code.strip()) < 2:
            return False
        
        # Code should contain only alphanumeric characters and underscores/hyphens
        pattern = r'^[A-Za-z0-9_-]+$'
        return bool(re.match(pattern, code.strip()))
    
    @staticmethod
    def format_partner_data(partner_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format and clean partner data
        
        Args:
            partner_data: Raw partner data
            
        Returns:
            Dict: Cleaned and formatted partner data
        """
        cleaned_data = {}
        
        for key, value in partner_data.items():
            if isinstance(value, str):
                # Strip whitespace from string fields
                cleaned_data[key] = value.strip()
            else:
                cleaned_data[key] = value
        
        # Ensure code is uppercase
        if 'code' in cleaned_data and cleaned_data['code']:
            cleaned_data['code'] = cleaned_data['code'].upper()
        
        return cleaned_data
    
    @staticmethod
    def generate_partner_code(name: str, existing_codes: list = None) -> str:
        """
        Generate partner code from name
        
        Args:
            name: Partner name
            existing_codes: List of existing codes to avoid duplicates
            
        Returns:
            str: Generated partner code
        """
        if not name:
            return ""
        
        # Take first 3 characters of each word, uppercase
        words = name.strip().split()
        code_parts = []
        
        for word in words[:3]:  # Max 3 words
            if len(word) >= 3:
                code_parts.append(word[:3].upper())
            else:
                code_parts.append(word.upper())
        
        base_code = ''.join(code_parts)
        
        # If no existing codes provided, return base code
        if not existing_codes:
            return base_code
        
        # Handle duplicates by adding numbers
        if base_code not in existing_codes:
            return base_code
        
        counter = 1
        while f"{base_code}{counter:02d}" in existing_codes:
            counter += 1
        
        return f"{base_code}{counter:02d}"
    
    @staticmethod
    def generate_api_key(length: int = 32) -> str:
        """
        Generate a secure API key
        
        Args:
            length: Length of the API key
            
        Returns:
            str: Generated API key
        """
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def generate_refresh_token(length: int = 64) -> str:
        """
        Generate a secure refresh token
        
        Args:
            length: Length of the refresh token
            
        Returns:
            str: Generated refresh token
        """
        alphabet = string.ascii_letters + string.digits + '-_'
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def generate_refresh_token_expiry(days: int = 30) -> datetime:
        """
        Generate refresh token expiry datetime
        
        Args:
            days: Number of days from now for expiry (default: 30)
            
        Returns:
            datetime: Expiry datetime
        """
        return timezone.now() + timedelta(days=days)
    
    @staticmethod
    def is_refresh_token_expired(expires_at: Optional[datetime]) -> bool:
        """
        Check if refresh token is expired
        
        Args:
            expires_at: Expiry datetime
            
        Returns:
            bool: True if expired, False otherwise
        """
        if not expires_at:
            return False  # No expiry means never expires
        
        return timezone.now() > expires_at
    
    @staticmethod
    def validate_refresh_token_format(refresh_token: str) -> bool:
        """
        Validate refresh token format
        
        Args:
            refresh_token: Refresh token to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not refresh_token or len(refresh_token.strip()) < 32:
            return False
        
        # Refresh token should contain only alphanumeric characters and some special chars
        pattern = r'^[A-Za-z0-9_-]+$'
        return bool(re.match(pattern, refresh_token.strip()))
    
    @staticmethod
    def validate_api_callback_structure(callback_data: Dict[str, Any]) -> bool:
        """
        Validate API callback URL structure
        
        Args:
            callback_data: Callback data dictionary
            
        Returns:
            bool: True if structure is valid, False otherwise
        """
        if not callback_data:
            return True  # Optional field
        
        required_keys = {"DeliveryStatusCallback", "DroneBaseStation", "DroneUserNotice"}
        
        # Check if all required keys are present
        if not required_keys.issubset(callback_data.keys()):
            return False
        
        # Check if there are any extra keys
        if not set(callback_data.keys()).issubset(required_keys):
            return False
        
        # Validate URL format for each callback
        for key, url in callback_data.items():
            if url and not PartnerUtils.validate_url_format(url):
                return False
        
        return True
    
    @staticmethod
    def get_default_api_callback() -> Dict[str, str]:
        """
        Get default API callback structure
        
        Returns:
            Dict: Default callback structure
        """
        return {
            "DeliveryStatusCallback": "",
            "DroneBaseStation": "",
            "DroneUserNotice": ""
        }
    
    @staticmethod
    def normalize_api_callback(callback_data: Optional[Dict[str, Any]]) -> Dict[str, str]:
        """
        Normalize API callback data to ensure proper structure
        
        Args:
            callback_data: Raw callback data
            
        Returns:
            Dict: Normalized callback data
        """
        default_callback = PartnerUtils.get_default_api_callback()
        
        if not callback_data:
            return default_callback
        
        # Merge with defaults and validate
        normalized = default_callback.copy()
        for key in default_callback.keys():
            if key in callback_data:
                url = callback_data[key]
                if url and isinstance(url, str):
                    normalized[key] = url.strip()
        
        return normalized
    
    @staticmethod
    def mask_sensitive_data(partner_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mask sensitive partner data for logging
        
        Args:
            partner_data: Partner data dictionary
            
        Returns:
            Dict: Masked data dictionary
        """
        masked_data = partner_data.copy()
        
        # Mask API key
        if 'api_key' in masked_data and masked_data['api_key']:
            api_key = masked_data['api_key']
            if len(api_key) > 8:
                masked_data['api_key'] = api_key[:4] + '*' * (len(api_key) - 8) + api_key[-4:]
            else:
                masked_data['api_key'] = '*' * len(api_key)
        
        # Mask refresh token
        if 'refresh_token' in masked_data and masked_data['refresh_token']:
            refresh_token = masked_data['refresh_token']
            if len(refresh_token) > 12:
                masked_data['refresh_token'] = refresh_token[:6] + '*' * (len(refresh_token) - 12) + refresh_token[-6:]
            else:
                masked_data['refresh_token'] = '*' * len(refresh_token)
        
        # Mask API callback URLs
        if 'api_callback_url' in masked_data and masked_data['api_callback_url']:
            masked_callbacks = {}
            for key, url in masked_data['api_callback_url'].items():
                if url:
                    masked_callbacks[key] = '***masked_url***'
                else:
                    masked_callbacks[key] = url
            masked_data['api_callback_url'] = masked_callbacks
        
        return masked_data
    
    @staticmethod
    def generate_partner_code_auto(name: str, group: UserGroup) -> str:
        """
        Auto-generate unique partner code from name with timestamp
        
        Args:
            name: Partner name
            group: Group object
        Returns:
            str: Generated unique partner code
        """

        
        # Add timestamp and random suffix for uniqueness
        timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
        
        return f"ms_{group.name}_{timestamp}"
    
    @staticmethod
    def extract_context_info(request=None, user=None, additional_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Extract context information for secure token generation
        
        Args:
            request: HTTP request object (optional)
            user: User object (optional) 
            additional_context: Additional context data (optional)
            
        Returns:
            Dict: Context information
        """
        context = {
            'timestamp': timezone.now().isoformat(),
            'uuid': str(uuid.uuid4()),
            'entropy': secrets.token_hex(8)
        }
        
        # Extract request info if available
        if request:
            context.update({
                'user_agent': request.META.get('HTTP_USER_AGENT', 'unknown')[:100],  # Limit length
                'remote_addr': request.META.get('REMOTE_ADDR', 'unknown'),
                'http_host': request.META.get('HTTP_HOST', 'unknown'),
                'request_method': request.method if hasattr(request, 'method') else 'unknown'
            })
        
        # Extract user info if available
        if user:
            context.update({
                'user_id': getattr(user, 'id', 'unknown'),
                'username': getattr(user, 'username', 'unknown')[:50],  # Limit length
                'user_type': 'authenticated' if user.is_authenticated else 'anonymous'
            })
        
        # Add additional context if provided
        if additional_context:
            # Only include safe, non-sensitive data
            safe_keys = ['partner_id', 'partner_code', 'action_type', 'group_id']
            for key in safe_keys:
                if key in additional_context:
                    context[key] = str(additional_context[key])[:100]  # Limit length
        
        return context
    
    @staticmethod
    def create_context_hash(context: Dict[str, Any]) -> str:
        """
        Create a hash from context information
        
        Args:
            context: Context information dictionary
            
        Returns:
            str: Base64 encoded hash of context
        """
        # Sort context keys for consistent hashing
        context_str = json.dumps(context, sort_keys=True, separators=(',', ':'))
        
        # Create SHA256 hash
        hash_object = hashlib.sha256(context_str.encode('utf-8'))
        hash_bytes = hash_object.digest()
        
        # Return base64 encoded hash (first 16 bytes for shorter token)
        return base64.urlsafe_b64encode(hash_bytes[:16]).decode('utf-8').rstrip('=')
    
    @staticmethod
    def create_hmac_signature(data: str, secret_key: str = None) -> str:
        """
        Create HMAC signature for data integrity
        
        Args:
            data: Data to sign
            secret_key: Secret key for HMAC (uses Django SECRET_KEY if not provided)
            
        Returns:
            str: Base64 encoded HMAC signature
        """
        if not secret_key:
            secret_key = getattr(settings, 'SECRET_KEY', 'default-secret-key')
        
        # Create HMAC-SHA256 signature
        signature = hmac.new(
            secret_key.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        # Return base64 encoded signature (first 12 bytes for shorter token)
        return base64.urlsafe_b64encode(signature[:12]).decode('utf-8').rstrip('=')
    
    @staticmethod
    def generate_api_key_with_prefix(request=None, user=None, additional_context: Dict[str, Any] = None) -> str:
        """
        Generate secure API key with 'pk_' prefix and context information
        
        Args:
            request: HTTP request object (optional)
            user: User object (optional)
            additional_context: Additional context data (optional)
            
        Returns:
            str: Generated secure API key with prefix
        """
        # Extract context information
        context = PartnerUtils.extract_context_info(request, user, additional_context)
        
        # Create context hash
        context_hash = PartnerUtils.create_context_hash(context)
        
        # Generate random token
        random_token = secrets.token_urlsafe(16)  # Reduced size since we have context
        
        # Combine context hash and random token
        combined_data = f"{context_hash}_{random_token}"
        
        # Create HMAC signature
        signature = PartnerUtils.create_hmac_signature(combined_data)
        
        # Final secure token format: pk_{context_hash}_{random_token}_{signature}
        secure_token = f"{context_hash}_{random_token}_{signature}"
        
        return f"pk_{secure_token}"
    
    @staticmethod
    def generate_secure_refresh_token(request=None, user=None, additional_context: Dict[str, Any] = None) -> str:
        """
        Generate secure refresh token with context information
        
        Args:
            request: HTTP request object (optional)
            user: User object (optional)  
            additional_context: Additional context data (optional)
            
        Returns:
            str: Generated secure refresh token
        """
        # Extract context information
        context = PartnerUtils.extract_context_info(request, user, additional_context)
        context['token_type'] = 'refresh'  # Add token type
        
        # Create context hash
        context_hash = PartnerUtils.create_context_hash(context)
        
        # Generate random token (longer for refresh tokens)
        random_token = secrets.token_urlsafe(24)
        
        # Combine context hash and random token
        combined_data = f"{context_hash}_{random_token}"
        
        # Create HMAC signature
        signature = PartnerUtils.create_hmac_signature(combined_data)
        
        # Final secure token format: {context_hash}_{random_token}_{signature}
        return f"{context_hash}_{random_token}_{signature}"
