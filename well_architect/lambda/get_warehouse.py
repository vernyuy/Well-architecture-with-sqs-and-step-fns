
import boto3
import json
import os
import aws_lambda_powertools
from aws_lambda_powertools.utilities.parser import event_parser, BaseModel
from aws_lambda_powertools.utilities.typing import LambdaContext
from typing import List, Optional
from aws_lambda_powertools import Logger
logger = Logger()
table_name = os.environ.get("TABLE_NAME")
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(table_name)
class Warehouse(BaseModel):
    id: str
    warehouseName: str
    warehouseDescription: str
    
def lambda_handler(event, context):
    print(event)
    response = table.get_item(
        Key={
            "SK": "WAREHOUSE#"+event['pathParameters']['warehouse_id'],
            "PK": "WAREHOUSE"
        }
    )
    print(response)
    logger.info(response)
    
    result = Warehouse.parse_obj(response['Item'])
    print(result)
    return {
        'statusCode': 200,
        'body': json.dumps({
            "id": result.id,
            "warehouseName": result.warehouseName,
            "warehouseDescription": result.warehouseDescription,
        })
    }
