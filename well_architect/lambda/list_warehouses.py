
import boto3
import json
import os
from aws_lambda_powertools.utilities.parser import event_parser, BaseModel
from aws_lambda_powertools.utilities.typing import LambdaContext
from typing import List, Optional
from aws_lambda_powertools import Logger

table_name = os.environ.get("TABLE_NAME")
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(table_name)
logger = Logger()
  
table_name = os.environ.get("TABLE_NAME")
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(table_name)

def lambda_handler(event, context):
    print(event)
    response = table.query(
        KeyConditionExpression="PK = :pk and begins_with(SK, :sk)",
        ExpressionAttributeValues={
            ":pk": "WAREHOUSE",
            ":sk": "WAREHOUSE#"
        }
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps(response['Items'])
    }
