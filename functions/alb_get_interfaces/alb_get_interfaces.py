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
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime

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
    date = "2023-01-31"
    date_format='%Y-%m-%dT%H:%M:%SZ'
    from_datetime = datetime.strptime(f'{date}T00:00:00Z', date_format)
    to_datetime = datetime.strptime(f'{date}T23:59:59Z', date_format)
    #2023-01-30T21:57:37Z
    response = table.scan(
        FilterExpression=Attr("load_balancer").eq(LB_NAME)
    )

    interfaces = []
    for item in response['Items']:
        created_datetime=datetime.strptime(item['created_time'], date_format)
        
        if created_datetime >= from_datetime and created_datetime <= to_datetime:
            # Interface was created after the from date but before the to date
            interfaces.append(item)
            continue
        if 'delete_time' not in item.keys():
            if created_datetime <= to_datetime:
                # Interface was created before or between the reference date and never deleted
                interfaces.append(item)
                continue
        else:
            deleted_time=datetime.strptime(item['delete_time'], date_format)
            if deleted_time >= from_datetime and deleted_time <= to_datetime:
                # Interface deleted in between from and to dates
                interfaces.append(item)
                continue
            if created_datetime <= from_datetime and deleted_time >= to_datetime:
                # Interface existed between from and to dates
                interfaces.append(item)
                continue
    if len(interfaces)==0:
        return f"No interfaces found active on {date} for load balancer {LB_NAME}"        
    else: 
        for interface in interfaces:
            print(interface['interface_id'])
    return "Interface retrieval finished"
    

