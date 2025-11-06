# 🚀 AWS DEPLOYMENT GUIDE - Vector RAG Chatbot

**For**: EchoChamber Analyst Chatbot Implementation
**Version**: 2.0.0
**Date**: 2025-01-28
**Prerequisites**: AWS Account, AWS CLI configured, Docker installed

---

## 📋 TABLE OF CONTENTS

1. [Prerequisites](#prerequisites)
2. [Architecture Overview](#architecture-overview)
3. [Step-by-Step Deployment](#step-by-step-deployment)
4. [Database Setup (RDS PostgreSQL + pgvector)](#database-setup)
5. [Redis Cache Setup (ElastiCache)](#redis-cache-setup)
6. [Docker Image Build & Push](#docker-image-build--push)
7. [ECS Deployment](#ecs-deployment)
8. [Load Balancer Setup](#load-balancer-setup)
9. [Environment Variables](#environment-variables)
10. [Post-Deployment Tasks](#post-deployment-tasks)
11. [Monitoring & Maintenance](#monitoring--maintenance)
12. [Rollback Procedures](#rollback-procedures)
13. [Troubleshooting](#troubleshooting)

---

## ✅ PREREQUISITES

### Required Tools

```bash
# AWS CLI
aws --version
# aws-cli/2.x.x

# Docker
docker --version
# Docker version 24.x.x

# Docker Compose (for local testing)
docker-compose --version
# docker-compose version 1.29.x
```

### AWS Permissions Required

Your AWS IAM user/role must have permissions for:
- ECS (Fargate)
- RDS (PostgreSQL)
- ElastiCache (Redis)
- ECR (Docker registry)
- VPC, Subnets, Security Groups
- Application Load Balancer
- CloudWatch Logs
- Secrets Manager
- Systems Manager (Parameter Store)

### AWS Services Cost Estimate

| Service | Configuration | Monthly Cost |
|---------|---------------|--------------|
| **RDS PostgreSQL** | db.t3.medium, 100 GB | $61 |
| **ElastiCache Redis** | cache.t3.micro | $14 |
| **ECS Fargate** | 2 tasks, 2 vCPU, 4 GB each | $88 |
| **ALB** | Application Load Balancer | $22 |
| **Data Transfer** | Moderate traffic | $10 |
| **Total Infrastructure** | | **~$195/month** |

---

## 🏗️ ARCHITECTURE OVERVIEW

```
                          ┌─────────────────────────────────────┐
                          │        Internet Gateway             │
                          └─────────────────────────────────────┘
                                          ↓
                          ┌─────────────────────────────────────┐
                          │   Application Load Balancer (ALB)   │
                          │   - HTTPS (port 443)                │
                          │   - Health checks                   │
                          └─────────────────────────────────────┘
                                          ↓
           ┌──────────────────────────────┴──────────────────────────────┐
           ↓                                                              ↓
    ┌─────────────────────┐                                  ┌─────────────────────┐
    │   Public Subnet A   │                                  │   Public Subnet B   │
    │   (us-east-1a)      │                                  │   (us-east-1b)      │
    └─────────────────────┘                                  └─────────────────────┘
           ↓                                                              ↓
    ┌─────────────────────┐                                  ┌─────────────────────┐
    │  ECS Fargate Task   │                                  │  ECS Fargate Task   │
    │  - Django Backend   │                                  │  - Django Backend   │
    │  - 2 vCPU, 4 GB RAM │                                  │  - 2 vCPU, 4 GB RAM │
    └─────────────────────┘                                  └─────────────────────┘
           ↓                                                              ↓
           └──────────────────────────────┬──────────────────────────────┘
                                          ↓
           ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
           │   Private Subnet    │  │   Private Subnet    │  │   Private Subnet    │
           │   (RDS Primary)     │  │   (RDS Standby)     │  │   (ElastiCache)     │
           │   us-east-1a        │  │   us-east-1b        │  │   us-east-1a        │
           └─────────────────────┘  └─────────────────────┘  └─────────────────────┘
                  ↓                         ↓                          ↓
           ┌──────────────┐         ┌──────────────┐         ┌──────────────┐
           │  PostgreSQL  │◄───────►│  PostgreSQL  │         │    Redis     │
           │   (Primary)  │         │  (Standby)   │         │ (Cache.t3.   │
           │ w/ pgvector  │         │ Multi-AZ     │         │   micro)     │
           └──────────────┘         └──────────────┘         └──────────────┘
                  ↓
           Vector Embeddings
           (1536 dimensions)
```

---

## 📝 STEP-BY-STEP DEPLOYMENT

### Phase 1: VPC and Networking

#### Step 1.1: Create VPC

```bash
# Create VPC
aws ec2 create-vpc \
    --cidr-block 10.0.0.0/16 \
    --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=echochamber-vpc}]'

# Save VPC ID
export VPC_ID=<vpc-id-from-output>

# Enable DNS hostnames
aws ec2 modify-vpc-attribute \
    --vpc-id $VPC_ID \
    --enable-dns-hostnames
```

#### Step 1.2: Create Subnets

```bash
# Public Subnet A (for ALB, ECS tasks)
aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.1.0/24 \
    --availability-zone us-east-1a \
    --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=echochamber-public-1a}]'

export PUBLIC_SUBNET_A=<subnet-id>

# Public Subnet B (for high availability)
aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.2.0/24 \
    --availability-zone us-east-1b \
    --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=echochamber-public-1b}]'

export PUBLIC_SUBNET_B=<subnet-id>

# Private Subnet A (for RDS, Redis)
aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.11.0/24 \
    --availability-zone us-east-1a \
    --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=echochamber-private-1a}]'

export PRIVATE_SUBNET_A=<subnet-id>

# Private Subnet B (for RDS Multi-AZ)
aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.12.0/24 \
    --availability-zone us-east-1b \
    --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=echochamber-private-1b}]'

export PRIVATE_SUBNET_B=<subnet-id>
```

#### Step 1.3: Internet Gateway

```bash
# Create Internet Gateway
aws ec2 create-internet-gateway \
    --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=echochamber-igw}]'

export IGW_ID=<igw-id>

# Attach to VPC
aws ec2 attach-internet-gateway \
    --vpc-id $VPC_ID \
    --internet-gateway-id $IGW_ID
```

#### Step 1.4: Route Tables

```bash
# Create route table for public subnets
aws ec2 create-route-table \
    --vpc-id $VPC_ID \
    --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=echochamber-public-rt}]'

export PUBLIC_RT=<route-table-id>

# Add route to Internet Gateway
aws ec2 create-route \
    --route-table-id $PUBLIC_RT \
    --destination-cidr-block 0.0.0.0/0 \
    --gateway-id $IGW_ID

# Associate with public subnets
aws ec2 associate-route-table --subnet-id $PUBLIC_SUBNET_A --route-table-id $PUBLIC_RT
aws ec2 associate-route-table --subnet-id $PUBLIC_SUBNET_B --route-table-id $PUBLIC_RT
```

#### Step 1.5: Security Groups

```bash
# ALB Security Group
aws ec2 create-security-group \
    --group-name echochamber-alb-sg \
    --description "Security group for ALB" \
    --vpc-id $VPC_ID

export ALB_SG=<security-group-id>

# Allow HTTPS from anywhere
aws ec2 authorize-security-group-ingress \
    --group-id $ALB_SG \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0

# ECS Security Group
aws ec2 create-security-group \
    --group-name echochamber-ecs-sg \
    --description "Security group for ECS tasks" \
    --vpc-id $VPC_ID

export ECS_SG=<security-group-id>

# Allow traffic from ALB
aws ec2 authorize-security-group-ingress \
    --group-id $ECS_SG \
    --protocol tcp \
    --port 8000 \
    --source-group $ALB_SG

# RDS Security Group
aws ec2 create-security-group \
    --group-name echochamber-rds-sg \
    --description "Security group for RDS" \
    --vpc-id $VPC_ID

export RDS_SG=<security-group-id>

# Allow PostgreSQL from ECS
aws ec2 authorize-security-group-ingress \
    --group-id $RDS_SG \
    --protocol tcp \
    --port 5432 \
    --source-group $ECS_SG

# Redis Security Group
aws ec2 create-security-group \
    --group-name echochamber-redis-sg \
    --description "Security group for Redis" \
    --vpc-id $VPC_ID

export REDIS_SG=<security-group-id>

# Allow Redis from ECS
aws ec2 authorize-security-group-ingress \
    --group-id $REDIS_SG \
    --protocol tcp \
    --port 6379 \
    --source-group $ECS_SG
```

---

## 💾 DATABASE SETUP

### Step 2.1: Create RDS Parameter Group (for pgvector)

```bash
# Create parameter group
aws rds create-db-parameter-group \
    --db-parameter-group-name echochamber-pg15-pgvector \
    --db-parameter-group-family postgres15 \
    --description "PostgreSQL 15 with pgvector support"

# Enable pgvector extension (requires RDS 15.3+)
aws rds modify-db-parameter-group \
    --db-parameter-group-name echochamber-pg15-pgvector \
    --parameters "ParameterName=shared_preload_libraries,ParameterValue=vector,ApplyMethod=pending-reboot"
```

### Step 2.2: Create DB Subnet Group

```bash
aws rds create-db-subnet-group \
    --db-subnet-group-name echochamber-db-subnet-group \
    --db-subnet-group-description "Subnet group for EchoChamber RDS" \
    --subnet-ids $PRIVATE_SUBNET_A $PRIVATE_SUBNET_B \
    --tags Key=Name,Value=echochamber-db-subnet-group
```

### Step 2.3: Create RDS PostgreSQL Instance

```bash
# Store database password in Secrets Manager
aws secretsmanager create-secret \
    --name echochamber/database/password \
    --description "PostgreSQL database password" \
    --secret-string "$(openssl rand -base64 32)"

export DB_PASSWORD=$(aws secretsmanager get-secret-value \
    --secret-id echochamber/database/password \
    --query SecretString \
    --output text)

# Create RDS instance
aws rds create-db-instance \
    --db-instance-identifier echochamber-postgres \
    --db-instance-class db.t3.medium \
    --engine postgres \
    --engine-version 15.3 \
    --master-username echochamber_admin \
    --master-user-password "$DB_PASSWORD" \
    --allocated-storage 100 \
    --storage-type gp3 \
    --storage-encrypted \
    --db-parameter-group-name echochamber-pg15-pgvector \
    --db-subnet-group-name echochamber-db-subnet-group \
    --vpc-security-group-ids $RDS_SG \
    --multi-az \
    --backup-retention-period 7 \
    --preferred-backup-window "03:00-04:00" \
    --preferred-maintenance-window "sun:04:00-sun:05:00" \
    --enable-performance-insights \
    --performance-insights-retention-period 7 \
    --publicly-accessible false \
    --tags Key=Name,Value=echochamber-postgres

# Wait for RDS to be available (takes 10-15 minutes)
aws rds wait db-instance-available \
    --db-instance-identifier echochamber-postgres

# Get RDS endpoint
export DB_ENDPOINT=$(aws rds describe-db-instances \
    --db-instance-identifier echochamber-postgres \
    --query 'DBInstances[0].Endpoint.Address' \
    --output text)

echo "Database endpoint: $DB_ENDPOINT"
```

### Step 2.4: Enable pgvector Extension

```bash
# Connect to database (you may need a bastion host or VPN)
psql "postgresql://echochamber_admin:$DB_PASSWORD@$DB_ENDPOINT:5432/postgres"

# In psql:
CREATE DATABASE echochamber_analyst;
\c echochamber_analyst

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify installation
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Test vector functionality
CREATE TABLE test_vectors (id serial PRIMARY KEY, embedding vector(3));
INSERT INTO test_vectors (embedding) VALUES ('[1,2,3]'), ('[4,5,6]');
SELECT * FROM test_vectors ORDER BY embedding <-> '[3,1,2]' LIMIT 2;

-- Clean up test
DROP TABLE test_vectors;

\q
```

### Step 2.5: Create Database URL Secret

```bash
# Store full DATABASE_URL in Secrets Manager
export DATABASE_URL="postgresql://echochamber_admin:$DB_PASSWORD@$DB_ENDPOINT:5432/echochamber_analyst"

aws secretsmanager create-secret \
    --name echochamber/database/url \
    --description "Complete DATABASE_URL for application" \
    --secret-string "$DATABASE_URL"
```

---

## 🔴 REDIS CACHE SETUP

### Step 3.1: Create ElastiCache Subnet Group

```bash
aws elasticache create-cache-subnet-group \
    --cache-subnet-group-name echochamber-redis-subnet-group \
    --cache-subnet-group-description "Subnet group for EchoChamber Redis" \
    --subnet-ids $PRIVATE_SUBNET_A $PRIVATE_SUBNET_B
```

### Step 3.2: Create Redis Cluster

```bash
aws elasticache create-replication-group \
    --replication-group-id echochamber-redis \
    --replication-group-description "Redis cache for EchoChamber" \
    --engine redis \
    --engine-version 7.0 \
    --cache-node-type cache.t3.micro \
    --num-cache-clusters 1 \
    --automatic-failover-enabled false \
    --cache-subnet-group-name echochamber-redis-subnet-group \
    --security-group-ids $REDIS_SG \
    --at-rest-encryption-enabled true \
    --transit-encryption-enabled false \
    --tags Key=Name,Value=echochamber-redis

# Wait for Redis to be available (takes 5-10 minutes)
aws elasticache wait replication-group-available \
    --replication-group-id echochamber-redis

# Get Redis endpoint
export REDIS_ENDPOINT=$(aws elasticache describe-replication-groups \
    --replication-group-id echochamber-redis \
    --query 'ReplicationGroups[0].NodeGroups[0].PrimaryEndpoint.Address' \
    --output text)

echo "Redis endpoint: $REDIS_ENDPOINT"

# Store Redis URL in Secrets Manager
export REDIS_URL="redis://$REDIS_ENDPOINT:6379/0"

aws secretsmanager create-secret \
    --name echochamber/redis/url \
    --description "Redis connection URL" \
    --secret-string "$REDIS_URL"
```

---

## 🐳 DOCKER IMAGE BUILD & PUSH

### Step 4.1: Create ECR Repository

```bash
# Create ECR repository
aws ecr create-repository \
    --repository-name echochamber-analyst \
    --image-scanning-configuration scanOnPush=true \
    --encryption-configuration encryptionType=AES256

export ECR_REGISTRY=$(aws ecr describe-repositories \
    --repository-names echochamber-analyst \
    --query 'repositories[0].repositoryUri' \
    --output text | cut -d'/' -f1)

echo "ECR Registry: $ECR_REGISTRY"
```

### Step 4.2: Build Docker Image

```bash
cd /Users/jithinkrishnan/Documents/Study/IS06\ /MVP/newgit/echo_chamber_analyst

# Build production Docker image
docker build \
    -f backend/Dockerfile.prod \
    -t echochamber-analyst:latest \
    -t echochamber-analyst:v2.0.0 \
    -t $ECR_REGISTRY/echochamber-analyst:latest \
    -t $ECR_REGISTRY/echochamber-analyst:v2.0.0 \
    backend/

# Test image locally (optional)
docker run --rm \
    -e DATABASE_URL="$DATABASE_URL" \
    -e REDIS_URL="$REDIS_URL" \
    -e OPENAI_API_KEY="your-openai-key" \
    -p 8000:8000 \
    echochamber-analyst:latest
```

### Step 4.3: Push to ECR

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | \
    docker login --username AWS --password-stdin $ECR_REGISTRY

# Push images
docker push $ECR_REGISTRY/echochamber-analyst:latest
docker push $ECR_REGISTRY/echochamber-analyst:v2.0.0

echo "Image pushed to: $ECR_REGISTRY/echochamber-analyst:v2.0.0"
```

---

## 🚀 ECS DEPLOYMENT

### Step 5.1: Create ECS Cluster

```bash
aws ecs create-cluster \
    --cluster-name echochamber-cluster \
    --capacity-providers FARGATE FARGATE_SPOT \
    --default-capacity-provider-strategy \
        capacityProvider=FARGATE,weight=1,base=1 \
    --tags key=Name,value=echochamber-cluster
```

### Step 5.2: Create IAM Execution Role

```bash
# Create trust policy
cat > ecs-task-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create execution role
aws iam create-role \
    --role-name echochamberECSTaskExecutionRole \
    --assume-role-policy-document file://ecs-task-trust-policy.json

# Attach managed policy
aws iam attach-role-policy \
    --role-name echochamberECSTaskExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Add Secrets Manager access
cat > secrets-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-east-1:*:secret:echochamber/*"
      ]
    }
  ]
}
EOF

aws iam put-role-policy \
    --role-name echochamberECSTaskExecutionRole \
    --policy-name SecretsManagerAccess \
    --policy-document file://secrets-policy.json

export EXECUTION_ROLE_ARN=$(aws iam get-role \
    --role-name echochamberECSTaskExecutionRole \
    --query 'Role.Arn' \
    --output text)
```

### Step 5.3: Create IAM Task Role

```bash
# Create task role (for application permissions)
aws iam create-role \
    --role-name echochamberECSTaskRole \
    --assume-role-policy-document file://ecs-task-trust-policy.json

# Add CloudWatch Logs access
cat > task-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:*:secret:echochamber/*"
    }
  ]
}
EOF

aws iam put-role-policy \
    --role-name echochamberECSTaskRole \
    --policy-name ApplicationAccess \
    --policy-document file://task-policy.json

export TASK_ROLE_ARN=$(aws iam get-role \
    --role-name echochamberECSTaskRole \
    --query 'Role.Arn' \
    --output text)
```

### Step 5.4: Create CloudWatch Log Group

```bash
aws logs create-log-group \
    --log-group-name /ecs/echochamber-analyst

aws logs put-retention-policy \
    --log-group-name /ecs/echochamber-analyst \
    --retention-in-days 7
```

### Step 5.5: Register Task Definition

```bash
# Get secret ARNs
export DB_URL_SECRET=$(aws secretsmanager describe-secret \
    --secret-id echochamber/database/url \
    --query 'ARN' \
    --output text)

export REDIS_URL_SECRET=$(aws secretsmanager describe-secret \
    --secret-id echochamber/redis/url \
    --query 'ARN' \
    --output text)

# Create task definition
cat > task-definition.json <<EOF
{
  "family": "echochamber-analyst",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "executionRoleArn": "$EXECUTION_ROLE_ARN",
  "taskRoleArn": "$TASK_ROLE_ARN",
  "containerDefinitions": [
    {
      "name": "echochamber-backend",
      "image": "$ECR_REGISTRY/echochamber-analyst:v2.0.0",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DEBUG",
          "value": "False"
        },
        {
          "name": "ALLOWED_HOSTS",
          "value": "*"
        },
        {
          "name": "LANGCHAIN_TRACING_V2",
          "value": "true"
        }
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "$DB_URL_SECRET"
        },
        {
          "name": "REDIS_URL",
          "valueFrom": "$REDIS_URL_SECRET"
        },
        {
          "name": "CELERY_BROKER_URL",
          "valueFrom": "$REDIS_URL_SECRET"
        },
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:echochamber/openai/api-key"
        },
        {
          "name": "LANGSMITH_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:echochamber/langsmith/api-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/echochamber-analyst",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "backend"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/api/v1/health/ || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
EOF

# Register task definition
aws ecs register-task-definition \
    --cli-input-json file://task-definition.json

echo "Task definition registered"
```

---

## ⚖️ LOAD BALANCER SETUP

### Step 6.1: Create Application Load Balancer

```bash
aws elbv2 create-load-balancer \
    --name echochamber-alb \
    --subnets $PUBLIC_SUBNET_A $PUBLIC_SUBNET_B \
    --security-groups $ALB_SG \
    --scheme internet-facing \
    --type application \
    --ip-address-type ipv4 \
    --tags Key=Name,Value=echochamber-alb

export ALB_ARN=$(aws elbv2 describe-load-balancers \
    --names echochamber-alb \
    --query 'LoadBalancers[0].LoadBalancerArn' \
    --output text)

export ALB_DNS=$(aws elbv2 describe-load-balancers \
    --names echochamber-alb \
    --query 'LoadBalancers[0].DNSName' \
    --output text)

echo "ALB DNS: $ALB_DNS"
```

### Step 6.2: Create Target Group

```bash
aws elbv2 create-target-group \
    --name echochamber-tg \
    --protocol HTTP \
    --port 8000 \
    --vpc-id $VPC_ID \
    --target-type ip \
    --health-check-enabled \
    --health-check-protocol HTTP \
    --health-check-path /api/v1/health/ \
    --health-check-interval-seconds 30 \
    --health-check-timeout-seconds 5 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 3

export TARGET_GROUP_ARN=$(aws elbv2 describe-target-groups \
    --names echochamber-tg \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text)
```

### Step 6.3: Create HTTPS Listener (Requires SSL Certificate)

```bash
# Option 1: If you have an ACM certificate
export CERTIFICATE_ARN="arn:aws:acm:us-east-1:ACCOUNT_ID:certificate/CERT_ID"

aws elbv2 create-listener \
    --load-balancer-arn $ALB_ARN \
    --protocol HTTPS \
    --port 443 \
    --certificates CertificateArn=$CERTIFICATE_ARN \
    --default-actions Type=forward,TargetGroupArn=$TARGET_GROUP_ARN

# Option 2: For testing, use HTTP (NOT FOR PRODUCTION)
aws elbv2 create-listener \
    --load-balancer-arn $ALB_ARN \
    --protocol HTTP \
    --port 80 \
    --default-actions Type=forward,TargetGroupArn=$TARGET_GROUP_ARN
```

---

## 🎯 CREATE ECS SERVICE

### Step 7.1: Run Database Migrations

```bash
# Run migrations as a one-time ECS task
aws ecs run-task \
    --cluster echochamber-cluster \
    --task-definition echochamber-analyst \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$PUBLIC_SUBNET_A],securityGroups=[$ECS_SG],assignPublicIp=ENABLED}" \
    --overrides '{
      "containerOverrides": [{
        "name": "echochamber-backend",
        "command": ["python", "manage.py", "migrate"]
      }]
    }'

# Wait for migration task to complete
# Check task status in AWS Console or via CLI

# Create superuser (optional, for admin access)
aws ecs run-task \
    --cluster echochamber-cluster \
    --task-definition echochamber-analyst \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$PUBLIC_SUBNET_A],securityGroups=[$ECS_SG],assignPublicIp=ENABLED}" \
    --overrides '{
      "containerOverrides": [{
        "name": "echochamber-backend",
        "command": ["python", "manage.py", "createsuperuser", "--noinput", "--username", "admin", "--email", "admin@example.com"]
      }]
    }'
```

### Step 7.2: Generate Initial Embeddings

```bash
# Run embedding generation task
aws ecs run-task \
    --cluster echochamber-cluster \
    --task-definition echochamber-analyst \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$PUBLIC_SUBNET_A],securityGroups=[$ECS_SG],assignPublicIp=ENABLED}" \
    --overrides '{
      "containerOverrides": [{
        "name": "echochamber-backend",
        "command": ["python", "manage.py", "generate_embeddings", "--all"]
      }]
    }'

# This will take ~100 minutes for 10K items
# Monitor progress in CloudWatch Logs
```

### Step 7.3: Create ECS Service

```bash
aws ecs create-service \
    --cluster echochamber-cluster \
    --service-name echochamber-service \
    --task-definition echochamber-analyst \
    --desired-count 2 \
    --launch-type FARGATE \
    --platform-version LATEST \
    --network-configuration "awsvpcConfiguration={subnets=[$PUBLIC_SUBNET_A,$PUBLIC_SUBNET_B],securityGroups=[$ECS_SG],assignPublicIp=ENABLED}" \
    --load-balancers targetGroupArn=$TARGET_GROUP_ARN,containerName=echochamber-backend,containerPort=8000 \
    --health-check-grace-period-seconds 60 \
    --deployment-configuration "maximumPercent=200,minimumHealthyPercent=100,deploymentCircuitBreaker={enable=true,rollback=true}" \
    --tags key=Name,value=echochamber-service

echo "ECS Service created successfully!"
echo "Access your application at: http://$ALB_DNS"
```

---

## 🔧 ENVIRONMENT VARIABLES

### Required Secrets in AWS Secrets Manager

```bash
# Database
aws secretsmanager create-secret \
    --name echochamber/database/url \
    --secret-string "postgresql://user:pass@host:5432/db"

# Redis
aws secretsmanager create-secret \
    --name echochamber/redis/url \
    --secret-string "redis://host:6379/0"

# OpenAI API Key
aws secretsmanager create-secret \
    --name echochamber/openai/api-key \
    --secret-string "sk-..."

# LangSmith API Key (optional, for monitoring)
aws secretsmanager create-secret \
    --name echochamber/langsmith/api-key \
    --secret-string "ls-..."

# LangSmith Project Name
aws secretsmanager create-secret \
    --name echochamber/langsmith/project \
    --secret-string "echochamber-analyst-prod"
```

### Environment Variables in Task Definition

| Variable | Value | Purpose |
|----------|-------|---------|
| `DEBUG` | `False` | Disable debug mode in production |
| `ALLOWED_HOSTS` | `*` or your domain | Django allowed hosts |
| `LANGCHAIN_TRACING_V2` | `true` | Enable LangSmith tracing |

---

## ✅ POST-DEPLOYMENT TASKS

### Task 1: Verify Health

```bash
# Check ALB health
curl http://$ALB_DNS/api/v1/health/

# Expected response:
# {"status":"healthy","timestamp":"...","service":"echochamber-analyst"}

# Check ECS service status
aws ecs describe-services \
    --cluster echochamber-cluster \
    --services echochamber-service \
    --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount}'
```

### Task 2: Test Chatbot Endpoint

```bash
# Test chat query
curl -X POST http://$ALB_DNS/api/v1/chat/ \
    -H "Content-Type: application/json" \
    -d '{
      "query": "What are the top pain points?",
      "conversation_history": []
    }'

# Expected: JSON response with chatbot answer
```

### Task 3: Monitor Logs

```bash
# Stream CloudWatch logs
aws logs tail /ecs/echochamber-analyst --follow

# Check for errors
aws logs filter-log-events \
    --log-group-name /ecs/echochamber-analyst \
    --filter-pattern "ERROR" \
    --start-time $(date -u -d '1 hour ago' +%s)000
```

### Task 4: Setup CloudWatch Alarms

```bash
# CPU utilization alarm
aws cloudwatch put-metric-alarm \
    --alarm-name echochamber-high-cpu \
    --alarm-description "ECS task CPU utilization > 80%" \
    --metric-name CPUUtilization \
    --namespace AWS/ECS \
    --statistic Average \
    --period 300 \
    --evaluation-periods 2 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=ServiceName,Value=echochamber-service Name=ClusterName,Value=echochamber-cluster

# Memory utilization alarm
aws cloudwatch put-metric-alarm \
    --alarm-name echochamber-high-memory \
    --alarm-description "ECS task memory utilization > 80%" \
    --metric-name MemoryUtilization \
    --namespace AWS/ECS \
    --statistic Average \
    --period 300 \
    --evaluation-periods 2 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=ServiceName,Value=echochamber-service Name=ClusterName,Value=echochamber-cluster

# Unhealthy target alarm
aws cloudwatch put-metric-alarm \
    --alarm-name echochamber-unhealthy-targets \
    --alarm-description "Unhealthy targets in target group" \
    --metric-name UnHealthyHostCount \
    --namespace AWS/ApplicationELB \
    --statistic Average \
    --period 60 \
    --evaluation-periods 2 \
    --threshold 1 \
    --comparison-operator GreaterThanOrEqualToThreshold \
    --dimensions Name=TargetGroup,Value=$(echo $TARGET_GROUP_ARN | cut -d':' -f6) Name=LoadBalancer,Value=$(echo $ALB_ARN | cut -d':' -f6)
```

---

## 📊 MONITORING & MAINTENANCE

### CloudWatch Dashboards

```bash
# Create custom dashboard
aws cloudwatch put-dashboard \
    --dashboard-name EchoChamber-Analyst \
    --dashboard-body file://cloudwatch-dashboard.json
```

**cloudwatch-dashboard.json**:
```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/ECS", "CPUUtilization", {"stat": "Average"}],
          [".", "MemoryUtilization", {"stat": "Average"}]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "ECS Resources"
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/ApplicationELB", "TargetResponseTime", {"stat": "Average"}],
          [".", "RequestCount", {"stat": "Sum"}]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "ALB Metrics"
      }
    }
  ]
}
```

### RDS Performance Insights

```bash
# Enable Performance Insights (already enabled during creation)
# Access via AWS Console: RDS > Performance Insights

# Check slow queries
aws rds describe-db-parameters \
    --db-parameter-group-name echochamber-pg15-pgvector \
    --query "Parameters[?ParameterName=='log_min_duration_statement'].{Value:ParameterValue}"
```

### Cost Monitoring

```bash
# Enable Cost Explorer
# Setup budget alert
aws budgets create-budget \
    --account-id $(aws sts get-caller-identity --query Account --output text) \
    --budget file://budget.json

# budget.json
{
  "BudgetName": "EchoChamber-Monthly-Budget",
  "BudgetLimit": {
    "Amount": "500",
    "Unit": "USD"
  },
  "TimeUnit": "MONTHLY",
  "BudgetType": "COST"
}
```

---

## 🔄 ROLLBACK PROCEDURES

### Rollback to Previous Task Definition

```bash
# List task definition revisions
aws ecs list-task-definitions \
    --family-prefix echochamber-analyst \
    --sort DESC

# Update service to previous revision
aws ecs update-service \
    --cluster echochamber-cluster \
    --service echochamber-service \
    --task-definition echochamber-analyst:PREVIOUS_REVISION

# Monitor rollback
aws ecs wait services-stable \
    --cluster echochamber-cluster \
    --services echochamber-service
```

### Database Rollback (if migrations fail)

```bash
# Connect to RDS
psql "$DATABASE_URL"

# Show migration history
SELECT * FROM django_migrations ORDER BY applied DESC LIMIT 10;

# Rollback specific migration
python manage.py migrate common 00XX_previous_migration

# Or restore from RDS snapshot
aws rds restore-db-instance-from-db-snapshot \
    --db-instance-identifier echochamber-postgres-restored \
    --db-snapshot-identifier echochamber-postgres-backup-20250128
```

---

## 🐛 TROUBLESHOOTING

### Issue 1: Tasks Failing to Start

**Check logs**:
```bash
aws logs tail /ecs/echochamber-analyst --follow

# Common causes:
# - Database connection failure
# - Missing environment variables
# - Image pull errors
```

**Solution**:
```bash
# Verify secrets are accessible
aws secretsmanager get-secret-value --secret-id echochamber/database/url

# Check task execution role permissions
aws iam get-role-policy \
    --role-name echochamberECSTaskExecutionRole \
    --policy-name SecretsManagerAccess
```

### Issue 2: pgvector Extension Not Found

**Error**: `ERROR: could not open extension control file ".../vector.control"`

**Solution**:
```bash
# Verify parameter group
aws rds describe-db-parameters \
    --db-parameter-group-name echochamber-pg15-pgvector \
    --query "Parameters[?ParameterName=='shared_preload_libraries']"

# If not set, reboot instance after setting
aws rds reboot-db-instance --db-instance-identifier echochamber-postgres
```

### Issue 3: High Database Connection Count

**Solution**:
```bash
# Check active connections
psql "$DATABASE_URL" -c "SELECT count(*) FROM pg_stat_activity;"

# Adjust ECS service count or use PgBouncer
# Install PgBouncer as sidecar container or separate service
```

### Issue 4: Slow Vector Searches

**Solution**:
```sql
-- Check index usage
EXPLAIN ANALYZE
SELECT * FROM common_processedcontent
ORDER BY embedding <-> '[...]'::vector
LIMIT 10;

-- Rebuild index with optimal parameters
REINDEX INDEX idx_processed_content_embedding;

-- Or switch to HNSW (better performance, more memory)
CREATE INDEX idx_processed_content_embedding_hnsw
ON common_processedcontent USING hnsw (embedding vector_cosine_ops);
```

---

## 📝 DEPLOYMENT CHECKLIST

- [ ] VPC and subnets created
- [ ] Security groups configured
- [ ] RDS PostgreSQL instance running
- [ ] pgvector extension enabled
- [ ] ElastiCache Redis cluster running
- [ ] ECR repository created
- [ ] Docker image built and pushed
- [ ] ECS cluster created
- [ ] IAM roles created (execution + task)
- [ ] Task definition registered
- [ ] Application Load Balancer created
- [ ] Target group created
- [ ] Listener configured (HTTPS recommended)
- [ ] Secrets stored in Secrets Manager
- [ ] Database migrations run
- [ ] Initial embeddings generated
- [ ] ECS service created with 2 tasks
- [ ] Health checks passing
- [ ] CloudWatch alarms configured
- [ ] Cost budget alerts setup
- [ ] LangSmith monitoring active
- [ ] Backup policy configured

---

## 🎉 DEPLOYMENT COMPLETE!

Your Vector RAG Chatbot is now deployed on AWS!

**Access your application**:
- API: `http://YOUR_ALB_DNS/api/v1/`
- Health: `http://YOUR_ALB_DNS/api/v1/health/`
- Chat: `POST http://YOUR_ALB_DNS/api/v1/chat/`

**Next Steps**:
1. Configure custom domain with Route 53
2. Setup SSL certificate with ACM
3. Enable auto-scaling policies
4. Configure backup schedules
5. Setup CI/CD pipeline (GitHub Actions or AWS CodePipeline)

**Support**:
- Issues: Check CloudWatch Logs and Performance Insights

---

**Estimated Total Deployment Time**: 2-3 hours
**Monthly Cost**: ~$195 infrastructure + API costs (see CHATBOT_APPENDIX.md for details)
