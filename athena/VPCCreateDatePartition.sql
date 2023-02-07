ALTER TABLE `alb-interface-monitoring-vpc-flow-logs`
ADD PARTITION (`date`='YEAR-MONTH-DAY')
LOCATION 's3://YOUR_BUCKET_NAME/AWSLogs/YOUR_ACCOUNT_NUMBER/vpcflowlogs/us-east-1/YEAR/MONTH/DAY';
