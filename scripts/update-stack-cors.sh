#!/bin/bash

# Script para actualizar el stack de CloudFormation con la nueva configuración de CORS

set -e

STACK_NAME="incident-analyzer-dev"
REGION="eu-west-1"
TEMPLATE_FILE="infrastructure/incident-analyzer-template.yaml"

echo "🔄 Actualizando stack de CloudFormation con configuración de CORS..."

# Obtener parámetros actuales del stack
echo "📋 Obteniendo parámetros actuales del stack..."
PARAMETERS=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Parameters' \
    --output json)

# Convertir parámetros a formato para update-stack
PARAM_OVERRIDES=""
for param in $(echo $PARAMETERS | jq -r '.[] | @base64'); do
    _jq() {
        echo ${param} | base64 --decode | jq -r ${1}
    }
    KEY=$(_jq '.ParameterKey')
    VALUE=$(_jq '.ParameterValue')
    
    # Saltar parámetros sensibles que no queremos cambiar
    if [ "$KEY" != "AuroraPassword" ]; then
        PARAM_OVERRIDES="$PARAM_OVERRIDES ParameterKey=$KEY,ParameterValue=$VALUE"
    else
        PARAM_OVERRIDES="$PARAM_OVERRIDES ParameterKey=$KEY,UsePreviousValue=true"
    fi
done

echo "🚀 Actualizando stack..."
aws cloudformation update-stack \
    --stack-name $STACK_NAME \
    --template-body file://$TEMPLATE_FILE \
    --parameters $PARAM_OVERRIDES \
    --capabilities CAPABILITY_IAM \
    --region $REGION

echo "⏳ Esperando a que se complete la actualización..."
aws cloudformation wait stack-update-complete \
    --stack-name $STACK_NAME \
    --region $REGION

echo "✅ Stack actualizado exitosamente con configuración de CORS"
echo ""
echo "🔍 Verifica que el dashboard ahora funcione correctamente"
echo "   URL del dashboard: file://$(pwd)/dashboard/index.html"
