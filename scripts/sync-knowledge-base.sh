#!/bin/bash
# Script para sincronizar la Knowledge Base con los datos en S3

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Verificar parámetros
if [ $# -lt 1 ]; then
    log_error "Uso: $0 <stack-name> [region]"
    exit 1
fi

STACK_NAME=$1
REGION=${2:-${AWS_REGION:-eu-west-1}}

log_info "Sincronizando Knowledge Base"
log_info "Stack: $STACK_NAME"
log_info "Región: $REGION"

# Obtener Knowledge Base ID y Data Source ID
KB_ID=$(aws ssm get-parameter \
    --name "/${STACK_NAME}/knowledge-base-id" \
    --region "$REGION" \
    --query 'Parameter.Value' \
    --output text 2>/dev/null)

if [ -z "$KB_ID" ] || [ "$KB_ID" == "None" ]; then
    log_error "No se encontró Knowledge Base ID en Parameter Store"
    log_error "Asegúrate de haber ejecutado create-knowledge-base.sh primero"
    exit 1
fi

DS_ID=$(aws ssm get-parameter \
    --name "/${STACK_NAME}/data-source-id" \
    --region "$REGION" \
    --query 'Parameter.Value' \
    --output text 2>/dev/null)

if [ -z "$DS_ID" ] || [ "$DS_ID" == "None" ]; then
    log_error "No se encontró Data Source ID en Parameter Store"
    exit 1
fi

log_info "Knowledge Base ID: $KB_ID"
log_info "Data Source ID: $DS_ID"

# Iniciar ingestion job
log_info "Iniciando sincronización..."
INGESTION_RESPONSE=$(aws bedrock-agent start-ingestion-job \
    --knowledge-base-id "$KB_ID" \
    --data-source-id "$DS_ID" \
    --region "$REGION")

INGESTION_JOB_ID=$(echo "$INGESTION_RESPONSE" | jq -r '.ingestionJob.ingestionJobId')

log_info "Ingestion Job iniciado: $INGESTION_JOB_ID"
log_info "Esperando a que complete..."

# Esperar a que complete
while true; do
    STATUS=$(aws bedrock-agent get-ingestion-job \
        --knowledge-base-id "$KB_ID" \
        --data-source-id "$DS_ID" \
        --ingestion-job-id "$INGESTION_JOB_ID" \
        --region "$REGION" \
        --query 'ingestionJob.status' \
        --output text)
    
    if [ "$STATUS" == "COMPLETE" ]; then
        log_info "✓ Sincronización completada exitosamente"
        
        # Obtener estadísticas
        STATS=$(aws bedrock-agent get-ingestion-job \
            --knowledge-base-id "$KB_ID" \
            --data-source-id "$DS_ID" \
            --ingestion-job-id "$INGESTION_JOB_ID" \
            --region "$REGION" \
            --query 'ingestionJob.statistics' \
            --output json)
        
        echo ""
        log_info "Estadísticas de ingestion:"
        echo "$STATS" | jq '.'
        break
    elif [ "$STATUS" == "FAILED" ]; then
        log_error "La sincronización falló"
        
        # Obtener detalles del error
        FAILURE=$(aws bedrock-agent get-ingestion-job \
            --knowledge-base-id "$KB_ID" \
            --data-source-id "$DS_ID" \
            --ingestion-job-id "$INGESTION_JOB_ID" \
            --region "$REGION" \
            --query 'ingestionJob.failureReasons' \
            --output json)
        
        echo ""
        log_error "Razones del fallo:"
        echo "$FAILURE" | jq '.'
        exit 1
    else
        echo -n "."
        sleep 10
    fi
done

echo ""
log_info "Knowledge Base sincronizada y lista para usar"
