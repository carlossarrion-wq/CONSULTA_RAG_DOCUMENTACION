# Guía de Despliegue - Sistema de Análisis de Incidencias con RAG

## Descripción General

Sistema de análisis inteligente de incidencias que utiliza RAG (Retrieval-Augmented Generation) con AWS Bedrock, Claude Sonnet 4.5, Aurora PostgreSQL con pgvector, y S3 para proporcionar diagnósticos, identificación de causas raíz y recomendaciones basadas en incidencias históricas similares.

## Arquitectura

```
┌─────────────┐
│   Cliente   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│                    API Gateway                          │
│              POST /analyze-incident                     │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              Lambda: Incident Analyzer                  │
│  1. Busca incidencias similares en Knowledge Base       │
│  2. Recupera archivos adjuntos de S3                    │
│  3. Analiza con Claude Sonnet 4.5                       │
└──────┬────────────────────────────┬─────────────────────┘
       │                            │
       ▼                            ▼
┌─────────────────┐        ┌──────────────────┐
│  Bedrock KB     │        │   S3 Bucket      │
│  (Aurora +      │        │  - Metadata      │
│   pgvector)     │        │  - Files         │
└─────────────────┘        └──────────────────┘
```

## Componentes Principales

### 1. AWS Bedrock Knowledge Base
- **Modelo de Embeddings**: Amazon Titan Embeddings v2 (1024 dimensiones)
- **Modelo de Análisis**: Claude Sonnet 4.5 (eu.anthropic.claude-sonnet-4-5-20250929-v1:0)
- **Storage**: Aurora PostgreSQL 15.4 con extensión pgvector
- **Búsqueda**: Híbrida (semántica + keyword)

### 2. Aurora PostgreSQL Serverless v2
- **Configuración**: 0.5 - 2 ACUs
- **Extensión**: pgvector para búsqueda vectorial
- **Índices**: IVFFlat para embeddings, GIN para metadata JSONB
- **Costo estimado**: ~$321/mes

### 3. Lambda Functions
- **Runtime**: Python 3.11
- **Memoria**: 2048 MB
- **Timeout**: 300 segundos
- **VPC**: Conectada a Aurora en subnets privadas

### 4. S3 Bucket
- **Estructura**:
  - `incidents-metadata/`: Archivos JSON con metadata (sincronizados con KB)
  - `incidents-files/`: Archivos adjuntos (PDFs, imágenes, logs)
- **Encriptación**: AES256
- **Versionado**: Habilitado

## Requisitos Previos

### Software Necesario
```bash
# AWS CLI
aws --version  # >= 2.0

# SAM CLI
sam --version  # >= 1.100

# Python
python3 --version  # >= 3.11

# PostgreSQL client (para init-aurora-db.sh)
psql --version  # >= 15

# jq (para procesamiento JSON)
jq --version  # >= 1.6
```

### Configuración AWS
```bash
# Configurar credenciales
aws configure

# Verificar acceso
aws sts get-caller-identity

# Verificar acceso a Bedrock
aws bedrock list-foundation-models --region eu-west-1
```

### Información de Red
Necesitarás:
- **VPC ID**: ID de la VPC donde desplegar
- **Subnet IDs**: Al menos 2 subnets privadas en diferentes AZs
- **Security Groups**: Se crearán automáticamente

## Proceso de Despliegue

### Paso 1: Clonar y Preparar el Proyecto

```bash
# Clonar repositorio
git clone <repository-url>
cd CONSULTA_RAG_DOCUMENTACION

# Dar permisos de ejecución a scripts
chmod +x scripts/*.sh
chmod +x scripts/*.py

# Instalar dependencias de desarrollo (opcional)
pip install -r requirements.txt
```

### Paso 2: Despliegue Completo Automatizado

```bash
# Ejecutar script de despliegue completo
./scripts/deploy-complete.sh \
  incident-analyzer \
  dev \
  vpc-xxxxx \
  subnet-xxxxx,subnet-yyyyy \
  MySecurePassword123

# Parámetros:
# 1. Stack name
# 2. Environment (dev/staging/prod)
# 3. VPC ID
# 4. Subnet IDs (separados por coma)
# 5. Aurora password (opcional, se genera automáticamente si no se proporciona)
```

El script ejecutará automáticamente:
1. ✓ Verificación de credenciales AWS
2. ✓ Build del código Lambda con SAM
3. ✓ Despliegue de infraestructura (CloudFormation)
4. ✓ Espera a que Aurora esté disponible
5. ✓ Inicialización de base de datos con pgvector
6. ✓ Creación de Knowledge Base en Bedrock
7. ✓ Configuración de Data Source para S3

### Paso 3: Generar y Subir Datos de Ejemplo

```bash
# Generar datos de ejemplo
python3 scripts/generate-sample-data.py

# Subir a S3 (reemplazar YOUR-BUCKET con el nombre real)
S3_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name incident-analyzer \
  --query 'Stacks[0].Outputs[?OutputKey==`S3BucketName`].OutputValue' \
  --output text)

aws s3 cp sample-data/incidents-metadata/ \
  s3://$S3_BUCKET/incidents-metadata/ --recursive

aws s3 cp sample-data/incidents-files/ \
  s3://$S3_BUCKET/incidents-files/ --recursive
```

### Paso 4: Sincronizar Knowledge Base

```bash
# Sincronizar datos con Knowledge Base
./scripts/sync-knowledge-base.sh incident-analyzer

# Esto iniciará un ingestion job y esperará a que complete
# Puede tomar varios minutos dependiendo del volumen de datos
```

### Paso 5: Verificar Despliegue

```bash
# Obtener información del stack
aws cloudformation describe-stacks \
  --stack-name incident-analyzer \
  --query 'Stacks[0].Outputs'

# Verificar Lambda
aws lambda get-function \
  --function-name incident-analyzer-incident-analyzer

# Verificar Aurora
aws rds describe-db-clusters \
  --db-cluster-identifier incident-analyzer-aurora-cluster

# Ver estadísticas de la Knowledge Base
KB_ID=$(aws ssm get-parameter \
  --name /incident-analyzer/knowledge-base-id \
  --query 'Parameter.Value' \
  --output text)

aws bedrock-agent get-knowledge-base \
  --knowledge-base-id $KB_ID
```

## Uso del Sistema

### Obtener API Key

```bash
# Obtener API Key
API_KEY_ID=$(aws cloudformation describe-stacks \
  --stack-name incident-analyzer \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiKeyId`].OutputValue' \
  --output text)

API_KEY=$(aws apigateway get-api-key \
  --api-key $API_KEY_ID \
  --include-value \
  --query 'value' \
  --output text)

echo "API Key: $API_KEY"
```

### Ejemplo de Consulta

```bash
# Obtener endpoint
API_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name incident-analyzer \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text)

# Analizar incidencia
curl -X POST $API_ENDPOINT/analyze-incident \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "incident_description": "El servidor web no responde y los usuarios reportan error 503",
    "max_similar_incidents": 5,
    "include_attachments": true
  }'
```

### Respuesta Esperada

```json
{
  "diagnosis": "El problema parece ser una falla en el servicio web...",
  "root_cause": "Posible fuga de memoria o sobrecarga del servidor",
  "recommended_actions": [
    "Verificar el uso de memoria del servidor",
    "Revisar logs de nginx/apache",
    "Reiniciar el servicio web si es necesario",
    "Aumentar recursos si el problema persiste"
  ],
  "confidence_score": 0.85,
  "similar_incidents": [
    {
      "incident_id": "INC-2024-001",
      "title": "Servidor web no responde",
      "similarity_score": 0.92,
      "resolution": "Se reinició el servicio nginx...",
      "attachments": ["INC-2024-001_logs.txt", "INC-2024-001_screenshot.png"]
    }
  ],
  "model_info": {
    "model_id": "eu.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "input_tokens": 1250,
    "output_tokens": 450,
    "total_tokens": 1700
  }
}
```

## Monitoreo y Logs

### Ver Logs de Lambda

```bash
# Logs en tiempo real
aws logs tail /aws/lambda/incident-analyzer-incident-analyzer --follow

# Logs de las últimas 2 horas
aws logs tail /aws/lambda/incident-analyzer-incident-analyzer \
  --since 2h \
  --format short
```

### Métricas de CloudWatch

```bash
# Errores de Lambda
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=incident-analyzer-incident-analyzer \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum

# Latencia de API Gateway
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Latency \
  --dimensions Name=ApiName,Value=incident-analyzer-api \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

### Estadísticas de Aurora

```bash
# Conectar a Aurora
AURORA_SECRET_ARN=$(aws cloudformation describe-stacks \
  --stack-name incident-analyzer \
  --query 'Stacks[0].Outputs[?OutputKey==`AuroraSecretArn`].OutputValue' \
  --output text)

# Obtener credenciales
CREDS=$(aws secretsmanager get-secret-value \
  --secret-id $AURORA_SECRET_ARN \
  --query 'SecretString' \
  --output text)

HOST=$(echo $CREDS | jq -r '.host')
PORT=$(echo $CREDS | jq -r '.port')
USER=$(echo $CREDS | jq -r '.username')
DB=$(echo $CREDS | jq -r '.dbname')

# Ver estadísticas
PGPASSWORD=$(echo $CREDS | jq -r '.password') \
psql -h $HOST -p $PORT -U $USER -d $DB \
  -c "SELECT * FROM incidents_kb_stats;"
```

## Mantenimiento

### Actualizar Código Lambda

```bash
# Modificar código en src/incident_analyzer/

# Rebuild y redeploy
sam build --template-file infrastructure/incident-analyzer-template.yaml
sam deploy --stack-name incident-analyzer --no-confirm-changeset
```

### Agregar Nuevas Incidencias

```bash
# 1. Crear archivo JSON de metadata
cat > new-incident.json <<EOF
{
  "incident_id": "INC-2024-009",
  "title": "Nueva incidencia",
  "description": "Descripción detallada...",
  "resolution": "Cómo se resolvió...",
  "category": "Infrastructure",
  "severity": "High"
}
EOF

# 2. Subir a S3
aws s3 cp new-incident.json \
  s3://$S3_BUCKET/incidents-metadata/INC-2024-009_metadata.json

# 3. Sincronizar Knowledge Base
./scripts/sync-knowledge-base.sh incident-analyzer
```

### Backup y Recuperación

```bash
# Backup manual de Aurora
aws rds create-db-cluster-snapshot \
  --db-cluster-identifier incident-analyzer-aurora-cluster \
  --db-cluster-snapshot-identifier incident-analyzer-backup-$(date +%Y%m%d)

# Listar backups
aws rds describe-db-cluster-snapshots \
  --db-cluster-identifier incident-analyzer-aurora-cluster

# Restaurar desde backup (crear nuevo cluster)
aws rds restore-db-cluster-from-snapshot \
  --db-cluster-identifier incident-analyzer-aurora-restored \
  --snapshot-identifier incident-analyzer-backup-20240101 \
  --engine aurora-postgresql
```

## Costos Estimados

### Desglose Mensual (uso moderado)

| Componente | Costo Mensual |
|------------|---------------|
| Aurora Serverless v2 (0.5-2 ACU) | $321 |
| Lambda (100K invocaciones/mes) | $20 |
| API Gateway (100K requests) | $3.50 |
| S3 (100GB storage + requests) | $25 |
| Bedrock Claude Sonnet 4.5 | $30-50 |
| Bedrock Knowledge Base | $10 |
| **TOTAL** | **~$410/mes** |

### Optimización de Costos

1. **Aurora**: Usar auto-scaling para ajustar ACUs según demanda
2. **Lambda**: Optimizar memoria y timeout
3. **S3**: Implementar lifecycle policies para archivos antiguos
4. **Bedrock**: Cachear respuestas frecuentes

## Troubleshooting

### Lambda Timeout

```bash
# Aumentar timeout
aws lambda update-function-configuration \
  --function-name incident-analyzer-incident-analyzer \
  --timeout 600
```

### Aurora Connection Issues

```bash
# Verificar security groups
aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=incident-analyzer-aurora-sg"

# Verificar que Lambda está en la VPC correcta
aws lambda get-function-configuration \
  --function-name incident-analyzer-incident-analyzer \
  --query 'VpcConfig'
```

### Knowledge Base No Encuentra Resultados

```bash
# Verificar que hay datos
aws bedrock-agent list-data-sources \
  --knowledge-base-id $KB_ID

# Forzar re-sincronización
./scripts/sync-knowledge-base.sh incident-analyzer
```

## Limpieza

### Eliminar Stack Completo

```bash
# ADVERTENCIA: Esto eliminará todos los recursos

# 1. Eliminar Knowledge Base
KB_ID=$(aws ssm get-parameter \
  --name /incident-analyzer/knowledge-base-id \
  --query 'Parameter.Value' \
  --output text)

aws bedrock-agent delete-knowledge-base \
  --knowledge-base-id $KB_ID

# 2. Vaciar bucket S3
aws s3 rm s3://$S3_BUCKET --recursive

# 3. Eliminar stack CloudFormation
aws cloudformation delete-stack --stack-name incident-analyzer

# 4. Esperar a que complete
aws cloudformation wait stack-delete-complete \
  --stack-name incident-analyzer
```

## Soporte y Contacto

Para problemas o preguntas:
- Revisar logs de CloudWatch
- Verificar documentación de arquitectura en `ARQUITECTURA_SISTEMA_INCIDENCIAS.md`
- Consultar guía de Aurora en `ARQUITECTURA_AURORA_PGVECTOR.md`

## Referencias

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Aurora PostgreSQL with pgvector](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraPostgreSQL.VectorDB.html)
- [Claude API Reference](https://docs.anthropic.com/claude/reference)
- [SAM CLI Documentation](https://docs.aws.amazon.com/serverless-application-model/)
