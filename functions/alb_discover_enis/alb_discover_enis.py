"""
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
import json
import boto3
import os
 
# Define global variables
ec2 = boto3.client('ec2')
LB_NAME=os.getenv("ALB_NAME")
TABLE_NAME=os.getenv("EVENTS_TABLE")
dynamo = boto3.resource('dynamodb')
print(f"Using table {TABLE_NAME} and ALB {LB_NAME}")
table = dynamo.Table(TABLE_NAME)
table.load()

def lambda_handler(event, context):
    # Query all interfaces
    interfaces = ec2.describe_network_interfaces()
    for eni in interfaces["NetworkInterfaces"]:
        interface_id = eni["NetworkInterfaceId"]
        # ALB creates interfaces with descriptions that include its name
        # This is how the function ENIs for a given load balancer
        if LB_NAME in eni["Description"]:
            interface_ddb = table.get_item(Key={"interface_id":interface_id})
            print(f'Found ENI {eni["NetworkInterfaceId"]} for ALB {LB_NAME}')
            # Only insert item if it is not present
            if "Item" not in interface_ddb.keys() or "load_balancer" not in interface_ddb["Item"].keys():
                print(f'Inserting item in DynamoDB')
                attachment_time = eni["Attachment"]["AttachTime"].strftime('%Y-%m-%dT%H:%M:%SZ')
                table.put_item(
                    Item={
                        'interface_id': interface_id,
                        'created_time': attachment_time,
                        'load_balancer': LB_NAME})
            else:
                print(f'ENI {eni["NetworkInterfaceId"]} already in dynamoDB table - ignoring...')
    return "Interface discovery finished"