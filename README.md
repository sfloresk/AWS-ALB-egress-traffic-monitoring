# Application Load Balancer Interface Monitoring

Serverless application to monitor ENI changes associated to a given application load balancer. The application uses 
EventBridge to intercept CreateNetworkInterface and DeleteNetworkInterface events via lambda and stores the interface ID, load balancer name and a timestamp 
in a dynamodb table. This table can be used to build Athena queries on flow logs associated to these interfaces

## Pre-requisites

1. Active AWS account

## Environment set-up

> These instructions assume us-east-1 as region but that is not mandatory

1. Navigate to Cloud9 Console
2. Create a new environment with default settings 
3. Attach an admin role to the environment EC2 instance (note that this is not recommended for production deployments, the actions that this deployment do can be found in template.yaml)
4. Open cloud9 dev environment
5. Disable temporary credentials and remove $HOME/.aws directory to make sure SAM uses your instance profile credentials
6. Clone this repo
7. Navigate to the project folder and edit the template.yaml - Modify line 15 with your load balancer's name (The value Test751 is used as example)
8. Build and deploy:

```bash
cd ALB-Interface-Monitoring
sam build
sam deploy --stack-name AblInterfaceMonitoringStack --region us-east-1  --resolve-s3 --capabilities CAPABILITY_IAM
```

9. (Optional) Execute a local invoke of the lambda function if your load balancer is present before the deployment:

```bash
sam local invoke AlbDiscoverEnis 
```

## Environment tear-down

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