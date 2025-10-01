#!/bin/bash
# Script de despliegue completo del sistema de análisis de incidencias

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir mensajes
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Verificar parámetros
if [ $# -lt 4 ]; then
    log_error "Uso: $0 <stack-name> <environment> <vpc-id> <subnet-ids> [aurora-password]"
    echo ""
    echo "Ejemplo:"
    echo "  $0 incident-analyzer dev vpc-12345 subnet-abc123,subnet-def456 MySecurePassword123"
    exit 1
fi

STACK_NAME=$1
ENVIRONMENT=$2
VPC_ID=$3
SUBNET_IDS=$4
AURORA_PASSWORD=${5:-$(openssl rand -base64 32)}
REGION=${AWS_REGION:-eu-west-1}

log_info "=========================================="
log_info "DESPLIEGUE SISTEMA ANÁLISIS DE INCIDENCIAS"
log_info "=========================================="
log_info "Stack: $STACK_NAME"
log_info "Environment: $ENVIRONMENT"
log_info "Region: $REGION"
log_info "VPC: $VPC_ID"
log_info "Subnets: $SUBNET_IDS"
log_info "=========================================="
echo ""

# Verificar que AWS CLI está instalado
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI no está instalado"
    exit 1
fi

# Verificar que SAM CLI está instalado
if ! command -v sam &> /dev/null; then
    log_error "SAM CLI no está instalado. Instalar con: pip install aws-sam-cli"
    exit 1
fi

# Verificar que jq está instalado
if ! command -v jq &> /dev/null; then
    log_error "jq no está instalado. Instalar con: brew install jq (macOS) o apt-get install jq (Linux)"
    exit 1
fi

# Verificar credenciales AWS
log_step "1/7 Verificando credenciales AWS..."
if ! aws sts get-caller-identity &> /dev/null; then
    log_error "No se pueden obtener credenciales AWS. Ejecuta 'aws configure'"
    exit 1
fi
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
log_info "✓ Cuenta AWS: $ACCOUNT_ID"
echo ""

# Construir el código Lambda
log_step "2/7 Construyendo código Lambda..."
cd "$(dirname "$0")/.."
sam build --template-file infrastructure/incident-analyzer-template.yaml
log_info "✓ Código construido"
echo ""

# Desplegar infraestructura con CloudFormation
log_step "3/7 Desplegando infraestructura con SAM/CloudFormation..."
sam deploy \
    --template-file infrastructure/incident-analyzer-template.yaml \
    --stack-name "$STACK_NAME" \
    --capabilities CAPABILITY_IAM \
    --region "$REGION" \
    --parameter-overrides \
        Environment="$ENVIRONMENT" \
        VpcId="$VPC_ID" \
        PrivateSubnetIds="$SUBNET_IDS" \
        AuroraPassword="$AURORA_PASSWORD" \
    --no-fail-on-empty-changeset

if [ $? -ne 0 ]; then
    log_error "Error desplegando stack CloudFormation"
    exit 1
fi
log_info "✓ Infraestructura desplegada"
echo ""

# Obtener outputs del stack
log_step "4/7 Obteniendo información del stack..."
S3_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`S3BucketName`].OutputValue' \
    --output text)

AURORA_SECRET_ARN=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`AuroraSecretArn`].OutputValue' \
    --output text)

KB_ROLE_ARN=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Resources[?LogicalResourceId==`KnowledgeBaseRole`].PhysicalResourceId' \
    --output text)

API_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
    --output text)

log_info "S3 Bucket: $S3_BUCKET"
log_info "Aurora Secret: $AURORA_SECRET_ARN"
log_info "API Endpoint: $API_ENDPOINT"
echo ""

# Esperar a que Aurora esté disponible
log_step "5/7 Esperando a que Aurora esté disponible..."
log_info "Esto puede tomar varios minutos..."
aws rds wait db-cluster-available \
    --db-cluster-identifier "${STACK_NAME}-aurora-cluster" \
    --region "$REGION"
log_info "✓ Aurora disponible"
echo ""

# Inicializar base de datos
log_step "6/7 Inicializando base de datos Aurora..."
bash scripts/init-aurora-db.sh "$AURORA_SECRET_ARN" "$REGION"
echo ""

# Crear Knowledge Base
log_step "7/7 Creando Knowledge Base en Bedrock..."
bash scripts/create-knowledge-base.sh "$STACK_NAME" "$S3_BUCKET" "$AURORA_SECRET_ARN" "$KB_ROLE_ARN"
echo ""

# Obtener API Key
API_KEY_ID=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiKeyId`].OutputValue' \
    --output text)

API_KEY_VALUE=$(aws apigateway get-api-key \
    --api-key "$API_KEY_ID" \
    --include-value \
    --region "$REGION" \
    --query 'value' \
    --output text)

# Resumen final
log_info "=========================================="
log_info "✓ DESPLIEGUE COMPLETADO EXITOSAMENTE"
log_info "=========================================="
echo ""
log_info "Información del sistema:"
log_info "  - Stack Name: $STACK_NAME"
log_info "  - Environment: $ENVIRONMENT"
log_info "  - Region: $REGION"
log_info "  - API Endpoint: $API_ENDPOINT"
log_info "  - S3 Bucket: $S3_BUCKET"
echo ""
log_info "Credenciales:"
log_info "  - API Key: $API_KEY_VALUE"
log_info "  - Aurora Secret ARN: $AURORA_SECRET_ARN"
echo ""
log_info "Próximos pasos:"
log_info "  1. Subir datos históricos de incidencias a S3:"
log_info "     aws s3 cp incidents-metadata/ s3://$S3_BUCKET/incidents-metadata/ --recursive"
log_info ""
log_info "  2. Sincronizar Knowledge Base:"
log_info "     bash scripts/sync-knowledge-base.sh $STACK_NAME"
log_info ""
log_info "  3. Probar el API:"
log_info "     curl -X POST $API_ENDPOINT/analyze-incident \\"
log_info "       -H 'x-api-key: $API_KEY_VALUE' \\"
log_info "       -H 'Content-Type: application/json' \\"
log_info "       -d '{\"incident_description\": \"Servidor web no responde\"}'"
echo ""
log_info "Para ver logs:"
log_info "  aws logs tail /aws/lambda/${STACK_NAME}-incident-analyzer --follow"
echo ""
