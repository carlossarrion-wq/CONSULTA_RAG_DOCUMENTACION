#!/bin/bash

# Script para deshabilitar API Key requirement en métodos OPTIONS

API_ID="k1n3got8n7"
REGION="eu-west-1"
STAGE="dev"

echo "Fixing CORS for API Gateway: $API_ID"
echo "Region: $REGION"
echo "Stage: $STAGE"
echo ""

# Obtener recursos del API
echo "Getting API resources..."
RESOURCES=$(aws apigateway get-resources --rest-api-id $API_ID --region $REGION)

# Extraer resource IDs para /analyze-incident y /health
ANALYZE_RESOURCE_ID=$(echo $RESOURCES | jq -r '.items[] | select(.path=="/analyze-incident") | .id')
HEALTH_RESOURCE_ID=$(echo $RESOURCES | jq -r '.items[] | select(.path=="/health") | .id')

echo "Resource ID for /analyze-incident: $ANALYZE_RESOURCE_ID"
echo "Resource ID for /health: $HEALTH_RESOURCE_ID"
echo ""

# Actualizar método OPTIONS para /analyze-incident
if [ ! -z "$ANALYZE_RESOURCE_ID" ]; then
    echo "Updating OPTIONS method for /analyze-incident..."
    aws apigateway update-method \
        --rest-api-id $API_ID \
        --resource-id $ANALYZE_RESOURCE_ID \
        --http-method OPTIONS \
        --patch-operations op=replace,path=/apiKeyRequired,value=false \
        --region $REGION
    
    if [ $? -eq 0 ]; then
        echo "✓ Successfully updated /analyze-incident OPTIONS"
    else
        echo "✗ Failed to update /analyze-incident OPTIONS"
    fi
    echo ""
fi

# Actualizar método OPTIONS para /health
if [ ! -z "$HEALTH_RESOURCE_ID" ]; then
    echo "Updating OPTIONS method for /health..."
    aws apigateway update-method \
        --rest-api-id $API_ID \
        --resource-id $HEALTH_RESOURCE_ID \
        --http-method OPTIONS \
        --patch-operations op=replace,path=/apiKeyRequired,value=false \
        --region $REGION
    
    if [ $? -eq 0 ]; then
        echo "✓ Successfully updated /health OPTIONS"
    else
        echo "✗ Failed to update /health OPTIONS"
    fi
    echo ""
fi

# Crear nuevo deployment
echo "Creating new deployment..."
DEPLOYMENT_ID=$(aws apigateway create-deployment \
    --rest-api-id $API_ID \
    --stage-name $STAGE \
    --region $REGION \
    --query 'id' \
    --output text)

if [ $? -eq 0 ]; then
    echo "✓ Successfully created deployment: $DEPLOYMENT_ID"
    echo ""
    echo "CORS configuration updated successfully!"
    echo "You can now test with:"
    echo "curl -X OPTIONS https://$API_ID.execute-api.$REGION.amazonaws.com/$STAGE/analyze-incident -v"
else
    echo "✗ Failed to create deployment"
    exit 1
fi
