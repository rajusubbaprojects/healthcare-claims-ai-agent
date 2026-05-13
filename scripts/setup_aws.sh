#!/bin/bash
# Setup AWS infrastructure for Claims AI Agent

set -e

AWS_REGION="us-east-1"
AWS_ACCOUNT_ID="490841876782"
ECR_REPO="claims-agent"
CLUSTER_NAME="claims-agent-cluster"
SERVICE_NAME="claims-agent-service"
TASK_FAMILY="claims-agent-task"
LOG_GROUP="/ecs/claims-agent"

echo "Creating ECS Cluster..."
aws ecs create-cluster \
  --cluster-name $CLUSTER_NAME \
  --region $AWS_REGION

echo "Creating CloudWatch Log Group..."
aws logs create-log-group \
  --log-group-name $LOG_GROUP \
  --region $AWS_REGION || true

echo "Creating ECS Task Execution Role..."
aws iam create-role \
  --role-name ecsTaskExecutionRole-claims \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ecs-tasks.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }' || true

aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole-claims \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy || true

echo "Registering ECS Task Definition..."
aws ecs register-task-definition \
  --family $TASK_FAMILY \
  --network-mode awsvpc \
  --requires-compatibilities FARGATE \
  --cpu "512" \
  --memory "1024" \
  --execution-role-arn arn:aws:iam::${AWS_ACCOUNT_ID}:role/ecsTaskExecutionRole-claims \
  --container-definitions "[
    {
      \"name\": \"claims-agent\",
      \"image\": \"${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}:latest\",
      \"portMappings\": [{
        \"containerPort\": 8000,
        \"protocol\": \"tcp\"
      }],
      \"environment\": [
        {\"name\": \"ENVIRONMENT\", \"value\": \"dev\"},
        {\"name\": \"CHROMA_DB_PATH\", \"value\": \"/app/chroma_db\"}
      ],
      \"secrets\": [],
      \"logConfiguration\": {
        \"logDriver\": \"awslogs\",
        \"options\": {
          \"awslogs-group\": \"${LOG_GROUP}\",
          \"awslogs-region\": \"${AWS_REGION}\",
          \"awslogs-stream-prefix\": \"ecs\"
        }
      },
      \"essential\": true
    }
  ]" \
  --region $AWS_REGION

echo "Getting default VPC and subnets..."
VPC_ID=$(aws ec2 describe-vpcs \
  --filters "Name=isDefault,Values=true" \
  --query "Vpcs[0].VpcId" \
  --output text \
  --region $AWS_REGION)

SUBNET_IDS=$(aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query "Subnets[*].SubnetId" \
  --output text \
  --region $AWS_REGION | tr '\t' ',')

echo "Creating Security Group..."
SG_ID=$(aws ec2 create-security-group \
  --group-name claims-agent-sg \
  --description "Security group for Claims AI Agent" \
  --vpc-id $VPC_ID \
  --region $AWS_REGION \
  --query "GroupId" \
  --output text) || true

aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 8000 \
  --cidr 0.0.0.0/0 \
  --region $AWS_REGION || true

echo "Creating ECS Service..."
aws ecs create-service \
  --cluster $CLUSTER_NAME \
  --service-name $SERVICE_NAME \
  --task-definition $TASK_FAMILY \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_IDS],securityGroups=[$SG_ID],assignPublicIp=ENABLED}" \
  --region $AWS_REGION

echo ""
echo "Infrastructure created successfully!"
echo "Cluster: $CLUSTER_NAME"
echo "Service: $SERVICE_NAME"
echo ""
echo "Next: Push Docker image to ECR then deploy"