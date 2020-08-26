#!/bin/bash

AMPLIFY_SETTINGS=amplify/#current-cloud-backend/amplify-meta.json

echo "Starting ..."

# Get Amplify Values
export AWS_REGION=$(jq -r '.providers.awscloudformation.Region' $AMPLIFY_SETTINGS)
export AWS_BRANCH=$(jq -r '.envName' amplify/.config/local-env-info.json)
export GRAPHQL_API_ID=$(jq -r '.api[(.api | keys)[0]].output.GraphQLAPIIdOutput' $AMPLIFY_SETTINGS)
export GRAPHQL_ENDPOINT=$(jq -r '.api[(.api | keys)[0]].output.GraphQLAPIEndpointOutput' $AMPLIFY_SETTINGS)


# Encrypt meh API key
# TODO: move into separate script; see aws-serverless-ecommerce-platform/tools/ for inspiration
echo "Encrypting API key ..."
export MEH_API_KEY=$(aws kms encrypt \
    --region $AWS_REGION \
    --key-id $KMS_KEY_ID \
    --plaintext $PLAIN_API_KEY \
    --encryption-context LambdaFunctionName=${BASE_NAME}-dealCheck-${AWS_BRANCH} \
    --cli-binary-format raw-in-base64-out \
    --output text \
    --query CiphertextBlob)

# Deploy
make deploy
