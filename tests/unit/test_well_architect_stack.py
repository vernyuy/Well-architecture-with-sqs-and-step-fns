import aws_cdk as core
import aws_cdk.assertions as assertions

from well_architect.well_architect_stack import WellArchitectStack

# example tests. To run these tests, uncomment this file along with the example
# resource in well_architect/well_architect_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = WellArchitectStack(app, "well-architect")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
