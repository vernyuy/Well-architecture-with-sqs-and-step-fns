
import boto3
import json
import os
import uuid
from aws_lambda_powertools.utilities.parser import event_parser, BaseModel
from aws_lambda_powertools.utilities.typing import LambdaContext
from typing import List, Optional
from aws_lambda_powertools import Logger
import time


table_name = os.environ.get("TABLE_NAME")
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(table_name)
logger = Logger()

class Warehouse(BaseModel):
    warehouseName: int
    warehouseDescription: str
    
    
def lambda_handler(event, context: LambdaContext):
    
    #Extract body data from the event
    body = Warehouse.parse_obj(json.loads(event['body']))
    logger.info(body)
    current_time = int(round(time.time() * 1000))
    warehouse_id = str(uuid.uuid4())
    logger.info(warehouse_id)
    warehouse_item = {
        "SK": "WAREHOUSE",
        "PK": "WAREHOUSE#"+warehouse_id,
        "warehouseName":body.warehouseName,
        "warehouseDescription":body.warehouseDescription,
        "id": warehouse_id,
        "createdOn": current_time
    }
    table.put_item(
        Item=warehouse_item,
    )
    logger.info(warehouse_item)
    return {
        'statusCode': 200,
        'body': json.dumps({
            'meesage': 'warehouse successfully created!'
        })
    }
