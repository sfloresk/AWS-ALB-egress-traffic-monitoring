"""
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
import json
import os
import boto3
 
print('Loading function')

# Define global variables
LB_NAME=os.getenv("ALB_NAME")
TABLE_NAME=os.getenv("EVENTS_TABLE")

dynamo = boto3.resource('dynamodb')
table = dynamo.Table(TABLE_NAME)
table.load()

def lambda_handler(event, context):
    print("Received event: " + json.dumps(event))
    event_time = event['detail']['eventTime']
    # Check for errors in the event and ignore those with them
    if "errorCode" not in event["detail"].keys():
        if event["detail"]["eventName"] == "CreateNetworkInterface":
            # ALB creates interfaces with descriptions that include its name
            # This is how the function filter events for a given load balancer
            if LB_NAME in event["detail"]["requestParameters"]["description"]:
                interface_id = event["detail"]["responseElements"]["networkInterface"]["networkInterfaceId"]
                print(f'New interface attached to {LB_NAME}: {interface_id}')
                print(f'Inserting item in DynamoDB')
                table.put_item(
                    Item={
                        'interface_id': interface_id,
                        'created_time': event_time,
                        'load_balancer': LB_NAME})
        elif event["detail"]["eventName"] == "DeleteNetworkInterface":
            # The delete event does not include the description so dynamodb needs to be query first
            interface_id = event["detail"]["requestParameters"]["networkInterfaceId"]
            print(f'Interface removed: {interface_id}')
            interface_ddb = table.get_item(Key={"interface_id":interface_id})
            if "load_balancer" in interface_ddb["Item"].keys():
                print(f'Updating interface {interface_id} in dynamoDB for load balancer {interface_ddb["Item"]["load_balancer"]}')
                table.update_item(
                    Key={"interface_id":interface_id},
                    UpdateExpression="set delete_time=:t",
                    ExpressionAttributeValues={
                        ':t': event_time})
            else:
                print(f"Interface {interface_id} does not have an associated load balancer in DynamoDB - ignoring...")
    else:
        print(f"Interface {interface_id} event intercepted but has an error code - ignoring...")
    return "Interface event handler finished"