#!/bin/bash

# Debug ECS Deployment Issues
# This script helps diagnose why the backend service is failing ALB health checks

set -e

CLUSTER="echochamber-cluster"
SERVICE="echochamber-backend-service"
REGION="ap-southeast-1"

echo "========================================="
echo "ECS Backend Deployment Debugging"
echo "========================================="
echo ""

# 1. Get the latest task ARN
echo "📋 Getting latest task..."
TASK_ARN=$(aws ecs list-tasks \
  --cluster $CLUSTER \
  --service-name $SERVICE \
  --region $REGION \
  --query 'taskArns[0]' \
  --output text)

if [ -z "$TASK_ARN" ] || [ "$TASK_ARN" = "None" ]; then
  echo "❌ No tasks found for service $SERVICE"
  exit 1
fi

echo "✅ Task ARN: $TASK_ARN"
echo ""

# 2. Get task details
echo "📊 Task Details:"
aws ecs describe-tasks \
  --cluster $CLUSTER \
  --tasks $TASK_ARN \
  --region $REGION \
  --query 'tasks[0].{Status:lastStatus,Health:healthStatus,StartedAt:startedAt,StoppedAt:stoppedAt,StopReason:stoppedReason,Containers:containers[*].[name,lastStatus,healthStatus,exitCode]}' \
  --output table
echo ""

# 3. Get container logs (last 50 lines)
echo "📜 Container Logs (last 50 lines):"
echo "-----------------------------------"
aws logs tail /ecs/echochamber-backend \
  --since 30m \
  --format short \
  --filter-pattern "" \
  --region $REGION \
  2>/dev/null | tail -50 || echo "⚠️  Could not fetch logs. Check CloudWatch log group name."
echo ""

# 4. Get ALB Target Group Health
echo "🏥 Checking ALB Target Group Health:"
echo "-----------------------------------"

# Get target group ARN
TG_ARN=$(aws elbv2 describe-target-groups \
  --region $REGION \
  --query "TargetGroups[?contains(TargetGroupName, 'echochamber-backend')].TargetGroupArn" \
  --output text | head -1)

if [ -z "$TG_ARN" ]; then
  echo "❌ Could not find backend target group"
else
  echo "Target Group: $TG_ARN"
  echo ""

  # Get target health
  echo "Target Health Status:"
  aws elbv2 describe-target-health \
    --target-group-arn $TG_ARN \
    --region $REGION \
    --output table
  echo ""

  # Get health check configuration
  echo "Health Check Configuration:"
  aws elbv2 describe-target-groups \
    --target-group-arns $TG_ARN \
    --region $REGION \
    --query 'TargetGroups[0].{Protocol:HealthCheckProtocol,Path:HealthCheckPath,Port:HealthCheckPort,Interval:HealthCheckIntervalSeconds,Timeout:HealthCheckTimeoutSeconds,HealthyThreshold:HealthyThresholdCount,UnhealthyThreshold:UnhealthyThresholdCount}' \
    --output table
fi

echo ""
echo "========================================="
echo "Debugging Tips:"
echo "========================================="
echo "1. Check if container logs show any errors"
echo "2. Verify the health check path matches your endpoint"
echo "3. Ensure the backend is listening on port 8000"
echo "4. Check if database/Redis connections are working"
echo "5. Look for unhealthy target status and reason"
echo ""
