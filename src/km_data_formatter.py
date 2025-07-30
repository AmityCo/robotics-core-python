"""
Knowledge Management Data Formatter
Handles formatting and extraction of KM search results for frontend consumption
"""
import json
import logging
import re
from typing import Dict, List

logger = logging.getLogger(__name__)


def extract_relevant_km_data(metadata_json: Dict, km_result) -> Dict:
    """
    Extract relevant data from KM search results based on metadata doc-ids.
    
    Args:
        metadata_json: The parsed metadata containing doc-ids
        km_result: The KM search result containing data items
        
    Returns:
        Dict with "items" array containing formatted data items for frontend consumption
    """
    try:
        # Extract doc-ids from metadata
        doc_ids_str = metadata_json.get('doc-ids', '')
        if not doc_ids_str:
            logger.warning("No doc-ids found in metadata")
            return {}
        
        # Parse doc-ids (format: "doc-784,doc-422")
        doc_ids = [doc_id.strip() for doc_id in doc_ids_str.split(',')]
        logger.info(f"Extracted doc-ids from metadata: {doc_ids}")
        
        relevant_data = []
        
        # Create a lookup dictionary for km_result data by publicId (doc-422, doc-763, etc.)
        km_data_lookup = {}
        for item in km_result.data:
            if item.document.publicId:
                km_data_lookup[item.document.publicId] = item
        
        logger.info(f"Available publicIds in KM data: {list(km_data_lookup.keys())}")
        
        # Create an array to store the formatted data items
        relevant_data = []
        
        # Process each doc-id and find corresponding data
        for doc_id in doc_ids:
            if doc_id in km_data_lookup:
                km_item = km_data_lookup[doc_id]
                document = km_item.document
                
                # Parse document metadata to get the rich data
                doc_metadata = {}
                if document.metadata:
                    try:
                        doc_metadata = json.loads(document.metadata)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse metadata for document {doc_id}: {document.metadata}")
                
                # Extract store name from metadata or use title/id as fallback
                store_name = doc_metadata.get('name', document.title or doc_id)
                
                # Extract thumbnail URL - check multiple possible sources
                thumbnail_url = None
                if 'images' in doc_metadata and isinstance(doc_metadata['images'], list) and len(doc_metadata['images']) > 0:
                    # Use first image as thumbnail
                    thumbnail_url = doc_metadata['images'][0].get('url', '')
                elif 'imageUrl' in doc_metadata and doc_metadata['imageUrl']:
                    thumbnail_url = doc_metadata['imageUrl']
                
                # Extract images array - include all images with non-empty URLs
                images = []
                if 'images' in doc_metadata and isinstance(doc_metadata['images'], list):
                    for img in doc_metadata['images']:
                        if isinstance(img, dict) and 'url' in img and img['url']:
                            image_item = {
                                "title": img.get('title', store_name),
                                "imageUrl": img['url']
                            }
                            # Add action if it exists
                            if 'action' in img and img['action']:
                                image_item['action'] = img['action']
                            images.append(image_item)
                
                # Also check if there's a standalone imageUrl that's not in the images array
                if 'imageUrl' in doc_metadata and doc_metadata['imageUrl']:
                    standalone_image_url = doc_metadata['imageUrl']
                    # Check if this URL is already in the images array
                    if not any(img.get('imageUrl') == standalone_image_url for img in images):
                        images.append({
                            "title": store_name,
                            "imageUrl": standalone_image_url
                        })
                
                # Extract navigation details
                navigation = {
                    "mapImageUrl": "",
                    "pin": {
                        "location": {
                            "x": 0,
                            "y": 0
                        },
                        "iconUrl": "",
                        "rotation": 0
                    },
                    "qrCodeUrl": "",
                    "clientGeoId": ""
                }
                
                if 'navigation' in doc_metadata and isinstance(doc_metadata['navigation'], dict):
                    nav_data = doc_metadata['navigation']
                    navigation.update({
                        "mapImageUrl": nav_data.get('mapImageUrl', ''),
                        "pin": nav_data.get('pin', navigation['pin']),
                        "qrCodeUrl": nav_data.get('qrCodeUrl', ''),
                        "clientGeoId": nav_data.get('clientGeoId', '')
                    })
                
                # Format data according to the simplified structure
                formatted_data = {
                    "docId": document.publicId,
                    "title": store_name,
                    "thumbnailUrl": thumbnail_url,
                    "images": images,
                    "navigation": navigation
                }
                
                # Add to array
                relevant_data.append(formatted_data)
                logger.info(f"Added relevant data for doc-id: {doc_id} - {store_name}")
            else:
                logger.warning(f"Doc-id {doc_id} not found in KM search results")
        
        return {"items": relevant_data}
        
    except Exception as e:
        logger.error(f"Error extracting relevant KM data: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {}
