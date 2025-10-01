# Arquitectura con Aurora PostgreSQL y pgvector

## 📋 Configuración de Knowledge Base Existente

Basado en tu KB piloto: `piloto-plan-pruebas-e2e-rag-knowledgebase-pgvector`

### Especificaciones Actuales

```yaml
Knowledge Base ID: VH6SRH9ZNO
Nombre: piloto-plan-pruebas-e2e-rag-knowledgebase-pgvector
Estado: ACTIVE
Región: eu-west-1

Embedding Model:
  Modelo: amazon.titan-embed-text-v2:0
  Dimensiones: 1024
  Tipo de datos: FLOAT32

Vector Store:
  Tipo: Amazon Aurora PostgreSQL
  Cluster: piloto-plan-pruebas-aurora-cluster
  Base de datos: pgvectordb
  Tabla: piloto_plan_pruebas_knowledge_base_embeddings
  
  Campos:
    - id (PRIMARY KEY)
    - embedding (VECTOR)
    - text_chunk (TEXT)
    - metadata (JSONB)

Data Source:
  Tipo: S3
  Bucket: s3://piloto-plan-pruebas-origen-datos-source

Secrets Manager:
  Credenciales: piloto-plan-pruebas-aurora-credentials
```

## 🏗️ Arquitectura Adaptada para Sistema de Incidencias

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              USUARIO/CLIENTE                             │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             │ POST /analyze-incident
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           API GATEWAY                                    │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    LAMBDA: Incident Analyzer                             │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ 1. Recibe descripción de incidencia                               │  │
│  │ 2. Consulta Bedrock Knowledge Base (con Aurora)                   │  │
│  │ 3. Obtiene incidencias similares                                  │  │
│  │ 4. Recupera archivos adjuntos de S3                               │  │
│  │ 5. Invoca Claude Sonnet 4.5                                       │  │
│  │ 6. Retorna diagnóstico y recomendaciones                          │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└──────┬──────────────────┬──────────────────┬────────────────────────────┘
       │                  │                  │
       │                  │                  │
       ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐
│   BEDROCK    │  │   BEDROCK    │  │      S3 BUCKETS          │
│  KNOWLEDGE   │  │    CLAUDE    │  │                          │
│     BASE     │  │  SONNET 4.5  │  │  ┌────────────────────┐  │
│              │  │              │  │  │ incidents-kb-      │  │
│  - Retrieve  │  │  - Análisis  │  │  │   source/          │  │
│  - RAG       │  │  - Diagnóstico│ │  │  (Data Source)     │  │
│              │  │  - Recomend. │  │  └────────────────────┘  │
└──────┬───────┘  └──────────────┘  │                          │
       │                             │  ┌────────────────────┐  │
       │                             │  │ incidents-files/   │  │
       │                             │  │  (Attachments)     │  │
       │                             │  └────────────────────┘  │
       │                             └──────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│              AMAZON AURORA POSTGRESQL (pgvector)                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Cluster: incidents-aurora-cluster                          │ │
│  │ Database: incidents_pgvectordb                             │ │
│  │                                                            │ │
│  │ Tabla: incidents_knowledge_base_embeddings                 │ │
│  │ ┌────────────────────────────────────────────────────────┐ │ │
│  │ │ id          | UUID (PRIMARY KEY)                       │ │ │
│  │ │ embedding   | VECTOR(1024)                             │ │ │
│  │ │ text_chunk  | TEXT                                     │ │ │
│  │ │ metadata    | JSONB                                    │ │ │
│  │ │             | {                                        │ │ │
│  │ │             |   "incident_id": "INC-2024-001",         │ │ │
│  │ │             |   "category": "infrastructure",          │ │ │
│  │ │             |   "severity": "high",                    │ │ │
│  │ │             |   "root_cause": "...",                   │ │ │
│  │ │             |   "attachments": [...]                   │ │ │
│  │ │             | }                                        │ │ │
│  │ └────────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  Índices:                                                        │
│  - CREATE INDEX ON embeddings USING ivfflat (embedding          │
│    vector_cosine_ops) WITH (lists = 100);                       │
│                                                                  │
│  Configuración:                                                  │
│  - Instance: db.r6g.xlarge (4 vCPU, 32 GB RAM)                  │
│  - Storage: 100 GB SSD                                           │
│  - Multi-AZ: Enabled                                             │
│  - Backup: 7 días                                                │
└─────────────────────────────────────────────────────────────────┘
```

## 🔧 Configuración Detallada

### 1. Aurora PostgreSQL Cluster

**Especificaciones Recomendadas**:
```yaml
Cluster Name: incidents-aurora-cluster
Engine: Aurora PostgreSQL 15.4
Instance Class: db.r6g.xlarge
  - vCPUs: 4
  - RAM: 32 GB
  - Network: Up to 10 Gbps

Storage:
  - Type: Aurora Storage (auto-scaling)
  - Initial: 100 GB
  - Max: 128 TB (auto-scaling)
  - IOPS: Provisioned based on storage

High Availability:
  - Multi-AZ: Yes
  - Read Replicas: 1-2 (opcional)
  - Automatic Failover: < 30 segundos

Backup:
  - Automated Backups: 7 días
  - Backup Window: 03:00-04:00 UTC
  - Point-in-Time Recovery: Enabled

Security:
  - VPC: Private subnets
  - Security Group: Restringido a Lambda
  - Encryption at Rest: AWS KMS
  - Encryption in Transit: SSL/TLS
```

### 2. Extensión pgvector

**Instalación y Configuración**:
```sql
-- Conectar a la base de datos
\c incidents_pgvectordb

-- Instalar extensión pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Crear tabla de embeddings
CREATE TABLE incidents_knowledge_base_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    embedding VECTOR(1024),
    text_chunk TEXT NOT NULL,
    metadata JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Crear índice IVFFlat para búsqueda rápida
-- lists = sqrt(num_rows) es una buena heurística
CREATE INDEX ON incidents_knowledge_base_embeddings 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- Índice en metadata para filtros
CREATE INDEX idx_metadata_incident_id ON incidents_knowledge_base_embeddings 
USING gin ((metadata->'incident_id'));

CREATE INDEX idx_metadata_category ON incidents_knowledge_base_embeddings 
USING gin ((metadata->'category'));

CREATE INDEX idx_metadata_severity ON incidents_knowledge_base_embeddings 
USING gin ((metadata->'severity'));

-- Función para actualizar updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_embeddings_updated_at 
BEFORE UPDATE ON incidents_knowledge_base_embeddings
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### 3. Estructura de Metadata en JSONB

```json
{
  "incident_id": "INC-2024-001",
  "title": "Servidor web no responde",
  "description": "El servidor web principal no responde en el puerto 443",
  "category": "infrastructure",
  "severity": "high",
  "reported_date": "2024-09-15T10:30:00Z",
  "resolved_date": "2024-09-15T11:00:00Z",
  "resolution_time_minutes": 30,
  "root_cause": "Certificado SSL expirado",
  "resolution": "Se renovó el certificado SSL usando certbot",
  "resolution_steps": [
    "Verificar estado del certificado",
    "Renovar certificado con certbot",
    "Reiniciar nginx"
  ],
  "tags": ["ssl", "certificate", "web-server", "nginx"],
  "attachments_metadata": [
    {
      "file_name": "error_log.txt",
      "file_type": "log",
      "description": "Log de errores del servidor nginx",
      "summary": "Múltiples errores SSL_ERROR_EXPIRED_CERT_ALERT",
      "s3_path": "s3://incidents-files/INC-2024-001/error_log.txt",
      "size_bytes": 15420
    }
  ],
  "source_system": "ServiceNow",
  "source_id": "INC0012345"
}
```

### 4. Bedrock Knowledge Base Configuration

**CloudFormation/Terraform**:
```yaml
IncidentsKnowledgeBase:
  Type: AWS::Bedrock::KnowledgeBase
  Properties:
    Name: incidents-knowledge-base-pgvector
    RoleArn: !GetAtt KnowledgeBaseRole.Arn
    KnowledgeBaseConfiguration:
      Type: VECTOR
      VectorKnowledgeBaseConfiguration:
        EmbeddingModelArn: !Sub 'arn:aws:bedrock:${AWS::Region}::foundation-model/amazon.titan-embed-text-v2:0'
        EmbeddingModelConfiguration:
          BedrockEmbeddingModelConfiguration:
            Dimensions: 1024
            EmbeddingDataType: FLOAT32
    StorageConfiguration:
      Type: RDS
      RdsConfiguration:
        ResourceArn: !GetAtt AuroraCluster.ClusterArn
        CredentialsSecretArn: !Ref AuroraSecret
        DatabaseName: incidents_pgvectordb
        TableName: incidents_knowledge_base_embeddings
        FieldMapping:
          PrimaryKeyField: id
          VectorField: embedding
          TextField: text_chunk
          MetadataField: metadata

IncidentsDataSource:
  Type: AWS::Bedrock::DataSource
  Properties:
    KnowledgeBaseId: !Ref IncidentsKnowledgeBase
    Name: incidents-s3-datasource
    DataSourceConfiguration:
      Type: S3
      S3Configuration:
        BucketArn: !GetAtt IncidentsKBSourceBucket.Arn
    VectorIngestionConfiguration:
      ChunkingConfiguration:
        ChunkingStrategy: FIXED_SIZE
        FixedSizeChunkingConfiguration:
          MaxTokens: 500
          OverlapPercentage: 10
```

### 5. Secrets Manager para Credenciales

```json
{
  "username": "incidents_admin",
  "password": "<GENERATED_PASSWORD>",
  "engine": "postgres",
  "host": "incidents-aurora-cluster.cluster-xxxxx.eu-west-1.rds.amazonaws.com",
  "port": 5432,
  "dbname": "incidents_pgvectordb"
}
```

## 💰 Estimación de Costos con Aurora

### Escenario: 10,000 consultas/mes, 50,000 incidencias indexadas

| Componente | Especificación | Costo Mensual |
|------------|----------------|---------------|
| **Aurora PostgreSQL** | db.r6g.xlarge (4 vCPU, 32GB) | $292.00 |
| Storage | 100 GB | $10.00 |
| Backup Storage | 100 GB | $9.50 |
| I/O Operations | ~1M requests | $10.00 |
| **Subtotal Aurora** | | **$321.50** |
| | | |
| API Gateway | 10,000 requests | $0.04 |
| Lambda | 10,000 × 5s × 2GB | $1.67 |
| Bedrock KB Queries | 10,000 queries | $10.00 |
| Bedrock Claude 4.5 | ~25M tokens | $75.00 |
| S3 Storage | 100GB | $2.30 |
| S3 Requests | 50,000 GET | $0.02 |
| Secrets Manager | 1 secret | $0.40 |
| **TOTAL** | | **~$411/mes** |

**Ahorro vs OpenSearch Serverless**: ~$378/mes (48% más económico)

## 🚀 Ventajas de Aurora PostgreSQL con pgvector

### 1. **Costo-Efectivo**
- ✅ $321/mes vs $700/mes de OpenSearch Serverless
- ✅ Ahorro del 54% en vector store
- ✅ Sin costos de OCU (OpenSearch Compute Units)

### 2. **Familiar y Estándar**
- ✅ PostgreSQL es ampliamente conocido
- ✅ SQL estándar para queries
- ✅ Herramientas de administración maduras

### 3. **Integración Nativa**
- ✅ Soporte nativo de Bedrock Knowledge Base
- ✅ No requiere código custom para búsqueda vectorial
- ✅ Gestión automática de embeddings

### 4. **Escalabilidad**
- ✅ Auto-scaling de storage (hasta 128 TB)
- ✅ Read replicas para alta disponibilidad
- ✅ Failover automático < 30 segundos

### 5. **Flexibilidad**
- ✅ Queries SQL complejas sobre metadata
- ✅ Joins con otras tablas si es necesario
- ✅ Índices adicionales para optimización

## 📊 Comparativa: Aurora vs OpenSearch Serverless

| Característica | Aurora PostgreSQL | OpenSearch Serverless |
|----------------|-------------------|----------------------|
| **Costo mensual** | ~$321 | ~$700 |
| **Gestión** | Managed (menos que RDS) | Fully Managed |
| **Escalabilidad** | Auto-scaling storage | Auto-scaling compute |
| **Query Language** | SQL + pgvector | OpenSearch DSL |
| **Backup** | Automático (7-35 días) | Automático |
| **Multi-AZ** | Sí | Sí |
| **Latencia búsqueda** | < 100ms | < 50ms |
| **Complejidad setup** | Media | Baja |
| **Integración Bedrock** | Nativa | Nativa |

## 🔄 Proceso de Migración desde tu KB Piloto

### Paso 1: Crear Nueva Aurora Cluster

```bash
# Usar configuración similar a piloto-plan-pruebas-aurora-cluster
aws rds create-db-cluster \
  --db-cluster-identifier incidents-aurora-cluster \
  --engine aurora-postgresql \
  --engine-version 15.4 \
  --master-username incidents_admin \
  --master-user-password <PASSWORD> \
  --database-name incidents_pgvectordb \
  --vpc-security-group-ids sg-xxxxx \
  --db-subnet-group-name incidents-subnet-group \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00" \
  --preferred-maintenance-window "mon:04:00-mon:05:00" \
  --enable-cloudwatch-logs-exports '["postgresql"]' \
  --storage-encrypted \
  --kms-key-id <KMS_KEY_ID>
```

### Paso 2: Crear Instancia

```bash
aws rds create-db-instance \
  --db-instance-identifier incidents-aurora-instance-1 \
  --db-instance-class db.r6g.xlarge \
  --engine aurora-postgresql \
  --db-cluster-identifier incidents-aurora-cluster
```

### Paso 3: Configurar pgvector

```bash
# Conectar y ejecutar SQL de configuración
psql -h incidents-aurora-cluster.cluster-xxxxx.eu-west-1.rds.amazonaws.com \
     -U incidents_admin \
     -d incidents_pgvectordb \
     -f setup_pgvector.sql
```

### Paso 4: Crear Knowledge Base

```bash
# Usar AWS CLI o CloudFormation
aws bedrock-agent create-knowledge-base \
  --name incidents-knowledge-base-pgvector \
  --role-arn arn:aws:iam::ACCOUNT:role/IncidentsKBRole \
  --knowledge-base-configuration file://kb-config.json \
  --storage-configuration file://storage-config.json
```

### Paso 5: Crear Data Source y Sincronizar

```bash
aws bedrock-agent create-data-source \
  --knowledge-base-id <KB_ID> \
  --name incidents-s3-datasource \
  --data-source-configuration file://datasource-config.json

# Iniciar sincronización
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id <KB_ID> \
  --data-source-id <DS_ID>
```

## 🔍 Queries de Ejemplo

### Búsqueda Vectorial Directa (sin Bedrock)

```sql
-- Buscar incidencias similares por embedding
SELECT 
    id,
    metadata->>'incident_id' as incident_id,
    metadata->>'title' as title,
    metadata->>'severity' as severity,
    1 - (embedding <=> $1::vector) as similarity
FROM incidents_knowledge_base_embeddings
WHERE metadata->>'category' = 'infrastructure'
ORDER BY embedding <=> $1::vector
LIMIT 5;
```

### Filtros Complejos con Metadata

```sql
-- Buscar incidencias críticas resueltas rápidamente
SELECT 
    metadata->>'incident_id' as incident_id,
    metadata->>'title' as title,
    (metadata->>'resolution_time_minutes')::int as resolution_time,
    metadata->>'root_cause' as root_cause
FROM incidents_knowledge_base_embeddings
WHERE 
    metadata->>'severity' = 'critical'
    AND (metadata->>'resolution_time_minutes')::int < 60
    AND metadata->>'resolved_date' IS NOT NULL
ORDER BY (metadata->>'resolution_time_minutes')::int ASC
LIMIT 10;
```

## 📝 Recomendaciones

### 1. **Usar Configuración del Piloto como Base**
- ✅ Reutilizar estructura de tabla
- ✅ Mismo embedding model (Titan v2, 1024 dims)
- ✅ Misma configuración de chunking

### 2. **Optimizaciones Adicionales**
- Ajustar `lists` en índice IVFFlat según volumen
- Considerar índices parciales para queries frecuentes
- Implementar particionamiento si > 1M incidencias

### 3. **Monitoreo**
- CloudWatch Metrics para Aurora
- Performance Insights habilitado
- Alarmas en latencia de queries

### 4. **Backup y DR**
- Snapshots automáticos diarios
- Cross-region replication (opcional)
- Procedimiento de restore documentado

## 🎯 Próximos Pasos

1. ✅ Revisar configuración de KB piloto
2. ⏭️ Crear Aurora cluster para incidencias
3. ⏭️ Configurar pgvector y tablas
4. ⏭️ Crear Knowledge Base apuntando a Aurora
5. ⏭️ Migrar datos de prueba
6. ⏭️ Implementar Lambda de análisis
7. ⏭️ Testing y optimización
