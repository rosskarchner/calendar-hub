#!/bin/bash

# Calendar Hub Prerequisites Deployment Script
# This script deploys all prerequisite AWS resources using CloudFormation

set -e

# Configuration
STACK_NAME="calendar-hub-prerequisites"
TEMPLATE_FILE="cloudformation-prerequisites.yaml"
PARAMETERS_FILE="cloudformation-parameters.json"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if AWS credentials are configured
if ! aws sts get-caller-identity &> /dev/null; then
    log_error "AWS credentials are not configured. Please run 'aws configure' first."
    exit 1
fi

# Check if template file exists
if [ ! -f "$TEMPLATE_FILE" ]; then
    log_error "Template file '$TEMPLATE_FILE' not found."
    exit 1
fi

# Check if parameters file exists
if [ ! -f "$PARAMETERS_FILE" ]; then
    log_error "Parameters file '$PARAMETERS_FILE' not found."
    exit 1
fi

# Validate parameters file
log_info "Validating parameters..."
if grep -q "CHANGE-THIS" "$PARAMETERS_FILE" || grep -q "yourdomain.com" "$PARAMETERS_FILE"; then
    log_error "Please update the parameters in '$PARAMETERS_FILE' with your actual values."
    log_error "Make sure to:"
    log_error "  - Replace 'yourdomain.com' with your actual domain"
    log_error "  - Replace 'outbound@yourdomain.com' with your actual sender email"
    log_error "  - Generate random 32-character strings for CSRF secrets"
    log_error "  - Add your actual GitHub personal access token"
    exit 1
fi

log_info "Deploying Calendar Hub prerequisites to AWS region: $REGION"
log_info "Stack name: $STACK_NAME"

# Validate CloudFormation template
log_info "Validating CloudFormation template..."
aws cloudformation validate-template \
    --template-body file://$TEMPLATE_FILE \
    --region $REGION

if [ $? -eq 0 ]; then
    log_info "Template validation successful."
else
    log_error "Template validation failed."
    exit 1
fi

# Check if stack already exists
if aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION &> /dev/null; then
    log_warn "Stack '$STACK_NAME' already exists. Updating..."
    
    # Update stack
    aws cloudformation update-stack \
        --stack-name $STACK_NAME \
        --template-body file://$TEMPLATE_FILE \
        --parameters file://$PARAMETERS_FILE \
        --capabilities CAPABILITY_NAMED_IAM \
        --region $REGION
    
    log_info "Waiting for stack update to complete..."
    aws cloudformation wait stack-update-complete \
        --stack-name $STACK_NAME \
        --region $REGION
    
    if [ $? -eq 0 ]; then
        log_info "Stack update completed successfully!"
    else
        log_error "Stack update failed. Check the CloudFormation console for details."
        exit 1
    fi
else
    log_info "Creating new stack..."
    
    # Create stack
    aws cloudformation create-stack \
        --stack-name $STACK_NAME \
        --template-body file://$TEMPLATE_FILE \
        --parameters file://$PARAMETERS_FILE \
        --capabilities CAPABILITY_NAMED_IAM \
        --region $REGION \
        --tags Key=Application,Value=CalendarHub Key=Environment,Value=Production
    
    log_info "Waiting for stack creation to complete..."
    aws cloudformation wait stack-create-complete \
        --stack-name $STACK_NAME \
        --region $REGION
    
    if [ $? -eq 0 ]; then
        log_info "Stack creation completed successfully!"
    else
        log_error "Stack creation failed. Check the CloudFormation console for details."
        exit 1
    fi
fi

# Get stack outputs
log_info "Retrieving stack outputs..."
aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
    --output table

log_info "Deployment completed successfully!"
log_info ""
log_info "Next steps:"
log_info "1. Verify your SES email identity in the AWS console"
log_info "2. Move SES out of sandbox mode if needed for production"
log_info "3. Use the IAM role ARN when launching your EC2 instance"
log_info "4. Update your application configuration with the output values"

# Save outputs to a file for easy reference
log_info "Saving outputs to 'stack-outputs.json'..."
aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs' \
    --output json > stack-outputs.json

log_info "Outputs saved to 'stack-outputs.json'"