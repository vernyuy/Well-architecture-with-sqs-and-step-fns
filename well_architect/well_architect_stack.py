#CSV > S3 > Lambda > SQS > Lambda > DynamoDb

from aws_cdk import (
    CfnOutput,
    Duration,
    Stack,
    aws_stepfunctions as sfn,
    RemovalPolicy,
    aws_sqs as sqs,
    aws_s3 as s3,
    aws_s3_notifications as s3_notifications,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_sns as sns,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cloudwatch_actions,
    aws_dynamodb as dynamodb,
    Tags,
    aws_logs as logs,
    aws_pipes as pipes,
    aws_apigateway as _apigw
)
from constructs import Construct
from aws_cdk.aws_lambda import Function, Tracing

class WellArchitectStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create a role for the Lambda function
        role = iam.Role(
            self, "InventoryFunctionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            role_name="InventoryFunctionRole",
            description="Role for Lambda functions"
        )

        Tags.of(role).add("department", "inventory")

        # Allow the Lambda function to write to CloudWatch Logs
        role.add_to_policy(iam.PolicyStatement(
            actions=["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
            resources=["arn:aws:logs:*:*:*"]
        ))

        # Create the Dead Letter Queue (DLQ)
        dlq = sqs.Queue(self, 'InventoryUpdatesDlq',
            visibility_timeout=Duration.seconds(300)
        )

        Tags.of(dlq).add("department", "inventory")

        # Create the SQS queue with DLQ setting
        queue = sqs.Queue(
            self, "InventoryUpdatesQueue",
            visibility_timeout=Duration.seconds(300),
            encryption=sqs.QueueEncryption.KMS_MANAGED,
            removal_policy=RemovalPolicy.DESTROY,
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=2,  # Number of retries before sending the message to the DLQ
                queue=dlq
            )
        )

        # Create an SQS queue policy to allow source queue to send messages to the DLQ
        policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["sqs:SendMessage"],
            resources=[dlq.queue_arn],
            conditions={"ArnEquals": {"aws:SourceArn": queue.queue_arn}},
        )
        queue.queue_policy = iam.PolicyDocument(statements=[policy])

        Tags.of(queue).add("department", "inventory")

        # Allow the Lambda function to receive messages from the SQS queue
        # role.add_to_policy(iam.PolicyStatement(
        #     actions=["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"],
        #     resources=[queue.queue_arn]
        # ))

        # Create the DynamoDB table
        table = dynamodb.Table(self, 'InventoryUpdates',
                               table_name="well-arch-table",
            partition_key=dynamodb.Attribute(name='id', type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        Tags.of(table).add("department", "inventory")

        #create input S3 bucket
        bucket = s3.Bucket(self, "InventoryUpdatesBucket", 
            bucket_name="inventoryupdatesbucket",
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
        )
        bucket_arn = bucket.bucket_arn

        Tags.of(bucket).add("department", "inventory")

        # Create rest api

        file_api = _apigw.RestApi(self, "FileApi", 
            rest_api_name="File API",
            description="This service serves files."
        )

        bucket_resource = file_api.root.add_resource("{bucketName}")
        item_resource = bucket_resource.add_resource("{item}")

        policy = {
          "s3write": iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(actions=["s3:PutObject"], effect=iam.Effect.ALLOW, resources=["*"])
              ]
            )
        }
        api_role = iam.Role(self, "APIGRole", assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com"), inline_policies=policy)


        integration_response = _apigw.IntegrationResponse(status_code="200")
        integration_options = _apigw.IntegrationOptions(
          request_parameters={
            "integration.request.path.bucket":"method.request.path.bucketName",
            "integration.request.path.object":"method.request.path.item"
          }, 
          credentials_role=api_role, 
          integration_responses=[integration_response]
        ) 
              
        bucket_integration = _apigw.AwsIntegration(service="s3", integration_http_method="PUT", path="{bucket}/{object}", region="eu-west-2", options=integration_options)

        post_to_bucket_method = item_resource.add_method("PUT", integration=bucket_integration, 
          request_parameters={
            "method.request.path.bucketName": True,
            "method.request.path.item": True
          },
          method_responses=[_apigw.MethodResponse(status_code="200")]
        )    

        
        # Create pre-processing Lambda function
        csv_processing_to_sqs_function  = _lambda.Function(self, 'CSVProcessingToSQSFunction',
                                   runtime=_lambda.Runtime.PYTHON_3_8,
                                   code=_lambda.Code.from_asset('well_architect/lambda'),
                                   handler='csv_processing_to_sqs_function.lambda_handler',
                                   role=role,
                                   tracing=Tracing.ACTIVE,
                                   timeout=Duration.seconds(300),
                                   memory_size=1024,
                                   environment={
                                       'QUEUE_URL': queue.queue_url,
                                   }
                                )

        # Add tags to the Lambda function
        Tags.of(csv_processing_to_sqs_function ).add("department", "inventory")

        # Grant the Lambda function read permissions to the S3 bucket
        bucket.grant_read(csv_processing_to_sqs_function )

        # Configure the bucket notification to invoke the Lambda function for all object creations
        notification = s3_notifications.LambdaDestination(csv_processing_to_sqs_function )
        bucket.add_event_notification(s3.EventType.OBJECT_CREATED, notification)


        # Create an SQS queue policy to allow source queue to send messages to the DLQ
        policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["sqs:SendMessage"],
            resources=[dlq.queue_arn],
            conditions={
                "ArnEquals": {
                    "aws:SourceArn": queue.queue_arn
                }
            }
        )
        queue.queue_policy = iam.PolicyDocument(statements=[policy])

        # Create an SNS topic for alarms
        topic = sns.Topic(self, 'InventoryUpdatesTopic')

        Tags.of(topic).add("department", "inventory")

        # Create a CloudWatch alarm for ApproximateAgeOfOldestMessage metric
        alarm = cloudwatch.Alarm(self, 'OldInventoryUpdatesAlarm',
            alarm_name='OldInventoryUpdatesAlarm',
            metric=queue.metric_approximate_age_of_oldest_message(),
            threshold=600,  # Specify your desired threshold value in seconds
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD
        )
        alarm.add_alarm_action(cloudwatch_actions.SnsAction(topic))

        Tags.of(alarm).add("department", "inventory")

        # Define the queue policy to allow messages from the Lambda function's role only
        policy = iam.PolicyStatement(
            actions=['sqs:SendMessage'],
            effect=iam.Effect.ALLOW,
            principals=[iam.ArnPrincipal(role.role_arn)],
            resources=[queue.queue_arn]
        )

        queue.add_to_resource_policy(policy)

        # Create an IAM policy statement allowing only HTTPS access to the queue
        secure_transport_policy = iam.PolicyStatement(
            effect=iam.Effect.DENY,
            actions=["sqs:*"],
            resources=[queue.queue_arn],
            conditions={
                "Bool": {
                    "aws:SecureTransport": "false",
                },
            },
        )
        
        sfn_target = sfn.StateMachine(self, "state-machine",
            definition_body=sfn.DefinitionBody.from_file("./stepfn.asl.json"),
            state_machine_type = sfn.StateMachineType.EXPRESS,
            state_machine_name = "InventoryStateMachine",
            logs = sfn.LogOptions(
                destination=logs.LogGroup(self, "state-machine-logs"),
                level=sfn.LogLevel.ALL,
                include_execution_data=True
            )
        )    

        Tags.of(sfn_target).add("department", "inventory")

        table.grant_write_data(sfn_target)
        # creating pipe
        source_policy = iam.PolicyStatement(
                actions=['sqs:ReceiveMessage', 'sqs:DeleteMessage', 'sqs:GetQueueAttributes'],
                resources=[queue.queue_arn],
                effect=iam.Effect.ALLOW,
        )
              
        target_policy = iam.PolicyStatement(
                actions=['states:StartExecution'],
                resources=[sfn_target.state_machine_arn],
                effect=iam.Effect.ALLOW,
        )
        pipe_role = iam.Role(self, 'pipe-role',
            assumed_by=iam.ServicePrincipal('pipes.amazonaws.com'),
        )

        pipe_role.add_to_policy(source_policy)
        pipe_role.add_to_policy(target_policy)
        
    # Polls messages from sqs
        cfn_pipe = pipes.CfnPipe(self, "InventoryUpdateCfnPipe",
            role_arn=pipe_role.role_arn,
            source=queue.queue_arn,
            target=sfn_target.state_machine_arn,
            source_parameters=pipes.CfnPipe.PipeSourceParametersProperty(
                sqs_queue_parameters=pipes.CfnPipe.PipeSourceSqsQueueParametersProperty(
                    batch_size=10
                )
            ),
            target_parameters=pipes.CfnPipe.PipeTargetParametersProperty(
                step_function_state_machine_parameters=pipes.CfnPipe.PipeTargetStateMachineParametersProperty(
                    invocation_type="FIRE_AND_FORGET"
                )
            )
        )

        Tags.of(cfn_pipe).add("department", "inventory")
        #Output
        CfnOutput(self, "S3 Bucket Name", value=bucket.bucket_name)
