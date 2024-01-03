
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

class Product(BaseModel):
    productPrice: int
    productDescription: str
    productQuantity: int
    warehouseId: str
    productName: str
    productImage: str
    
    
def lambda_handler(event, context: LambdaContext):
    
    #Extract body data from the event
    body = Product.parse_obj(json.loads(event['body']))
    logger.info(body)
    current_time = int(round(time.time() * 1000))
    product_id = str(uuid.uuid4())
    logger.info(product_id)
    product_item = {
        "SK": "PRODUCT#"+product_id,
        "PK": "WAREHOUSE#"+body.warehouseId,
        "productName":body.productName,
        "productImage":body.productImage,
        "id": product_id,
        "productPrice":body.productPrice,
        "productQuantity":body.productQuantity,
        "productDescription":body.productDescription,
        "warehouseId":body.warehouseId,
        "createdOn": current_time,
        "GSI1_PK": "PRODUCT",
        "GSI1_SK": "PRODUCT#"+product_id,
    }
    table.put_item(
        Item=product_item,
    )
    logger.info(product_item)
    return {
        'statusCode': 200,
        'body': json.dumps({
            'meesage': 'product successfully created!'
        })
    }
