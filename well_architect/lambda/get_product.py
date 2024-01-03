
import boto3
import json
import os

table_name = os.environ.get("TABLE_NAME")
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(table_name)

def lambda_handler(event, context):
    print(event)
    response = table.get_item(
        IndexName="product-index",
        Key={
            "GSI1_SK": "PRODUCT#"+event['pathParameters']['product'],
            "GSI1_PK": "PRODUCT"
        }
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps(response['Item'])
    }
