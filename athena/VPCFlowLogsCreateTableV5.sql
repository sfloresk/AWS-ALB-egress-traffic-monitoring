CREATE EXTERNAL TABLE IF NOT EXISTS `alb-interface-monitoring-vpc-flow-logs` ( 
    `account_id` string, 
    `action` string, 
    `az_id` string, 
    `bytes` bigint, 
    `dstaddr` string, 
    `dstport` int, 
    `end` bigint, 
    `flow_direction` string,
    `instance_id` string,
    `interface_id` string, 
    `log_status` string, 
    `packets` bigint, 
    `pkt_dst_aws_service` string,
    `pkt_dstaddr` string, 
    `pkt_src_aws_service` string,
    `pkt_srcaddr` string, 
    `protocol` bigint, 
    `region` string, 
    `srcaddr` string, 
    `srcport` int, 
    `start` bigint,
    `sublocation_id` string, 
    `sublocation_type` string, 
    `subnet_id` string, 
    `tcp_flags` int, 
    `traffic_path` int, 
    `type` string, 
    `version` int, 
    `vpc_id` string
)
PARTITIONED BY (`date` date)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ' '
LOCATION 's3://YOUR_BUCKET_NAME/AWSLogs/YOUR_ACCOUNT_NUMBER/vpcflowlogs/us-east-1/'
TBLPROPERTIES ("skip.header.line.count"="1");
