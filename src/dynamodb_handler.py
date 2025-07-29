"""
DynamoDB Handler Module
Handles all DynamoDB operations with proper error handling and connection management
"""

import logging
import boto3
from typing import Dict, Any, Optional, List
from botocore.exceptions import ClientError, NoCredentialsError
from .app_config import config as app_config

logger = logging.getLogger(__name__)

class DynamoDBHandler:
    """
    DynamoDB Handler for managing connections and operations
    """
    
    def __init__(self, table_name: str = None, region_name: str = None):
        """
        Initialize the DynamoDB handler
        
        Args:
            table_name: Name of the DynamoDB table
            region_name: AWS region where the DynamoDB table is located
        """
        self.table_name = table_name or app_config.DYNAMODB_TABLE_NAME
        self.region_name = region_name or app_config.DYNAMODB_REGION
        self._dynamodb = None
        self._table = None
    
    def _get_dynamodb_table(self):
        """Initialize DynamoDB connection if not already done"""
        if self._table is None:
            try:
                # Use AWS credentials from app config if available
                if app_config.AWS_ACCESS_KEY_ID and app_config.AWS_SECRET_ACCESS_KEY:
                    self._dynamodb = boto3.resource(
                        'dynamodb',
                        region_name=self.region_name,
                        aws_access_key_id=app_config.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=app_config.AWS_SECRET_ACCESS_KEY
                    )
                    logger.info(f"Using configured AWS credentials from app config")
                else:
                    # Fall back to default credentials (IAM role, AWS CLI, etc.)
                    self._dynamodb = boto3.resource('dynamodb', region_name=self.region_name)
                    logger.info(f"Using default AWS credentials")
                
                self._table = self._dynamodb.Table(self.table_name)
                logger.info(f"Connected to DynamoDB table: {self.table_name} in region: {self.region_name}")
            except NoCredentialsError:
                logger.error("AWS credentials not found. Please configure AWS credentials.")
                raise
            except Exception as e:
                logger.error(f"Failed to connect to DynamoDB: {str(e)}")
                raise
        return self._table
    
    async def get_item(self, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get an item from DynamoDB table
        
        Args:
            key: The key to query for (e.g., {'configId': 'some-id'})
            
        Returns:
            Item data if found, None if not found
            
        Raises:
            ClientError: If there's an error accessing DynamoDB
        """
        try:
            table = self._get_dynamodb_table()
            
            response = table.get_item(Key=key)
            
            if 'Item' not in response:
                logger.warning(f"No item found for key: {key}")
                return None
            
            item = response['Item']
            logger.debug(f"Found item for key: {key}")
            return item
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"DynamoDB error ({error_code}): {error_message}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting item: {str(e)}")
            raise
    
    async def put_item(self, item: Dict[str, Any]) -> bool:
        """
        Put an item into DynamoDB table
        
        Args:
            item: The item data to store
            
        Returns:
            True if successful
            
        Raises:
            ClientError: If there's an error accessing DynamoDB
        """
        try:
            table = self._get_dynamodb_table()
            
            table.put_item(Item=item)
            logger.debug(f"Successfully put item")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"DynamoDB error ({error_code}): {error_message}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error putting item: {str(e)}")
            raise
    
    async def update_item(self, key: Dict[str, Any], update_expression: str, 
                          expression_attribute_values: Dict[str, Any] = None,
                          expression_attribute_names: Dict[str, str] = None) -> bool:
        """
        Update an item in DynamoDB table
        
        Args:
            key: The key of the item to update
            update_expression: The update expression
            expression_attribute_values: Values for the update expression
            expression_attribute_names: Names for the update expression
            
        Returns:
            True if successful
            
        Raises:
            ClientError: If there's an error accessing DynamoDB
        """
        try:
            table = self._get_dynamodb_table()
            
            update_kwargs = {
                'Key': key,
                'UpdateExpression': update_expression
            }
            
            if expression_attribute_values:
                update_kwargs['ExpressionAttributeValues'] = expression_attribute_values
            
            if expression_attribute_names:
                update_kwargs['ExpressionAttributeNames'] = expression_attribute_names
            
            table.update_item(**update_kwargs)
            logger.debug(f"Successfully updated item with key: {key}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"DynamoDB error ({error_code}): {error_message}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating item: {str(e)}")
            raise
    
    async def delete_item(self, key: Dict[str, Any]) -> bool:
        """
        Delete an item from DynamoDB table
        
        Args:
            key: The key of the item to delete
            
        Returns:
            True if successful
            
        Raises:
            ClientError: If there's an error accessing DynamoDB
        """
        try:
            table = self._get_dynamodb_table()
            
            table.delete_item(Key=key)
            logger.debug(f"Successfully deleted item with key: {key}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"DynamoDB error ({error_code}): {error_message}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error deleting item: {str(e)}")
            raise
    
    async def query(self, key_condition_expression: str, 
                    expression_attribute_values: Dict[str, Any] = None,
                    expression_attribute_names: Dict[str, str] = None,
                    index_name: str = None) -> List[Dict[str, Any]]:
        """
        Query items from DynamoDB table
        
        Args:
            key_condition_expression: The key condition expression
            expression_attribute_values: Values for the expression
            expression_attribute_names: Names for the expression
            index_name: Name of the index to query (optional)
            
        Returns:
            List of items found
            
        Raises:
            ClientError: If there's an error accessing DynamoDB
        """
        try:
            table = self._get_dynamodb_table()
            
            query_kwargs = {
                'KeyConditionExpression': key_condition_expression
            }
            
            if expression_attribute_values:
                query_kwargs['ExpressionAttributeValues'] = expression_attribute_values
            
            if expression_attribute_names:
                query_kwargs['ExpressionAttributeNames'] = expression_attribute_names
            
            if index_name:
                query_kwargs['IndexName'] = index_name
            
            response = table.query(**query_kwargs)
            items = response.get('Items', [])
            logger.debug(f"Query returned {len(items)} items")
            return items
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"DynamoDB error ({error_code}): {error_message}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error querying items: {str(e)}")
            raise
    
    async def scan(self, filter_expression: str = None,
                   expression_attribute_values: Dict[str, Any] = None,
                   expression_attribute_names: Dict[str, str] = None) -> List[Dict[str, Any]]:
        """
        Scan items from DynamoDB table
        
        Args:
            filter_expression: The filter expression (optional)
            expression_attribute_values: Values for the expression
            expression_attribute_names: Names for the expression
            
        Returns:
            List of items found
            
        Raises:
            ClientError: If there's an error accessing DynamoDB
        """
        try:
            table = self._get_dynamodb_table()
            
            scan_kwargs = {}
            
            if filter_expression:
                scan_kwargs['FilterExpression'] = filter_expression
            
            if expression_attribute_values:
                scan_kwargs['ExpressionAttributeValues'] = expression_attribute_values
            
            if expression_attribute_names:
                scan_kwargs['ExpressionAttributeNames'] = expression_attribute_names
            
            response = table.scan(**scan_kwargs)
            items = response.get('Items', [])
            logger.debug(f"Scan returned {len(items)} items")
            return items
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"DynamoDB error ({error_code}): {error_message}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error scanning items: {str(e)}")
            raise
