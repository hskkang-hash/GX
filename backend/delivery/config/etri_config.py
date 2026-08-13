"""
ETRI Integration Configuration
"""

# ETRI API Endpoints
ETRI_API_ENDPOINTS = {
    'production': 'https://etri-production-api.com/api',
    'staging': 'https://etri-staging-api.com/api', 
    'development': '{host}/{api_endpoint}'  # Points to our mock API
}

# ETRI Data Mapping
LOGISTICS_TYPE_MAPPING = {
    '전자제품': ['전자', 'electronic', 'device', 'electronics', 'elec'],
    '식품': ['음식', '식품', 'food', 'beverage'],
    '의약품': ['의약품', 'medicine', 'drug', 'pharmaceutical'],
    '의류': ['의류', 'clothing', 'apparel', 'fashion', 'cloth'],
    '서적': ['서적', 'book', 'magazine', 'document', 'documents', 'doc'],
    '승강물': ['승강물', 'elevator'],
    '수산물': ['수산물', 'seafood', 'fish'],
    '건자재': ['건자재', 'construction', 'building'],
    '시료': ['시료', 'sample', 'specimen'],
    '선물': ['선물', 'gift', 'present'],
    '보급': ['보급', 'supply', 'provision'],
    '취급주의': ['fragile', 'fragile items', 'frag', 'delicate', 'breakable'],
    '기타': ['기타', 'other', 'misc']
}

# ETRI Status Code Mapping - Using existing status codes
ETRI_STATUS_MAPPING = {
    0: 'completed_order',             # 배송완료 - Delivery is complete
    1: 'cancelled',             # 배송취소 - Delivery is rejected or delivery failed
    2: 'in_transit_processing', # 배송중 - Delivery is in progress  
    3: 'select_route_processing',     # 배송대기 - Waiting for delivery to start
    4: 'unverified_order',  # 접수완료 - Receipt completed but not confirmed by operator
    5: 'receipt_cancelled'      # 접수취소 - Receipt cancelled by operator or orderer
}

# Request Configuration
ETRI_REQUEST_CONFIG = {
    'timeout': 30,
    'retry_attempts': 3,
    'retry_delay': 1,  # seconds
    'headers': {
        'Content-Type': 'application/json',
        'User-Agent': 'GAION-Delivery-System/1.0'
    }
} 