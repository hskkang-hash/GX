import os
import json
import logging
import certifi
import time
import threading
from typing import Dict, List, Any, Optional, Tuple, Union
from urllib3.exceptions import InsecureRequestWarning
import urllib3
from opensearchpy import OpenSearch, helpers, RequestsHttpConnection, TransportError
from django.conf import settings
from functools import wraps

# Suppress only the InsecureRequestWarning from urllib3
urllib3.disable_warnings(InsecureRequestWarning)

# OpenSearch configuration
INDEX_OPENSEARCH_NAME = os.environ.get('OPENSEARCH_INDEX', 'drone_logs_stg')
OPENSEARCH_HOST = os.environ.get('OPENSEARCH_HOST', 'https://gx-opensearch-api.gaion.dev')
# W0-0: 자격증명 기본값 제거 (§0.4 예외 승인 — 시크릿 제거만, 로직 불변)
OPENSEARCH_USERNAME = os.environ.get('OPENSEARCH_USERNAME', '')
OPENSEARCH_PASSWORD = os.environ.get('OPENSEARCH_PASSWORD', '')

# Circuit breaker configuration
MAX_FAILURES = 5
RESET_TIMEOUT = 60  # seconds
REQUEST_TIMEOUT = 30  # seconds
CONNECTION_TIMEOUT = 10  # seconds

# Default mapping for drone logs
DEFAULT_MAPPING = {
    "mappings": {
        "properties": {
            "timestamp": {"type": "date"},  # Required for sorting
            "sysId": {"type": "integer"},
            "compId": {"type": "integer"},
            "msgType": {"type": "keyword"},
            "uniqueId": {"type": "keyword"},
            # GLOBAL_POSITION_INT fields
            "latitude": {"type": "double"},
            "longitude": {"type": "double"},
            "altitude": {"type": "double"},
            "relativeAltitude": {"type": "double"},
            "heading": {"type": "double"},
            "groundSpeed": {"type": "double"},
            "airSpeed": {"type": "double"},
            "climbRate": {"type": "double"},
            # VIBRATION fields
            "vibrationX": {"type": "double"},
            "vibrationY": {"type": "double"},
            "vibrationZ": {"type": "double"},
            "clipping0": {"type": "integer"},
            "clipping1": {"type": "integer"},
            "clipping2": {"type": "integer"},
            # RAW_IMU fields
            "xacc": {"type": "integer"},
            "yacc": {"type": "integer"},
            "zacc": {"type": "integer"},
            "xgyro": {"type": "integer"},
            "ygyro": {"type": "integer"},
            "zgyro": {"type": "integer"},
            "xmag": {"type": "integer"},
            "ymag": {"type": "integer"},
            "zmag": {"type": "integer"},
            # SCALED_IMU2 fields
            "temperature": {"type": "double"},
            # Additional fields for state analysis
            "batteryLevel": {"type": "double"},
            "systemStatus": {"type": "keyword"},
            "droneState": {"type": "keyword"},
            "flightMode": {"type": "keyword"},
            "currentMissionId": {"type": "keyword"},
            "gpsSatellites": {"type": "integer"},
            "gpsAccuracy": {"type": "double"},
            "windSpeed": {"type": "double"}
        }
    },
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 1
    }
}

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """Circuit breaker pattern to prevent cascading failures."""
    
    def __init__(self, max_failures=MAX_FAILURES, reset_timeout=RESET_TIMEOUT):
        self.max_failures = max_failures
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()
    
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        with self._lock:
            if self.state == 'OPEN':
                if time.time() - self.last_failure_time > self.reset_timeout:
                    self.state = 'HALF_OPEN'
                    logger.info("Circuit breaker transitioning to HALF_OPEN")
                else:
                    raise Exception("Circuit breaker is OPEN - service temporarily unavailable")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful operation."""
        with self._lock:
            self.failure_count = 0
            self.state = 'CLOSED'
    
    def _on_failure(self):
        """Handle failed operation."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.max_failures:
                self.state = 'OPEN'
                logger.error(f"Circuit breaker opened after {self.failure_count} failures")

def safe_opensearch_call(func):
    """Decorator to safely handle OpenSearch operations with retries and fallbacks."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except (TransportError, ConnectionError, TimeoutError) as e:
                if attempt == max_retries - 1:
                    logger.error(f"Final attempt failed for {func.__name__}: {str(e)}")
                    # Return safe fallback based on function
                    if 'search' in func.__name__:
                        return {"hits": {"hits": []}}
                    elif 'get' in func.__name__:
                        return {}
                    elif 'count' in func.__name__:
                        return 0
                    else:
                        return None
                else:
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}")
                    time.sleep(retry_delay)
                    retry_delay *= 2
            except Exception as e:
                logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
                if 'search' in func.__name__:
                    return {"hits": {"hits": []}}
                elif 'get' in func.__name__:
                    return {}
                elif 'count' in func.__name__:
                    return 0
                else:
                    return None
        return None
    return wrapper

class OpenSearchDataService:
    """Service for connecting to and retrieving data from OpenSearch."""
    
    def __init__(self, hosts=None, http_auth=None, verify_certs=False, use_ssl=True):
        """Initialize OpenSearch client connection."""
        self.hosts = hosts or [f"{OPENSEARCH_HOST}"]
        self.http_auth = http_auth or (OPENSEARCH_USERNAME, OPENSEARCH_PASSWORD)
        self.verify_certs = verify_certs
        self.use_ssl = use_ssl
        self.circuit_breaker = CircuitBreaker()
        self.client = None
        self._initialize_client()
        self._ensure_index_exists()

    def _initialize_client(self):
        """Initialize OpenSearch client with crash protection."""
        try:
            self.client = self._create_client()
        except Exception as e:
            logger.error(f"Failed to initialize OpenSearch client: {str(e)}")
            self.client = None

    def _create_client(self):
        """Create OpenSearch client with CRASH-PROOF configuration."""
        try:
            from opensearchpy import OpenSearch
            from opensearchpy.connection import RequestsHttpConnection
            
            # CRASH-PROOF CONFIGURATION
            client = OpenSearch(
                hosts=self.hosts,
                http_auth=self.http_auth,
                use_ssl=self.use_ssl,
                verify_certs=self.verify_certs,
                ssl_show_warn=False,
                connection_class=RequestsHttpConnection,
                
                # TIMEOUT CONFIGURATION - FIXED: Use integer instead of string
                timeout=REQUEST_TIMEOUT,
                max_retries=3,
                retry_on_timeout=True,
                retry_on_status=[500, 502, 503, 504],
                
                # CONNECTION POOLING (SAFE)
                http_compress=True,
                maxsize=10,  # Conservative pool size
                keep_alive=False,  # Disable keep-alive to prevent hanging
                
                # SSL CONFIGURATION
                ssl_assert_hostname=False,
                ssl_assert_fingerprint=None,
                
                # DISABLE SNIFFING (causes connection issues)
                sniff_on_start=False,
                sniff_on_connection_fail=False,
                sniffer_timeout=None,
                
                # REQUEST CONFIGURATION
                headers={'Content-Type': 'application/json'},
                
                # CERTIFICATE VERIFICATION
                ca_certs=certifi.where() if self.verify_certs else None,
            )
            
            # Test connection
            try:
                client.ping()
                logger.info("Successfully connected to OpenSearch with crash-proof configuration")
            except Exception as e:
                logger.warning(f"OpenSearch ping failed: {str(e)}")
                # Don't raise - client might still work for some operations
            
            return client
            
        except Exception as e:
            logger.error(f"Failed to create OpenSearch client: {str(e)}")
            raise

    @safe_opensearch_call
    def _ensure_index_exists(self):
        """Ensure the index exists with proper mapping."""
        if not self.client:
            logger.warning("OpenSearch client not available")
            return
            
        try:
            if not self.client.indices.exists(index=INDEX_OPENSEARCH_NAME):
                self.client.indices.create(
                    index=INDEX_OPENSEARCH_NAME,
                    body=DEFAULT_MAPPING
                )
                logger.info(f"Created index {INDEX_OPENSEARCH_NAME} with mapping")
            else:
                # Only update mapping if index exists but mapping is different
                try:
                    current_mapping = self.client.indices.get_mapping(index=INDEX_OPENSEARCH_NAME)
                    if not current_mapping or INDEX_OPENSEARCH_NAME not in current_mapping:
                        # Index exists but no mapping, create it
                        self.client.indices.put_mapping(
                            index=INDEX_OPENSEARCH_NAME,
                            body=DEFAULT_MAPPING["mappings"]
                        )
                        logger.info(f"Created mapping for existing index {INDEX_OPENSEARCH_NAME}")
                    else:
                        logger.info(f"Index {INDEX_OPENSEARCH_NAME} already exists with mapping")
                except Exception as e:
                    logger.warning(f"Could not update mapping: {str(e)}")
        except Exception as e:
            logger.error(f"Error ensuring index exists: {str(e)}")

    @safe_opensearch_call
    def get_cluster_health(self) -> Dict[str, Any]:
        """Get the health status of the OpenSearch cluster."""
        if not self.client:
            return {"status": "unavailable", "reason": "client_not_initialized"}
        
        return self.circuit_breaker.call(self.client.cluster.health)
    
    @safe_opensearch_call
    def search(self, query: Dict[str, Any], size: int = 100, sort: List[Dict] = None, aggs: Dict = None) -> Dict[str, Any]:
        """Execute a search query against the specified index."""
        if not self.client:
            return {"hits": {"hits": []}}
        
        try:
            # Ensure index exists
            if not self.client.indices.exists(index=INDEX_OPENSEARCH_NAME):
                logger.warning(f"Index {INDEX_OPENSEARCH_NAME} does not exist")
                return {"hits": {"hits": []}}

            body = {"query": query} if "query" not in query else query
            
            if sort:
                body["sort"] = sort
                
            if aggs:
                body["aggs"] = aggs
                
            return self.circuit_breaker.call(
                self.client.search,
                index=INDEX_OPENSEARCH_NAME,
                body=body,
                size=size
            )
        except Exception as e:
            logger.error(f"Search failed for index {INDEX_OPENSEARCH_NAME}: {str(e)}")
            return {"hits": {"hits": []}}
    
    @safe_opensearch_call
    def search_dsl(self, index: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a search using a complete OpenSearch DSL query body.
        This allows full control over the query, including sorting, aggregations, etc.
        
        Args:
            index: The index name to search
            body: Complete query DSL body with query, sort, aggs, etc.
            
        Returns:
            Search results dictionary
        """
        if not self.client:
            return {"hits": {"hits": []}}
        
        return self.circuit_breaker.call(
            self.client.search,
            index=index,
            body=body
        )
    
    def create_bool_query(self, must: List[Dict] = None, must_not: List[Dict] = None, 
                         should: List[Dict] = None, filter: List[Dict] = None) -> Dict[str, Any]:
        """
        Create a bool query with must, must_not, should, and filter clauses.
        
        Args:
            must: List of queries that must match
            must_not: List of queries that must not match
            should: List of queries that should match (at least one if specified)
            filter: List of queries that must match but don't contribute to score
            
        Returns:
            Bool query dictionary
        """
        bool_query = {"bool": {}}
        
        if must:
            bool_query["bool"]["must"] = must
        if must_not:
            bool_query["bool"]["must_not"] = must_not
        if should:
            bool_query["bool"]["should"] = should
        if filter:
            bool_query["bool"]["filter"] = filter
            
        return bool_query
    
    def create_term_query(self, field: str, value: Any) -> Dict[str, Any]:
        """
        Create a term query for exact field matching.
        
        Args:
            field: Field name
            value: Field value to match
            
        Returns:
            Term query dictionary
        """
        return {"term": {field: value}}
    
    def create_multi_match_query(self, field: str, value: Any) -> Dict[str, Any]:
        """
        Create a multi-match query for full-text search.
        
        Args:
            field: Field name
            value: Field value to match
        """
        return {"multi_match": {
            "query": value,
            "fields": [field, field + ".keyword"],
            "type": "phrase"
        }}
    
    def create_terms_query(self, field: str, values: List[Any]) -> Dict[str, Any]:
        """
        Create a terms query for matching multiple values.
        
        Args:
            field: Field name
            values: List of values to match
            
        Returns:
            Terms query dictionary
        """
        return {"terms": {field: values}}
    
    def create_match_query(self, field: str, value: Any) -> Dict[str, Any]:
        """
        Create a match query for full-text search.
        
        Args:
            field: Field name
            value: Field value to match
            
        Returns:
            Match query dictionary
        """
        return {"match": {field: value}}
    
    def create_range_query(self, field: str, gte: Any = None, gt: Any = None, 
                          lte: Any = None, lt: Any = None) -> Dict[str, Any]:
        """
        Create a range query for numeric or date ranges.
        
        Args:
            field: Field name
            gte: Greater than or equal value
            gt: Greater than value
            lte: Less than or equal value
            lt: Less than value
            
        Returns:
            Range query dictionary
        """
        range_params = {}
        if gte is not None:
            range_params["gte"] = gte
        if gt is not None:
            range_params["gt"] = gt
        if lte is not None:
            range_params["lte"] = lte
        if lt is not None:
            range_params["lt"] = lt
            
        return {"range": {field: range_params}}
    
    @safe_opensearch_call
    def search_drone_positions_batch(self, unique_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        PERFORMANCE OPTIMIZATION: Batch search for multiple drone positions in a single query.
        This reduces network overhead and improves performance significantly.
        
        Args:
            unique_ids: List of drone unique IDs
            
        Returns:
            Dictionary mapping unique_id to position data
        """
        if not self.client or not unique_ids:
            return {uid: {"latitude": 0, "longitude": 0, "timestamp": 0} for uid in unique_ids}
        
        try:
            # PERFORMANCE OPTIMIZATION: Use multi-search API for batch queries
            body = []
            for unique_id in unique_ids:
                # Header for each search request
                body.append({"index": INDEX_OPENSEARCH_NAME})
                # Query body for each search request
                body.append({
                    "size": 1,
                    "query": {
                        "bool": {
                            "must": [
                                self.create_multi_match_query("uniqueId", unique_id),
                                {"term": {"msgType": "GLOBAL_POSITION_INT"}}
                            ],
                            "filter": [
                                {"exists": {"field": "latitude"}},
                                {"exists": {"field": "longitude"}}
                            ]
                        }
                    },
                    "sort": [{"timestamp": {"order": "desc"}}],
                    "_source": ["latitude", "longitude", "timestamp"],
                    "timeout": "5s"  # Reduced timeout for batch operations
                })
            
            # Execute batch search with circuit breaker protection
            start_time = time.time()
            result = self.circuit_breaker.call(
                self.client.msearch,
                body=body
            )
            batch_time = (time.time() - start_time) * 1000
            
            # Log batch performance
            if batch_time > 1000:  # Increased threshold
                logger.warning(f"Slow batch OpenSearch query for {len(unique_ids)} drones: {batch_time:.2f}ms")
            
            # Process results
            positions = {}
            if 'responses' in result:
                for i, response in enumerate(result['responses']):
                    unique_id = unique_ids[i]
                    if response.get('hits', {}).get('hits', []):
                        source = response['hits']['hits'][0]['_source']
                        positions[unique_id] = {
                            "latitude": source.get('latitude', 0),
                            "longitude": source.get('longitude', 0),
                            "timestamp": source.get('timestamp', 0)
                        }
                    else:
                        positions[unique_id] = {"latitude": 0, "longitude": 0, "timestamp": 0}
            
            return positions
            
        except Exception as e:
            logger.error(f"Failed to batch search drone positions: {str(e)}")
            # Fallback: return empty positions
            return {uid: {"latitude": 0, "longitude": 0, "timestamp": 0} for uid in unique_ids}

    def search_drone_logs_by_unique_id(self, unique_id: str, 
                                       msg_type: str = None, 
                                       time_from: str = None, time_to: str = None, 
                                       size: int = 100, sort_order: str = "desc",
                                       index: str = None) -> Dict[str, Any]:
        """
        Search drone logs by unique ID.
        
        Args:
            unique_id: Unique ID of the drone
            msg_type: Message type to filter (e.g., "GLOBAL_POSITION_INT")
            time_from: Start time in ISO format
            time_to: End time in ISO format
            size: Number of results to return
            sort_order: Sort order ("asc" or "desc")
            index: Index name to search (defaults to INDEX_OPENSEARCH_NAME)
        """
        # Use specified index or default
        search_index = index or INDEX_OPENSEARCH_NAME
        
        try:
            # Build must conditions
            must = []
            
            if unique_id is not None:
                must.append(self.create_multi_match_query("uniqueId", unique_id))
                
            if msg_type:
                must.append(self.create_multi_match_query("msgType", msg_type))
                
            # Add timestamp range if provided
            if time_from or time_to:
                range_params = {}
                if time_from:
                    range_params["gte"] = time_from
                if time_to:
                    range_params["lte"] = time_to
                    
                if range_params:
                    must.append({"range": {"timestamp": range_params}})
            
            # Create the query body
            body = {
                "size": size,
                "query": {
                    "bool": {
                        "must": must
                    }
                },
                "sort": [
                    {"timestamp": {"order": sort_order}}
                ]
            }
                   
            # Execute the search using the specified or default index
            return self.search_dsl(search_index, body)
            
        except Exception as e:
            logger.error(f"Failed to search drone logs for unique_id {unique_id}, msg_type {msg_type}, index {search_index}: {str(e)}")
            return {"hits": {"hits": []}}

    def search_drone_logs_by_unique_id_updated(
        self, 
        unique_id: str,
        msg_type: str = None,
        time_from: str = None,
        time_to: str = None,
        size: int = 100,
        sort_order: str = "desc"
    ) -> Dict[str, Any]:

        try:
            must_filters = []

            # Unique ID filter
            if unique_id:
                must_filters.append({"term": {"uniqueId": unique_id}})

            # msgType filter (keyword + text)
            if msg_type:
                must_filters.append({
                    "bool": {
                        "should": [
                            {"term": {"msgType.keyword": msg_type}},   # exact match
                            {"match": {"msgType": msg_type}}           # analyzed match
                        ],
                        "minimum_should_match": 1
                    }
                })

            # Timestamp range
            if time_from or time_to:
                range_params = {}
                if time_from:
                    range_params["gte"] = time_from
                if time_to:
                    range_params["lte"] = time_to

                must_filters.append({"range": {"timestamp": range_params}})

            # Final query
            body = {
                "size": size,
                "query": {
                    "bool": {
                        "filter": must_filters
                    }
                },
                "sort": [
                    {"timestamp": {"order": sort_order}}
                ]
            }

            return self.search_dsl(INDEX_OPENSEARCH_NAME, body)

        except Exception as e:
            logger.error(f"Failed to search drone logs for unique_id {unique_id}: {str(e)}")
            return {"hits": {"hits": []}}

    
    def search_drone_logs_by_sys_id_and_msg_type(self, sys_id: int = None, msg_type: str = None, 
                          time_from: str = None, time_to: str = None, 
                          size: int = 100, sort_order: str = "desc") -> Dict[str, Any]:
        """
        Search drone logs with common filtering parameters.
        Designed specifically for drone_logs index.
        
        Args:
            sys_id: System ID to filter by
            msg_type: Message type to filter by
            time_from: Start timestamp
            time_to: End timestamp
            size: Maximum number of results
            sort_order: Sort order (asc or desc)
            
        Returns:
            Search results
        """
        try:
            # Build must conditions
            must = []
            
            if sys_id is not None:
                must.append(self.create_multi_match_query("sysId", sys_id))
                
            if msg_type:
                must.append(self.create_multi_match_query("msgType", msg_type))
                
            # Add timestamp range if provided
            if time_from or time_to:
                range_params = {}
                if time_from:
                    range_params["gte"] = time_from
                if time_to:
                    range_params["lte"] = time_to
                    
                if range_params:
                    must.append({"range": {"timestamp": range_params}})
            
            # Create the query body
            body = {
                "size": size,
                "query": {
                    "bool": {
                        "must": must
                    }
                },
                "sort": [
                    {"timestamp": {"order": sort_order}}
                ]
            }
            
            # Execute the search
            return self.search_dsl(INDEX_OPENSEARCH_NAME, body)
            
        except Exception as e:
            logger.error(f"Failed to search drone logs for sys_id {sys_id} and msg_type {msg_type}: {str(e)}")
            return {"hits": {"hits": []}}
    
    def create_index(self, index: str, body: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create an index with optional settings and mappings.
        
        Args:
            index: The name of the index to create
            body: Index settings and mappings
            
        Returns:
            Creation response
        """
        try:
            if not self.client.indices.exists(index=index):
                return self.client.indices.create(index=index, body=body)
            logger.info(f"Index {index} already exists")
            return {"acknowledged": True, "index": index, "status": "already_exists"}
        except Exception as e:
            logger.error(f"Failed to create index {index}: {str(e)}")
            raise
    
    def delete_index(self, index: str) -> Dict[str, Any]:
        """
        Delete an index.
        
        Args:
            index: The name of the index to delete
            
        Returns:
            Deletion response
        """
        try:
            if self.client.indices.exists(index=index):
                return self.client.indices.delete(index=index)
            logger.info(f"Index {index} does not exist")
            return {"acknowledged": True, "index": index, "status": "not_found"}
        except Exception as e:
            logger.error(f"Failed to delete index {index}: {str(e)}")
            raise
    
    def index_document(self, index: str, doc_id: str, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Index a single document.
        
        Args:
            index: Index name
            doc_id: Document ID
            document: Document body
            
        Returns:
            Indexing response
        """
        try:
            return self.client.index(
                index=index,
                id=doc_id,
                body=document,
                refresh=True
            )
        except Exception as e:
            logger.error(f"Failed to index document {doc_id} in {index}: {str(e)}")
            raise
    
    def bulk_index(self, index: str, documents: List[Dict[str, Any]], id_field: str = 'id') -> Tuple[int, List[str]]:
        """
        Bulk index multiple documents.
        
        Args:
            index: Index name
            documents: List of document dicts
            id_field: Field name to use as document ID
            
        Returns:
            Tuple of (success_count, error_messages)
        """
        try:
            actions = [
                {
                    "_index": index,
                    "_id": doc.get(id_field, None),
                    "_source": doc
                }
                for doc in documents
            ]
            
            success, errors = 0, []
            for ok, item in helpers.streaming_bulk(self.client, actions, raise_on_error=False):
                if ok:
                    success += 1
                else:
                    errors.append(str(item))
            
            return success, errors
        except Exception as e:
            logger.error(f"Bulk indexing failed for index {index}: {str(e)}")
            raise
    
    def get_document(self, index: str, doc_id: str) -> Dict[str, Any]:
        """
        Get a document by ID.
        
        Args:
            index: Index name
            doc_id: Document ID
            
        Returns:
            Document data or None if not found
        """
        try:
            result = self.client.get(index=index, id=doc_id)
            return result.get('_source', {})
        except Exception as e:
            logger.error(f"Failed to get document {doc_id} from {index}: {str(e)}")
            if "404" in str(e):
                return {}
            raise
    
    def update_document(self, index: str, doc_id: str, document: Dict[str, Any], partial: bool = True) -> Dict[str, Any]:
        """
        Update a document.
        
        Args:
            index: Index name
            doc_id: Document ID
            document: Document fields to update
            partial: If True, performs partial update; otherwise full replacement
            
        Returns:
            Update response
        """
        try:
            if partial:
                return self.client.update(
                    index=index,
                    id=doc_id,
                    body={"doc": document},
                    refresh=True
                )
            else:
                return self.client.index(
                    index=index,
                    id=doc_id,
                    body=document,
                    refresh=True
                )
        except Exception as e:
            logger.error(f"Failed to update document {doc_id} in {index}: {str(e)}")
            raise
    
    def delete_document(self, index: str, doc_id: str) -> Dict[str, Any]:
        """
        Delete a document.
        
        Args:
            index: Index name
            doc_id: Document ID
            
        Returns:
            Deletion response
        """
        try:
            return self.client.delete(
                index=index,
                id=doc_id,
                refresh=True
            )
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id} from {index}: {str(e)}")
            raise
    
    def count_documents(self, index: str, query: Dict[str, Any] = None) -> int:
        """
        Count documents in an index.
        
        Args:
            index: Index name
            query: Optional query to filter the count
            
        Returns:
            Document count
        """
        try:
            query = query or {"query": {"match_all": {}}}
            result = self.client.count(index=index, body=query)
            return result.get('count', 0)
        except Exception as e:
            logger.error(f"Failed to count documents in {index}: {str(e)}")
            raise
            
    def search_by_query_string(self, index: str, query_string: str, fields: List[str] = None, 
                               size: int = 100) -> Dict[str, Any]:
        """
        Search using query string syntax.
        
        Args:
            index: Index name
            query_string: Query string in OpenSearch query string syntax
            fields: List of fields to search in, or None for all
            size: Maximum number of results to return
            
        Returns:
            Search results
        """
        try:
            query = {
                "query": {
                    "query_string": {
                        "query": query_string
                    }
                }
            }
            
            if fields:
                query["query"]["query_string"]["fields"] = fields
                
            return self.search(index, query, size)
        except Exception as e:
            logger.error(f"Query string search failed for index {index}: {str(e)}")
            raise
    
    def get_indices(self, pattern: str = "*") -> List[str]:
        """
        Get list of indices matching a pattern.
        
        Args:
            pattern: Index pattern to match
            
        Returns:
            List of index names
        """
        try:
            indices = self.client.indices.get(index=pattern)
            return list(indices.keys())
        except Exception as e:
            logger.error(f"Failed to get indices with pattern {pattern}: {str(e)}")
            raise
            
    def get_mapping(self, index: str) -> Dict[str, Any]:
        """
        Get the mapping for an index.
        
        Args:
            index: Index name
            
        Returns:
            Mapping information
        """
        try:
            return self.client.indices.get_mapping(index=index)
        except Exception as e:
            logger.error(f"Failed to get mapping for index {index}: {str(e)}")
            raise

    def reconnect(self):
        """Attempt to reconnect to OpenSearch."""
        try:
            logger.info("Attempting to reconnect to OpenSearch...")
            self._initialize_client()
            if self.client:
                self.client.ping()
                logger.info("Successfully reconnected to OpenSearch")
                return True
            else:
                logger.error("Failed to reconnect to OpenSearch")
                return False
        except Exception as e:
            logger.error(f"Reconnection failed: {str(e)}")
            return False

    def is_healthy(self) -> bool:
        """Check if the OpenSearch connection is healthy."""
        try:
            if not self.client:
                return False
            self.client.ping()
            return True
        except Exception:
            return False
