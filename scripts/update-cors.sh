#!/bin/bash

# Script para actualizar la configuración de CORS en API Gateway
# Este script actualiza el stack de CloudFormation para habilitar CORS

set -e

STACK_NAME="incident-analyzer-dev"
REGION="eu-west-1"

echo "🔄 Actualizando configuración de CORS en API Gateway..."

# Obtener el API ID
API_ID=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
    --output text | cut -d'/' -f3 | cut -d'.' -f1)

if [ -z "$API_ID" ]; then
    echo "❌ Error: No se pudo obtener el API ID"
    exit 1
fi

echo "📋 API ID: $API_ID"

# Habilitar CORS para el método POST /analyze
echo "🔧 Configurando CORS para POST /analyze..."
aws apigateway update-integration-response \
    --rest-api-id $API_ID \
    --resource-id $(aws apigateway get-resources --rest-api-id $API_ID --region $REGION --query 'items[?path==`/analyze`].id' --output text) \
    --http-method POST \
    --status-code 200 \
    --patch-operations \
        op=add,path=/responseParameters/method.response.header.Access-Control-Allow-Origin,value="'*'" \
    --region $REGION 2>/dev/null || echo "⚠️  Ya existe o no se pudo actualizar"

# Habilitar CORS para el método GET /health
echo "🔧 Configurando CORS para GET /health..."
aws apigateway update-integration-response \
    --rest-api-id $API_ID \
    --resource-id $(aws apigateway get-resources --rest-api-id $API_ID --region $REGION --query 'items[?path==`/health`].id' --output text) \
    --http-method GET \
    --status-code 200 \
    --patch-operations \
        op=add,path=/responseParameters/method.response.header.Access-Control-Allow-Origin,value="'*'" \
    --region $REGION 2>/dev/null || echo "⚠️  Ya existe o no se pudo actualizar"

# Crear método OPTIONS para /analyze si no existe
echo "🔧 Configurando método OPTIONS para /analyze..."
ANALYZE_RESOURCE_ID=$(aws apigateway get-resources --rest-api-id $API_ID --region $REGION --query 'items[?path==`/analyze`].id' --output text)

aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $ANALYZE_RESOURCE_ID \
    --http-method OPTIONS \
    --authorization-type NONE \
    --region $REGION 2>/dev/null || echo "⚠️  Método OPTIONS ya existe"

aws apigateway put-method-response \
    --rest-api-id $API_ID \
    --resource-id $ANALYZE_RESOURCE_ID \
    --http-method OPTIONS \
    --status-code 200 \
    --response-parameters \
        method.response.header.Access-Control-Allow-Headers=true,\
method.response.header.Access-Control-Allow-Methods=true,\
method.response.header.Access-Control-Allow-Origin=true \
    --region $REGION 2>/dev/null || echo "⚠️  Method response ya existe"

aws apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $ANALYZE_RESOURCE_ID \
    --http-method OPTIONS \
    --type MOCK \
    --request-templates '{"application/json": "{\"statusCode\": 200}"}' \
    --region $REGION 2>/dev/null || echo "⚠️  Integration ya existe"

aws apigateway put-integration-response \
    --rest-api-id $API_ID \
    --resource-id $ANALYZE_RESOURCE_ID \
    --http-method OPTIONS \
    --status-code 200 \
    --response-parameters \
        method.response.header.Access-Control-Allow-Headers="'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,x-api-key'",\
method.response.header.Access-Control-Allow-Methods="'POST,OPTIONS'",\
method.response.header.Access-Control-Allow-Origin="'*'" \
    --region $REGION 2>/dev/null || echo "⚠️  Integration response ya existe"

# Crear método OPTIONS para /health si no existe
echo "🔧 Configurando método OPTIONS para /health..."
HEALTH_RESOURCE_ID=$(aws apigateway get-resources --rest-api-id $API_ID --region $REGION --query 'items[?path==`/health`].id' --output text)

aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $HEALTH_RESOURCE_ID \
    --http-method OPTIONS \
    --authorization-type NONE \
    --region $REGION 2>/dev/null || echo "⚠️  Método OPTIONS ya existe"

aws apigateway put-method-response \
    --rest-api-id $API_ID \
    --resource-id $HEALTH_RESOURCE_ID \
    --http-method OPTIONS \
    --status-code 200 \
    --response-parameters \
        method.response.header.Access-Control-Allow-Headers=true,\
method.response.header.Access-Control-Allow-Methods=true,\
method.response.header.Access-Control-Allow-Origin=true \
    --region $REGION 2>/dev/null || echo "⚠️  Method response ya existe"

aws apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $HEALTH_RESOURCE_ID \
    --http-method OPTIONS \
    --type MOCK \
    --request-templates '{"application/json": "{\"statusCode\": 200}"}' \
    --region $REGION 2>/dev/null || echo "⚠️  Integration ya existe"

aws apigateway put-integration-response \
    --rest-api-id $API_ID \
    --resource-id $HEALTH_RESOURCE_ID \
    --http-method OPTIONS \
    --status-code 200 \
    --response-parameters \
        method.response.header.Access-Control-Allow-Headers="'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,x-api-key'",\
method.response.header.Access-Control-Allow-Methods="'GET,OPTIONS'",\
method.response.header.Access-Control-Allow-Origin="'*'" \
    --region $REGION 2>/dev/null || echo "⚠️  Integration response ya existe"

# Desplegar los cambios
echo "🚀 Desplegando cambios en el stage dev..."
aws apigateway create-deployment \
    --rest-api-id $API_ID \
    --stage-name dev \
    --region $REGION

echo "✅ Configuración de CORS actualizada exitosamente"
echo ""
echo "🔍 Verifica que el dashboard ahora funcione correctamente"
echo "   URL del dashboard: file://$(pwd)/dashboard/index.html"
