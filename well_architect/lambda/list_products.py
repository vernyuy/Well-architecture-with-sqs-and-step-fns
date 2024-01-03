
import boto3
import json
import os
from aws_lambda_powertools import Logger

table_name = os.environ.get("TABLE_NAME")
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(table_name)
logger = Logger()
    
def lambda_handler(event, context):
    print(event)
    response = table.query(
        IndexName="product-index",
        KeyConditionExpression="GSI1_PK = :pk and begins_with(GSI1_SK, :sk)",
        ExpressionAttributeValues={
            ":pk": "PRODUCT",
            ":sk": "PRODUCT#"
        }
    )
    # result: Products = response["Items"]
    
    logger.info(response['Items'])
    
    return {
        'statusCode': 200,
        'body': json.dumps(response['Items'])
    }
