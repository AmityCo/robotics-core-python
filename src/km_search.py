"""
Knowledge Management Search Module
Handles all KM search operations with proper typing and parallel execution
"""

import time
from typing import List, Dict, Any, Optional, Union
from concurrent.futures import ThreadPoolExecutor, Future
from pydantic import BaseModel
import requests
import logging
from src.app_config import config

logger = logging.getLogger(__name__)

# Type definitions matching the Amity KM API response structure
class KMDocument(BaseModel):
    id: str
    content: str
    sampleQuestions: Optional[str] = None
    metadata: Optional[str] = None
    publicId: Optional[str] = None
    contentTh: Optional[str] = None
    contentEn: Optional[str] = None
    title: Optional[str] = None

class KMDataItem(BaseModel):
    score: float
    rerankerScore: float
    document: KMDocument
    documentId: str

class KMSearchResponse(BaseModel):
    total: int
    source: str
    answers: List[Any]  # Usually empty in the examples
    data: List[KMDataItem]

class KMBatchSearchRequest(BaseModel):
    queries: List[str]
    language: str = "en"
    km_id: str
    km_token: str
    max_results: int = 10

class KMSearchRequest(BaseModel):
    query: str
    language: str = "en"
    km_id: str
    km_token: str

class KMSearchResult(BaseModel):
    success: bool
    query: str
    data: Optional[List[KMDataItem]] = None
    error: Optional[str] = None

def perform_single_km_search(query: str, knowledge_id: int, km_token: str, language: str) -> KMSearchResult:
    """
    Perform a single KM search - helper function for parallel execution
    """
    try:
        response: requests.Response = requests.post(
            config.AMITY_KM_API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {km_token}"
            },
            json={
                "content": query,
                "knowledgeId": knowledge_id,
                "language": language
            },
            timeout=config.REQUEST_TIMEOUT
        )
        
        if response.ok:
            result = response.json()
            logger.info(f"KM API response for '{query}': found {len(result.get('data', []))} items")
            
            # Parse the response into our typed model
            km_response = KMSearchResponse.model_validate(result)
            
            return KMSearchResult(
                success=True,
                query=query,
                data=km_response.data
            )
        else:
            error_msg = f"Query '{query}': {response.status_code} - {response.text}"
            logger.warning(f"KM API error: {error_msg}")
            return KMSearchResult(
                success=False,
                query=query,
                error=error_msg
            )
            
    except requests.RequestException as e:
        error_msg = f"Query '{query}': Request failed - {str(e)}"
        logger.warning(f"Request error: {error_msg}")
        return KMSearchResult(
            success=False,
            query=query,
            error=error_msg
        )
    except Exception as e:
        error_msg = f"Query '{query}': Unexpected error - {str(e)}"
        logger.error(error_msg)
        return KMSearchResult(
            success=False,
            query=query,
            error=error_msg
        )

def batch_search_km(request: KMBatchSearchRequest) -> KMSearchResponse:
    """
    Batch search the knowledge management system via Amity Solutions API
    Performs multiple searches, deduplicates, and returns top results sorted by reranker score
    """
    logger.info(f"Batch searching KM with {len(request.queries)} queries, language: {request.language}, max_results: {request.max_results}")
    start = time.time()
    # Convert km_id to integer as required by the API
    try:
        knowledge_id = int(request.km_id)
    except ValueError:
        raise ValueError(f"Invalid knowledgeId: {request.km_id} must be a number")
    
    # Remove duplicates and empty strings from queries
    unique_queries = list(set([q.strip() for q in request.queries if q and q.strip()]))
    
    if not unique_queries:
        return KMSearchResponse(
            total=0,
            source="",
            answers=[],
            data=[]
        )
    
    logger.info(f"Processing {len(unique_queries)} unique queries: {unique_queries}")
    
    # Perform searches in parallel using ThreadPoolExecutor
    all_results: List[KMDataItem] = []
    search_errors: List[str] = []
    source = "batch"
    
    with ThreadPoolExecutor(max_workers=min(len(unique_queries), 10)) as executor:
        # Submit all search tasks
        future_to_query: Dict[Future[KMSearchResult], str] = {
            executor.submit(perform_single_km_search, query, knowledge_id, request.km_token, request.language): query
            for query in unique_queries
        }
        
        # Collect results as they complete
        for future in future_to_query:
            try:
                result = future.result()
                if result.success and result.data:
                    all_results.extend(result.data)
                elif not result.success and result.error:
                    search_errors.append(result.error)
            except Exception as e:
                query = future_to_query[future]
                error_msg = f"Query '{query}': Unexpected error - {str(e)}"
                logger.error(error_msg)
                search_errors.append(error_msg)
    
    # Deduplicate by document ID
    seen_doc_ids = set()
    deduplicated_results: List[KMDataItem] = []
    
    for item in all_results:
        doc_id = item.documentId or item.document.id
        if doc_id and doc_id not in seen_doc_ids:
            seen_doc_ids.add(doc_id)
            deduplicated_results.append(item)
    
    # Sort by reranker score (highest first)
    deduplicated_results.sort(key=lambda x: x.rerankerScore, reverse=True)
    
    # Limit to max_results
    final_results = deduplicated_results[:request.max_results]

    logger.info(f"Batch search complete in {time.time() - start:.2f}s: {len(all_results)} total results, {len(deduplicated_results)} unique documents, returning top {len(final_results)}")

    if search_errors:
        logger.warning(f"Some searches failed: {search_errors}")
    
    # Return response matching the KM API structure
    return KMSearchResponse(
        total=len(final_results),
        source=source,
        answers=[],
        data=final_results
    )

def single_search_km(request: KMSearchRequest) -> KMSearchResponse:
    """
    Perform a single KM search and return the result
    """
    logger.info(f"Searching KM with query: {request.query}, language: {request.language}")
    
    # Convert km_id to integer as required by the API
    try:
        knowledge_id = int(request.km_id)
    except ValueError:
        raise ValueError(f"Invalid knowledgeId: {request.km_id} must be a number")
    
    response: requests.Response = requests.post(
        config.AMITY_KM_API_URL,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {request.km_token}"
        },
        json={
            "content": request.query,
            "knowledgeId": knowledge_id,
            "language": request.language
        },
        timeout=config.REQUEST_TIMEOUT
    )

    if not response.ok:
        logger.error(f"KM API error: {response.status_code} - {response.text}")
        raise requests.HTTPError(f"KM API returned {response.status_code}: {response.text}")

    result = response.json()
    logger.info(f"KM API response: {result}")
    
    # Parse and return the response as typed model
    return KMSearchResponse.model_validate(result)
