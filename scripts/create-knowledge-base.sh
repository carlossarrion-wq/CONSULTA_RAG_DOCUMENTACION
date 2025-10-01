#!/bin/bash
# Script para crear la Knowledge Base en AWS Bedrock

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Verificar parámetros
if [ $# -lt 4 ]; then
    log_error "Uso: $0 <stack-name> <s3-bucket> <aurora-secret-arn> <kb-role-arn>"
    exit 1
fi

STACK_NAME=$1
S3_BUCKET=$2
AURORA_SECRET_ARN=$3
KB_ROLE_ARN=$4
REGION=${AWS_REGION:-eu-west-1}

log_info "Creando Knowledge Base para stack: $STACK_NAME"
log_info "Región: $REGION"
log_info "S3 Bucket: $S3_BUCKET"

# Obtener credenciales de Aurora desde Secrets Manager
log_info "Obteniendo credenciales de Aurora..."
AURORA_CREDS=$(aws secretsmanager get-secret-value \
    --secret-id "$AURORA_SECRET_ARN" \
    --region "$REGION" \
    --query 'SecretString' \
    --output text)

AURORA_HOST=$(echo "$AURORA_CREDS" | jq -r '.host')
AURORA_PORT=$(echo "$AURORA_CREDS" | jq -r '.port')
AURORA_DB=$(echo "$AURORA_CREDS" | jq -r '.dbname')
AURORA_USER=$(echo "$AURORA_CREDS" | jq -r '.username')

log_info "Aurora endpoint: $AURORA_HOST:$AURORA_PORT"

# Obtener el identificador real del cluster Aurora
log_info "Obteniendo identificador del cluster Aurora..."
AURORA_CLUSTER_ID=$(aws rds describe-db-clusters \
    --region "$REGION" \
    --query "DBClusters[?Endpoint=='${AURORA_HOST}'].DBClusterIdentifier" \
    --output text)

if [ -z "$AURORA_CLUSTER_ID" ]; then
    log_error "No se pudo obtener el identificador del cluster Aurora"
    exit 1
fi

log_info "Cluster Aurora ID: $AURORA_CLUSTER_ID"

# Obtener Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Crear configuración de la Knowledge Base
KB_CONFIG=$(cat <<EOF
{
  "name": "${STACK_NAME}-incidents-kb",
  "description": "Knowledge Base para análisis de incidencias con RAG",
  "roleArn": "${KB_ROLE_ARN}",
  "knowledgeBaseConfiguration": {
    "type": "VECTOR",
    "vectorKnowledgeBaseConfiguration": {
      "embeddingModelArn": "arn:aws:bedrock:${REGION}::foundation-model/amazon.titan-embed-text-v2:0"
    }
  },
  "storageConfiguration": {
    "type": "RDS",
    "rdsConfiguration": {
      "resourceArn": "arn:aws:rds:${REGION}:${ACCOUNT_ID}:cluster:${AURORA_CLUSTER_ID}",
      "credentialsSecretArn": "${AURORA_SECRET_ARN}",
      "databaseName": "${AURORA_DB}",
      "tableName": "incidents_knowledge_base_embeddings",
      "fieldMapping": {
        "primaryKeyField": "id",
        "vectorField": "embedding",
        "textField": "text_chunk",
        "metadataField": "metadata"
      }
    }
  }
}
EOF
)

# Crear Knowledge Base
log_info "Creando Knowledge Base..."
KB_RESPONSE=$(aws bedrock-agent create-knowledge-base \
    --region "$REGION" \
    --cli-input-json "$KB_CONFIG")

KB_ID=$(echo "$KB_RESPONSE" | jq -r '.knowledgeBase.knowledgeBaseId')

if [ -z "$KB_ID" ] || [ "$KB_ID" == "null" ]; then
    log_error "Error creando Knowledge Base"
    exit 1
fi

log_info "Knowledge Base creada con ID: $KB_ID"

# Guardar KB ID en Parameter Store
log_info "Guardando KB ID en Parameter Store..."
aws ssm put-parameter \
    --name "/${STACK_NAME}/knowledge-base-id" \
    --value "$KB_ID" \
    --type "String" \
    --overwrite \
    --region "$REGION"

# Crear Data Source para S3
log_info "Creando Data Source para S3..."
DS_CONFIG=$(cat <<EOF
{
  "name": "${STACK_NAME}-incidents-datasource",
  "description": "Data source para metadatos de incidencias",
  "knowledgeBaseId": "${KB_ID}",
  "dataSourceConfiguration": {
    "type": "S3",
    "s3Configuration": {
      "bucketArn": "arn:aws:s3:::${S3_BUCKET}",
      "inclusionPrefixes": ["incidents-metadata/"]
    }
  },
  "vectorIngestionConfiguration": {
    "chunkingConfiguration": {
      "chunkingStrategy": "FIXED_SIZE",
      "fixedSizeChunkingConfiguration": {
        "maxTokens": 512,
        "overlapPercentage": 20
      }
    }
  }
}
EOF
)

DS_RESPONSE=$(aws bedrock-agent create-data-source \
    --region "$REGION" \
    --cli-input-json "$DS_CONFIG")

DS_ID=$(echo "$DS_RESPONSE" | jq -r '.dataSource.dataSourceId')

log_info "Data Source creado con ID: $DS_ID"

# Guardar DS ID en Parameter Store
aws ssm put-parameter \
    --name "/${STACK_NAME}/data-source-id" \
    --value "$DS_ID" \
    --type "String" \
    --overwrite \
    --region "$REGION"

log_info "✓ Knowledge Base configurada exitosamente"
log_info ""
log_info "Resumen:"
log_info "  - Knowledge Base ID: $KB_ID"
log_info "  - Data Source ID: $DS_ID"
log_info "  - Embedding Model: Amazon Titan Embeddings v2"
log_info "  - Storage: Aurora PostgreSQL con pgvector"
log_info ""
log_info "Siguiente paso: Ejecutar init-aurora-db.sh para inicializar la base de datos"
