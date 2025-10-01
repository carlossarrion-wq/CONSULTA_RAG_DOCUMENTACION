#!/bin/bash

# Script de despliegue para Lambda con AWS SAM

set -e

echo "=========================================="
echo "Despliegue de Consulta RAG Bedrock Lambda"
echo "=========================================="

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar que SAM CLI está instalado
if ! command -v sam &> /dev/null; then
    echo -e "${RED}Error: AWS SAM CLI no está instalado${NC}"
    echo "Instala SAM CLI: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html"
    exit 1
fi

# Verificar que AWS CLI está configurado
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}Error: AWS CLI no está configurado correctamente${NC}"
    echo "Configura AWS CLI con: aws configure"
    exit 1
fi

echo -e "${GREEN}✓ Verificaciones completadas${NC}"

# Parámetros
STACK_NAME="${STACK_NAME:-consulta-rag-bedrock}"
REGION="${AWS_REGION:-eu-west-1}"
S3_BUCKET="${S3_BUCKET:-}"

echo ""
echo "Configuración:"
echo "  Stack Name: $STACK_NAME"
echo "  Region: $REGION"

# Si no se proporciona bucket S3, crear uno
if [ -z "$S3_BUCKET" ]; then
    S3_BUCKET="sam-deploy-$STACK_NAME-$(date +%s)"
    echo -e "${YELLOW}  S3 Bucket: $S3_BUCKET (se creará)${NC}"
    
    echo ""
    echo "Creando bucket S3..."
    aws s3 mb s3://$S3_BUCKET --region $REGION
else
    echo "  S3 Bucket: $S3_BUCKET"
fi

echo ""
echo "=========================================="
echo "Paso 1: Instalando dependencias"
echo "=========================================="

# Instalar dependencias en el directorio src
cd ../src/lambda
pip install -r requirements.txt -t .
cd ../../infrastructure

echo -e "${GREEN}✓ Dependencias instaladas${NC}"

echo ""
echo "=========================================="
echo "Paso 2: Construyendo aplicación SAM"
echo "=========================================="

sam build --template-file template.yaml

echo -e "${GREEN}✓ Aplicación construida${NC}"

echo ""
echo "=========================================="
echo "Paso 3: Desplegando a AWS"
echo "=========================================="

sam deploy \
    --template-file .aws-sam/build/template.yaml \
    --stack-name $STACK_NAME \
    --s3-bucket $S3_BUCKET \
    --region $REGION \
    --capabilities CAPABILITY_IAM \
    --no-confirm-changeset \
    --no-fail-on-empty-changeset

echo -e "${GREEN}✓ Despliegue completado${NC}"

echo ""
echo "=========================================="
echo "Información del despliegue"
echo "=========================================="

# Obtener outputs del stack
API_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`ConsultaRAGApi`].OutputValue' \
    --output text)

FUNCTION_ARN=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`ConsultaRAGFunction`].OutputValue' \
    --output text)

echo ""
echo -e "${GREEN}API Endpoint:${NC} $API_URL"
echo -e "${GREEN}Lambda ARN:${NC} $FUNCTION_ARN"

echo ""
echo "=========================================="
echo "Prueba la API con:"
echo "=========================================="
echo ""
echo "curl -X POST $API_URL \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"prompt\": \"Hola, ¿cómo estás?\"}'"
echo ""

echo -e "${GREEN}✓ Despliegue exitoso${NC}"
