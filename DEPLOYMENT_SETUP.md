# 🚀 Deployment Guide - EchoChamber Analyst

Complete guide for deploying EchoChamber Analyst to AWS ECS Fargate with GitHub Actions CI/CD.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [AWS Infrastructure Setup](#aws-infrastructure-setup)
3. [GitHub Actions Setup](#github-actions-setup)
4. [Manual Deployment](#manual-deployment)
5. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Tools
- **AWS Account** with billing enabled
- **AWS CLI** installed and configured with SSO
- **Docker Desktop** installed and running
- **GitHub Account** with repository access
- **Domain Name** (optional but recommended for production)

### Required API Keys
- **OpenAI API Key** - For LLM features
- **LangSmith API Key** - For monitoring (optional)
- **Reddit API** credentials (optional for content scouting)

---

## AWS Infrastructure Setup

### Step 1: Configure AWS SSO

```bash
# Configure AWS SSO with AdministratorAccess role
aws configure sso

# Follow prompts:
# - SSO session name: your-session-name
# - SSO start URL: your-aws-sso-portal-url
# - SSO Region: ap-southeast-1
# - Account: Select your AWS account
# - Role: AdministratorAccess (important!)
# - CLI default region: ap-southeast-1
# - CLI output format: json

# Login
aws sso login --profile your-profile-name

# Verify
aws sts get-caller-identity --profile your-profile-name
```

### Step 2: Create VPC and Networking

**Note**: If you already have VPC, subnets, and security groups, skip to Step 3.

```bash
# Create VPC
aws ec2 create-vpc --cidr-block 10.0.0.0/16 --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=echochamber-vpc}]'

# Create Public and Private Subnets
# Public Subnet 1
aws ec2 create-subnet --vpc-id <vpc-id> --cidr-block 10.0.1.0/24 --availability-zone ap-southeast-1a

# Public Subnet 2
aws ec2 create-subnet --vpc-id <vpc-id> --cidr-block 10.0.2.0/24 --availability-zone ap-southeast-1b

# Private Subnet 1
aws ec2 create-subnet --vpc-id <vpc-id> --cidr-block 10.0.11.0/24 --availability-zone ap-southeast-1a

# Private Subnet 2
aws ec2 create-subnet --vpc-id <vpc-id> --cidr-block 10.0.12.0/24 --availability-zone ap-southeast-1b

# Create Internet Gateway
aws ec2 create-internet-gateway

# Attach to VPC
aws ec2 attach-internet-gateway --vpc-id <vpc-id> --internet-gateway-id <igw-id>

# Create NAT Gateway (for private subnets)
# First allocate Elastic IP
aws ec2 allocate-address --domain vpc

# Create NAT Gateway in public subnet
aws ec2 create-nat-gateway --subnet-id <public-subnet-id> --allocation-id <eip-allocation-id>
```

### Step 3: Create RDS PostgreSQL

```bash
# Create DB subnet group
aws rds create-db-subnet-group \
  --db-subnet-group-name echochamber-db-subnet \
  --db-subnet-group-description "Subnet group for EchoChamber RDS" \
  --subnet-ids subnet-xxx subnet-yyy

# Create security group for RDS
aws ec2 create-security-group \
  --group-name echochamber-rds-sg \
  --description "Security group for EchoChamber RDS" \
  --vpc-id <vpc-id>

# Allow PostgreSQL from ECS tasks
aws ec2 authorize-security-group-ingress \
  --group-id <rds-sg-id> \
  --protocol tcp \
  --port 5432 \
  --source-group <ecs-tasks-sg-id>

# Create RDS PostgreSQL instance
aws rds create-db-instance \
  --db-instance-identifier echochamber-db \
  --db-instance-class db.t4g.micro \
  --engine postgres \
  --engine-version 17.2 \
  --master-username echochamber \
  --master-user-password 'YourSecurePassword123!' \
  --allocated-storage 20 \
  --storage-type gp3 \
  --vpc-security-group-ids <rds-sg-id> \
  --db-subnet-group-name echochamber-db-subnet \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00" \
  --preferred-maintenance-window "mon:04:00-mon:05:00" \
  --no-publicly-accessible \
  --storage-encrypted
```

### Step 4: Create ElastiCache Redis

```bash
# Create cache subnet group
aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name echochamber-redis-subnet \
  --cache-subnet-group-description "Subnet group for EchoChamber Redis" \
  --subnet-ids subnet-xxx subnet-yyy

# Create security group for Redis
aws ec2 create-security-group \
  --group-name echochamber-redis-sg \
  --description "Security group for EchoChamber Redis" \
  --vpc-id <vpc-id>

# Allow Redis from ECS tasks
aws ec2 authorize-security-group-ingress \
  --group-id <redis-sg-id> \
  --protocol tcp \
  --port 6379 \
  --source-group <ecs-tasks-sg-id>

# Create Redis cluster
aws elasticache create-cache-cluster \
  --cache-cluster-id echochamber-redis \
  --engine redis \
  --cache-node-type cache.t4g.micro \
  --num-cache-nodes 1 \
  --security-group-ids <redis-sg-id> \
  --cache-subnet-group-name echochamber-redis-subnet
```

### Step 5: Create AWS Secrets Manager Secrets

```bash
# Database password
aws secretsmanager create-secret \
  --name echochamber/database \
  --description "Database credentials" \
  --secret-string '{"password":"YourSecurePassword123!"}'

# Django secret key
aws secretsmanager create-secret \
  --name echochamber/django \
  --secret-string '{"secret_key":"your-django-secret-key-here"}'

# OpenAI API key
aws secretsmanager create-secret \
  --name echochamber/openai \
  --secret-string '{"api_key":"your-openai-api-key"}'

# LangSmith API key (optional)
aws secretsmanager create-secret \
  --name echochamber/langsmith \
  --secret-string '{"api_key":"your-langsmith-api-key"}'
```

### Step 6: Create ECR Repositories

```bash
# Backend repository
aws ecr create-repository \
  --repository-name echochamber-backend \
  --region ap-southeast-1

# Frontend repository
aws ecr create-repository \
  --repository-name echochamber-frontend \
  --region ap-southeast-1

# Celery repository
aws ecr create-repository \
  --repository-name echochamber-celery \
  --region ap-southeast-1
```

### Step 7: Create ECS Cluster

```bash
# Create ECS cluster
aws ecs create-cluster \
  --cluster-name echochamber-cluster \
  --region ap-southeast-1

# Create execution role (if not exists)
aws iam create-role \
  --role-name ecsTaskExecutionRole \
  --assume-role-policy-document file://ecs-task-execution-trust-policy.json

# Attach managed policy
aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
```

### Step 8: Create Application Load Balancer

```bash
# Create ALB security group
aws ec2 create-security-group \
  --group-name echochamber-alb-sg \
  --description "Security group for ALB" \
  --vpc-id <vpc-id>

# Allow HTTP/HTTPS
aws ec2 authorize-security-group-ingress \
  --group-id <alb-sg-id> \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-id <alb-sg-id> \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0

# Create ALB
aws elbv2 create-load-balancer \
  --name echochamber-alb \
  --subnets <public-subnet-1-id> <public-subnet-2-id> \
  --security-groups <alb-sg-id> \
  --scheme internet-facing
```

---

## GitHub Actions Setup

### Step 1: Create OIDC Provider

```bash
# Create OIDC provider for GitHub Actions
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list a031c46782e6e6c662c2c87c76da9aa62ccabd8e
```

### Step 2: Create IAM Role for GitHub Actions

```bash
# Create trust policy file
cat > github-trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<account-id>:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:<your-github-username>/echo_chamber_analyst:*"
        }
      }
    }
  ]
}
EOF

# Create role
aws iam create-role \
  --role-name GitHubActionsECSDeployRole \
  --assume-role-policy-document file://github-trust-policy.json

# Create permissions policy
cat > github-permissions.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:UpdateService",
        "ecs:DescribeServices",
        "ecs:DescribeTasks",
        "ecs:ListTasks",
        "ecs:RunTask",
        "ecs:DescribeTaskDefinition",
        "ecs:RegisterTaskDefinition"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "iam:PassedToService": "ecs-tasks.amazonaws.com"
        }
      }
    }
  ]
}
EOF

# Attach inline policy
aws iam put-role-policy \
  --role-name GitHubActionsECSDeployRole \
  --policy-name GitHubActionsECSDeployPolicy \
  --policy-document file://github-permissions.json
```

### Step 3: Add GitHub Secrets

Go to your GitHub repository: `Settings` → `Secrets and variables` → `Actions` → `New repository secret`

Add these 5 secrets:

| Secret Name | Value | Example |
|-------------|-------|---------|
| `AWS_ACCOUNT_ID` | Your AWS Account ID | `123456789012` |
| `AWS_ROLE_ARN` | IAM Role ARN from Step 2 | `arn:aws:iam::123456789012:role/GitHubActionsECSDeployRole` |
| `NEXT_PUBLIC_API_URL` | Load Balancer DNS | `https://echochamber-alb-xxx.ap-southeast-1.elb.amazonaws.com` |
| `PRIVATE_SUBNET_IDS` | Private subnet IDs (comma-separated) | `subnet-xxx,subnet-yyy` |
| `BACKEND_SECURITY_GROUP` | ECS tasks security group ID | `sg-xxx` |

---

## Manual Deployment

If you prefer to deploy manually without GitHub Actions:

### Step 1: Build and Push Docker Images

```bash
# Login to ECR
aws ecr get-login-password --region ap-southeast-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.ap-southeast-1.amazonaws.com

# Build and push backend
cd backend
docker build -f Dockerfile.prod -t <account-id>.dkr.ecr.ap-southeast-1.amazonaws.com/echochamber-backend:latest .
docker push <account-id>.dkr.ecr.ap-southeast-1.amazonaws.com/echochamber-backend:latest

# Build and push celery
docker build -f Dockerfile.celery -t <account-id>.dkr.ecr.ap-southeast-1.amazonaws.com/echochamber-celery:latest .
docker push <account-id>.dkr.ecr.ap-southeast-1.amazonaws.com/echochamber-celery:latest

# Build and push frontend
cd ../frontend
docker build -t <account-id>.dkr.ecr.ap-southeast-1.amazonaws.com/echochamber-frontend:latest .
docker push <account-id>.dkr.ecr.ap-southeast-1.amazonaws.com/echochamber-frontend:latest
```

### Step 2: Create ECS Task Definitions

Create task definitions for backend, frontend, and celery services using the AWS Console or CLI.

### Step 3: Create ECS Services

```bash
# Create backend service
aws ecs create-service \
  --cluster echochamber-cluster \
  --service-name echochamber-backend-service \
  --task-definition echochamber-backend \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx,subnet-yyy],securityGroups=[sg-xxx],assignPublicIp=DISABLED}"

# Similar for frontend and celery...
```

---

## Troubleshooting

### Deployment Fails at "Configure AWS credentials"

**Error**: `Not authorized to perform sts:AssumeRoleWithWebIdentity`

**Solution**:
1. Verify `AWS_ROLE_ARN` GitHub secret is correct
2. Check IAM role trust policy includes your GitHub repository
3. Ensure OIDC provider exists

```bash
# Verify role
aws iam get-role --role-name GitHubActionsECSDeployRole

# Check OIDC provider
aws iam list-open-id-connect-providers
```

### Docker Build Fails

**Error**: Dependency conflicts or build errors

**Solution**:
1. Ensure `Dockerfile.celery` uses Python 3.12 (same as `Dockerfile.prod`)
2. Check `requirements.txt` for version conflicts
3. Test build locally:
   ```bash
   docker build -f backend/Dockerfile.prod -t test-backend .
   docker build -f backend/Dockerfile.celery -t test-celery .
   ```

### Service Not Starting

**Error**: ECS tasks fail to start

**Solution**:
1. Check CloudWatch logs:
   ```bash
   aws logs tail /ecs/echochamber-backend --follow
   ```
2. Verify environment variables in task definition
3. Check security group allows traffic
4. Ensure secrets exist in Secrets Manager

### Database Connection Errors

**Error**: Cannot connect to PostgreSQL

**Solution**:
1. Verify RDS security group allows traffic from ECS tasks security group
2. Check database endpoint in environment variables
3. Ensure RDS is in same VPC as ECS tasks
4. Test connection from ECS task:
   ```bash
   aws ecs execute-command \
     --cluster echochamber-cluster \
     --task <task-id> \
     --container backend \
     --interactive \
     --command "/bin/bash"
   ```

### Migration Task Fails

**Error**: Database migration errors

**Solution**:
1. Check migration logs:
   ```bash
   aws logs tail /ecs/echochamber-migrations --since 1h
   ```
2. Run migrations manually:
   ```bash
   aws ecs run-task \
     --cluster echochamber-cluster \
     --task-definition echochamber-migrate-task \
     --launch-type FARGATE \
     --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=DISABLED}"
   ```

---

## Monitoring

### CloudWatch Logs

```bash
# View backend logs
aws logs tail /ecs/echochamber-backend --follow

# View celery logs
aws logs tail /ecs/echochamber-celery --follow

# View migration logs
aws logs tail /ecs/echochamber-migrations --since 30m
```

### ECS Service Status

```bash
# Check service status
aws ecs describe-services \
  --cluster echochamber-cluster \
  --services echochamber-backend-service echochamber-frontend-service

# List running tasks
aws ecs list-tasks --cluster echochamber-cluster

# Describe task
aws ecs describe-tasks \
  --cluster echochamber-cluster \
  --tasks <task-arn>
```

---

## Cost Optimization

**Estimated Monthly Costs**:
- ECS Fargate (3 services): ~$50-80
- RDS PostgreSQL (db.t4g.micro): ~$15-20
- ElastiCache Redis (cache.t4g.micro): ~$12-15
- ALB: ~$20-25
- Data transfer: ~$10-20
- **Total**: ~$100-150/month

**Tips to Reduce Costs**:
1. Use AWS Free Tier where applicable
2. Stop services during development (non-production)
3. Use t4g instance types (ARM-based, cheaper)
4. Enable auto-scaling to scale down during low traffic
5. Use Reserved Instances for RDS (save up to 40%)

---

## Security Best Practices

1. **Never commit secrets** to Git
2. **Use AWS Secrets Manager** for all sensitive data
3. **Enable VPC Flow Logs** for network monitoring
4. **Use HTTPS only** with ACM certificates
5. **Enable RDS encryption** at rest
6. **Regular backups** - Enable automated RDS backups
7. **IAM least privilege** - Only grant necessary permissions
8. **MFA** for AWS root account and IAM users
9. **CloudTrail** enabled for audit logging
10. **Security group** rules - Only allow necessary ports

---

## Rollback

If deployment fails and you need to rollback:

```bash
# List previous task definitions
aws ecs list-task-definitions --family-prefix echochamber-backend --sort DESC

# Update service to previous version
aws ecs update-service \
  --cluster echochamber-cluster \
  --service echochamber-backend-service \
  --task-definition echochamber-backend:7
```

---

## Support

For issues:
- **GitHub Actions**: Check Actions tab for workflow logs
- **ECS Issues**: Check CloudWatch logs
- **Database**: Verify RDS endpoint and credentials
- **General**: Review AWS console for resource status

---

**Last Updated**: 2025-10-18
**Status**: Production Ready 
