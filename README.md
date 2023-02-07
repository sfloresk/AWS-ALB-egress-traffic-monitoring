# AWS Application Load Balancer - Egress traffic monitoring and correlation with cost & usage reports

## Solution overview

Serverless application to monitor ENI changes associated to a given application load balancer. This information can be used to retrieve egress traffic to the internet using flow logs and compare the bytes with the charges populated in cost and usage reports.

> These instructions assume us-east-1 as region but that is not mandatory

## Solution architecture

For new interfaces, the solution will detect them using a subscription of events triggered by cloudtrail

![Screenshot](docs/detection-new-interfaces.png?raw=true "Detection of new interfaces")

For existing interfaces attached to a ALB, there is a different lambda function that can be invoked to discover them

![Screenshot](docs/discover-existing-interfaces.png?raw=true "Discover existing interfaces")

## Pre-requisites

1. Active AWS account
2. Cost and usage report:
     * **Enable report data integration for Amazon Athena**
     * There is no need to enable additional report details or include resource IDs
     * For example:

    ![Screenshot](docs/cur-settings-example.png?raw=true "Cost and usage report - Example settings")

     * Detailed steps can be found in the documentation: https://docs.aws.amazon.com/cur/latest/userguide/cur-create.html 

## App set-up

1. Navigate to Cloud9 Console
2. Create a new environment with default settings 
3. (Optional) Attach an admin role to the environment EC2 instance if you would like to use a role instead of your credentials - **Attaching an admin role is not recommended for production deployments, for a detailed list of actions that this deployment does, refer to the template.yaml file and the following sections**
4. Open the Cloud9 development environment
5. (Optional) Disable temporary credentials and remove $HOME/.aws directory to make sure SAM uses your instance profile credentials if you prefer to use a role
6. Clone this repo
7. **Navigate to the project folder and edit the template.yaml file - Modify line 15 with your load balancer's name (The value Test751 is used as example)**
8. Create a bucket, build and deploy:

    ```bash
    cd  AWS-ALB-egress-traffic-monitoring
    BUCKET_NAME=alb-interface-monitoring-sam-$(tr -dc a-z0-9 </dev/urandom | head -c 13 ; echo '')
    aws s3 mb s3://$BUCKET_NAME
    sam build
    sam deploy --stack-name AblInterfaceMonitoringStack --region us-east-1  --s3-bucket $BUCKET_NAME --capabilities CAPABILITY_IAM

    ```

9. If the ALB has been created before this deployment, execute a local invoke of the discover ENIs lambda function - this will populate the DynamoDB table with the current ALB's interfaces:

    ```bash
    sam local invoke AlbDiscoverEnis 
    ```

## VPC Flow Logs

In order to find the egress traffic for the discovered interfaces, VPC flow logs need to be enable for the subnets configured in the ALB. In the cloud9 terminal, follow these steps:

1. Create a bucket to store the VPC flow logs
```bash
VPC_FLOW_LOGS_BUCKET_NAME=alb-interface-monitoring-vpc-flow-logs-$(tr -dc a-z0-9 </dev/urandom | head -c 13 ; echo '')
aws s3 mb s3://$VPC_FLOW_LOGS_BUCKET_NAME
cat > /tmp/alb-interface-monitoring-lifecycle-policy.json << EOF
{
"Rules": [
    {
        "Status": "Enabled", 
        "Prefix": "",
        "Expiration": {
            "Days": 14
        }, 
        "ID": "Delete after 14 days"
    }
    ]
}
EOF
aws s3api put-bucket-lifecycle --bucket $VPC_FLOW_LOGS_BUCKET_NAME --lifecycle-configuration file:///tmp/alb-interface-monitoring-lifecycle-policy.json

```

2. Create the flow logs 

    **In the first line below, replace Test751 for your load balancer's name**
    ```bash
    ALB_NAME=Test751
    sudo yum install -y jq
    VPC_FLOW_FORMAT='${account-id} ${action} ${az-id} ${bytes} ${dstaddr} ${dstport} ${end} ${flow-direction} ${instance-id} ${interface-id} ${log-status} ${packets} ${pkt-dst-aws-service} ${pkt-dstaddr} ${pkt-src-aws-service} ${pkt-srcaddr} ${protocol} ${region} ${srcaddr} ${srcport} ${start} ${sublocation-id} ${sublocation-type} ${subnet-id} ${tcp-flags} ${traffic-path} ${type} ${version} ${vpc-id}'
    ALB_SUBNETS=$(aws elbv2 describe-load-balancers --names $ALB_NAME | jq .LoadBalancers[].AvailabilityZones[].SubnetId | tr '"' ' ') 
    FLOW_LOG_RESULT=$(aws ec2 create-flow-logs --resource-type Subnet --resource-ids $ALB_SUBNETS --traffic-type ALL --log-destination-type s3 --log-destination arn:aws:s3:::$VPC_FLOW_LOGS_BUCKET_NAME --max-aggregation-interval 60 --log-format "$VPC_FLOW_FORMAT")
    echo $FLOW_LOG_RESULT
    ```
    Make sure that the "Unsuccessful" list does not have any elements. You can verify the flows in the console, selecting a subnet under "VPC" -> "Subnets" and clicking on "Flow Logs"

# Athena tables, partitions and queries for VPC flow logs

1. An Athena table and partitions is required to be able to execute queries against flow logs. In the console, navigate to Athena -> Query Editor. If you haven't used Athena before, you will need to select a bucket for the query results - **Do not select the ones for VPC flow logs or Cost and usage reports** 

2. Copy the content of athena/VPCFlowLogsCreateTableV5.sql in the editor - before you execute the query, there are some modifications needed to make sure it works for your environment:

    a. In line 35, change the string YOUR BUCKET for the VPC flow logs bucket name and YOUR_ACCOUNT_NUMBER for your account id. You can get these values with the following commands when executed in the cloud9 terminal:
    
    ```bash
    echo VPC Flow logs bucket name: $VPC_FLOW_LOGS_BUCKET_NAME
    echo Account Number: $(aws sts get-caller-identity | jq .Account | tr '"' ' ')
    ```

    > If you are using another region than us-east-1, you will need to change that too in the same line

3. Run the query - a new table should be created

4. Create a partition (**You need to repeat this step for each date that you are planning to use in your queries**)

    In the query editor, copy the content of athena/VPCCreateDatePartition.sql - before you execute the query, there are some modifications needed to make sure it works for your environment:

    a. In line 2, change the string YEAR-MONTH-DAY for the date you want to explore the flow logs (do not remove the single quotes). For example, '2023-01-31' is a valid value.

    b. In line 3, change the string "YOUR BUCKET" for the VPC flow logs bucket name and YOUR_ACCOUNT_NUMBER for your account id. You can get these values with the following commands:

    ```bash
    echo VPC Flow logs bucket name: $VPC_FLOW_LOGS_BUCKET_NAME
    echo Account Number: $(aws sts get-caller-identity | jq .Account | tr '"' ' ')
    ```
    c. In line 3, change YEAR/MONTH/DAY for the same value used in line 2. For example 2023/01/31 is a valid value

    > If you are using another region than us-east-1, you will need to change that too in the same line

5. Execute a test query:
    ```sql
    SELECT *
    FROM "alb-interface-monitoring-vpc-flow-logs"
    LIMIT 1
    ```

6. Get the load balancer's ENIs egress traffic. For example:
    ```sql
    SELECT sum(bytes)/1024.0/1024.0/1024.0 as "GB Egress via IGW"
    FROM "alb-interface-monitoring-vpc-flow-logs" 
    where interface_id IN ('eni-0286b85fcf79e3320','eni-02d0c0d5c268dacf4','eni-0122206c98dcf72e4','eni-02d3ad2e138be4a41')
    and flow_direction like 'egress'
    and (traffic_path=8 or traffic_path=2)
    and date = DATE('2023-01-31') 
    ```
    
    The above query will return the GB of the traffic that went through an internet gateway from the ALB's interfaces on January 31st 2023. There are changes required to make this query work correctly in your environment:

    a. Modify the interface_id statement to include your load balancer's interfaces for the desired date. This information is stored in the DynamoDB table created during the App Setup section, and there is a lambda function that can be invoked to automatically retrieve the ALB assigned interfaces in a given date:
    
    * In your cloud9 environment, open the file functions -> alb_get_interfaces -> alb_get_interfaces.py and change the date in line 26 with the date you would like to execute the queries with. For example, 2023-01-31 is a valid value.
    * Build and execute a local invoke of the function:

            ```bash
            sam build
            sam local invoke AlbRetrieveEnis
            ```

    * The result should look like this:

            ```bash
            Invoking get_alb_interfaces.lambda_handler (python3.7)
            (...)
            Using table ALBInterfacesUpdates and ALB Test751
            eni-02d3ad2e138be4a41
            eni-0286b85fcf79e3320
            eni-02d0c0d5c268dacf4
            eni-0122206c98dcf72e4
            "Interface retrieval finished"
            (...)
            ```

    b. Modify the date statement with the value that you would like Athena to run the query with. This should be the same date as the one used to find the interfaces in DynamoDB
    
    > More information of each field in the VPC flow log can be found in this link: https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html#flow-logs-fields

    Make a note of the result, it will be compared against the cost and usage report in the following section.


## Usage and cost report

So far, we have created an application that keeps track of the interfaces of a given application load balancer and save those in a DynamoDB table, we created flow logs and an athena table to retrieve the bytes leaving those interface to the internet. Now, we are going to correlate that information with the cost and usage report:

> The setup of a cost and usage report is a pre-requisite for this to work. Once setup, it can take up to 24 hours to start delivering information to S3

1. Navigate to Athena and create the table and partitions for the report following this guide: https://docs.aws.amazon.com/cur/latest/userguide/cur-ate-manual.html 

2. Create a new query to find the egress GBs measured for the load balancer:
    ```sql
    select line_item_resource_id, pricing_unit, sum(line_item_usage_amount)  as usage_amount
    from detailed_cost_report 
    where line_item_product_code like 'AWSELB' 
    and line_item_usage_type like 'DataTransfer-Out-Bytes' 
    and line_item_usage_start_date between TIMESTAMP '2023-01-31 00:00:00' 
    and TIMESTAMP '2023-01-31 23:59:59'
    and line_item_resource_id like 'arn:aws:elasticloadbalancing:us-east-1:1111111111:loadbalancer/app/Test751/1111111111'
    group by line_item_resource_id, pricing_unit
    ```
    
    This query aggregates the usage amount (in GB) for egress traffic for the entire day specified (January 31st 2023) for a given ARN. For this query to work in your environment, make the following changes:

    a. In line 3, replace "detailed_cost_report" for the name of your table
    
    b. In line 7, replace the ARN for the one belonging to your ALB

    c. In line 5 and 6, modify the dates for the time range you would like to use. This should be the same time range used to query egress traffic from the ALB's ENIs in the previous section

    The result should be equal, or very similar, to the value returned by the VPC logs query mentioned in the previous section

## App tear-down

> These instructions assume us-east-1 as region, the same region used for set-up should be used in the following commands

1. Open cloud9 dev environment
2. Navigate to the project folder and delete the cloud formation stack

    ```bash
    aws cloudformation delete-stack --stack-name AblInterfaceMonitoringStack --region us-east-1
    ```
3. Optional, you can monitor the delete operation:

    ```bash
    aws cloudformation wait stack-delete-complete --stack-name AblInterfaceMonitoringStack --region us-east-1
    ``` 

## Flow logs, athena table and S3 bucket tear down

1. Delete the Athena table:
    ```sql
    DROP TABLE `alb-interface-monitoring-vpc-flow-logs`;
    ```
2. Delete flow logs
    ```bash
    aws ec2 delete-flow-logs --flow-log-ids $(echo $FLOW_LOG_RESULT |  jq .FlowLogIds[] | tr '"' ' ') 
    ```
3. Delete VPC Flow log bucket
    ```bash
    aws s3 rm s3://$VPC_FLOW_LOGS_BUCKET_NAME --recursive
    aws s3api delete-bucket --bucket $VPC_FLOW_LOGS_BUCKET_NAME --region us-east-1
    ```