# Arquitectura del Sistema de Análisis de Incidencias con RAG

## 📋 Resumen Ejecutivo

Sistema de análisis inteligente de incidencias que utiliza AWS Bedrock Knowledge Base y Claude para proporcionar diagnósticos, causas raíz y recomendaciones basadas en histórico de incidencias similares.

## 🎯 Caso de Uso

**Entrada**: Descripción de una incidencia por parte del usuario

**Proceso**: 
1. Búsqueda de incidencias similares en Knowledge Base
2. Recuperación de documentos adjuntos relacionados
3. Análisis con LLM (Claude)

**Salida**:
- Diagnóstico y posible causa raíz
- Acciones recomendadas para resolución
- Listado de incidencias históricas relevantes con resumen

## 🏗️ Arquitectura de la Solución

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              USUARIO/CLIENTE                             │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             │ HTTPS Request
                             │ POST /analyze-incident
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           API GATEWAY (REST)                             │
│  - Autenticación (API Key / Cognito)                                    │
│  - Rate Limiting                                                         │
│  - Request Validation                                                    │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    LAMBDA 1: Incident Analyzer                           │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ 1. Recibe descripción de incidencia                               │  │
│  │ 2. Genera embedding de la consulta                                │  │
│  │ 3. Busca en Knowledge Base (RAG)                                  │  │
│  │ 4. Obtiene incidencias similares + metadatos                      │  │
│  │ 5. Recupera archivos adjuntos de S3                               │  │
│  │ 6. Construye contexto enriquecido                                 │  │
│  │ 7. Invoca Claude con contexto completo                            │  │
│  │ 8. Formatea y devuelve respuesta                                  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└──────┬──────────────────┬──────────────────┬────────────────────────────┘
       │                  │                  │
       │                  │                  │
       ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐
│   BEDROCK    │  │   BEDROCK    │  │      S3 BUCKETS          │
│  KNOWLEDGE   │  │    CLAUDE    │  │                          │
│     BASE     │  │  SONNET 4.5  │  │  ┌────────────────────┐  │
│              │  │              │  │  │ incidents-metadata/│  │
│  - Embeddings│  │  - Análisis  │  │  │  (SINCRONIZADO     │  │
│  - Búsqueda  │  │  - Diagnóstico│ │  │   CON KB)          │  │
│    Semántica │  │  - Recomend. │  │  └────────────────────┘  │
│              │  │              │  │                          │
│              │  │              │  │  ┌────────────────────┐  │
│              │  │              │  │  │ incidents-files/   │  │
│              │  │              │  │  │  (NO SINCRONIZADO) │  │
│              │  │              │  │  │  - 123/doc1.pdf    │  │
│              │  │              │  │  │  - 123/img1.jpg    │  │
│              │  │              │  │  │  - 456/doc2.pdf    │  │
│              │  │              │  │  └────────────────────┘  │
└──────────────┘  └──────────────┘  └──────────────────────────┘
       ▲                                      ▲
       │                                      │
       │                                      │
┌──────┴──────────────────────────────────────┴──────────────────┐
│              LAMBDA 2: Data Ingestion (Opcional)                │
│  - Procesa nuevas incidencias                                   │
│  - Extrae metadatos                                             │
│  - Sube archivos a S3                                           │
│  - Actualiza Knowledge Base                                     │
└─────────────────────────────────────────────────────────────────┘
```

## 🔧 Componentes Detallados

### 1. API Gateway

**Configuración**:
```yaml
Endpoint: /analyze-incident
Método: POST
Autenticación: API Key o AWS Cognito
Rate Limit: 100 requests/minuto
Timeout: 300 segundos (5 minutos)
```

**Request Body**:
```json
{
  "incident_description": "El servidor web no responde en el puerto 443",
  "incident_metadata": {
    "severity": "high",
    "category": "infrastructure",
    "reported_by": "user@example.com"
  },
  "max_similar_incidents": 5,
  "include_attachments": true
}
```

**Response**:
```json
{
  "diagnosis": {
    "root_cause": "Certificado SSL expirado",
    "confidence": 0.92,
    "analysis": "Basado en 5 incidencias similares..."
  },
  "recommended_actions": [
    {
      "priority": 1,
      "action": "Renovar certificado SSL",
      "estimated_time": "15 minutos",
      "commands": ["certbot renew"]
    }
  ],
  "similar_incidents": [
    {
      "incident_id": "INC-2024-001",
      "similarity_score": 0.95,
      "summary": "Certificado SSL expirado en servidor producción",
      "resolution": "Renovación de certificado",
      "resolution_time": "20 minutos"
    }
  ],
  "metadata": {
    "processing_time_ms": 3500,
    "tokens_used": 2500,
    "knowledge_base_hits": 5
  }
}
```

### 2. Lambda Function: Incident Analyzer

**Especificaciones**:
- **Runtime**: Python 3.11
- **Memoria**: 2048 MB
- **Timeout**: 300 segundos
- **Concurrencia**: 10 ejecuciones simultáneas

**Variables de Entorno**:
```bash
KNOWLEDGE_BASE_ID=XXXXX
BEDROCK_MODEL_ID=eu.anthropic.claude-sonnet-4-5-20250929-v1:0
S3_METADATA_BUCKET=incidents-metadata
S3_FILES_BUCKET=incidents-files
S3_KB_BUCKET=incidents-knowledge-base
AWS_REGION=eu-west-1
MAX_SIMILAR_INCIDENTS=5
```

**Nota Importante sobre Sincronización**:
- ✅ **incidents-metadata/** → SE SINCRONIZA con Knowledge Base
- ❌ **incidents-files/** → NO se sincroniza (solo almacenamiento)
- Los archivos se recuperan bajo demanda usando incident_id como clave

**Permisos IAM Requeridos**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:Retrieve",
        "bedrock:RetrieveAndGenerate",
        "bedrock:InvokeModel"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::incidents-metadata/*",
        "arn:aws:s3:::incidents-files/*"
      ]
    }
  ]
}
```

### 3. Bedrock Knowledge Base

**Configuración**:

**Data Source**:
- **Tipo**: S3
- **Bucket**: `incidents-knowledge-base`
- **Formato**: JSON estructurado

**Estructura de Documento en Knowledge Base**:
```json
{
  "incident_id": "INC-2024-001",
  "title": "Servidor web no responde",
  "description": "El servidor web principal no responde en el puerto 443. Los usuarios reportan error de conexión SSL.",
  "category": "infrastructure",
  "severity": "high",
  "reported_date": "2024-09-15T10:30:00Z",
  "resolved_date": "2024-09-15T11:00:00Z",
  "root_cause": "Certificado SSL expirado",
  "resolution": "Se renovó el certificado SSL usando certbot",
  "resolution_steps": [
    "Verificar estado del certificado: openssl x509 -in cert.pem -noout -dates",
    "Renovar certificado: certbot renew",
    "Reiniciar nginx: systemctl restart nginx"
  ],
  "tags": ["ssl", "certificate", "web-server", "nginx"],
  "attachments": [
    "s3://incidents-files/INC-2024-001/error_log.txt",
    "s3://incidents-files/INC-2024-001/certificate_info.pdf"
  ]
}
```

**Embedding Model**:
- **Modelo**: Amazon Titan Embeddings G1 - Text
- **Dimensiones**: 1536
- **Chunking**: 
  - Tamaño: 500 tokens
  - Overlap: 50 tokens

**Vector Store**:
- **Tipo**: OpenSearch Serverless
- **Índice**: incidents-vector-index
- **Similarity Metric**: Cosine

### 4. S3 Buckets

**Bucket 1: incidents-metadata**
```
incidents-metadata/
├── INC-2024-001.json
├── INC-2024-002.json
├── INC-2024-003.json
└── ...
```

**Bucket 2: incidents-files**
```
incidents-files/
├── INC-2024-001/
│   ├── error_log.txt
│   ├── screenshot.png
│   └── certificate_info.pdf
├── INC-2024-002/
│   ├── network_trace.pcap
│   └── config_backup.conf
└── ...
```

**Bucket 3: incidents-knowledge-base** (Data Source para Bedrock KB)
```
incidents-knowledge-base/
├── incidents_batch_001.json  ← Sincronizado desde incidents-metadata/
├── incidents_batch_002.json  ← Sincronizado desde incidents-metadata/
└── ...
```

**Nota**: Este bucket es el Data Source de Bedrock Knowledge Base. 
Se sincroniza automáticamente con incidents-metadata/ mediante:
- Lambda de ingesta
- EventBridge Schedule
- S3 Event Notifications

**Políticas de Lifecycle**:
- Transición a S3 Glacier después de 90 días
- Eliminación después de 7 años (cumplimiento)

### 5. Lambda Function: Data Ingestion (Opcional)

**Propósito**: Automatizar la ingesta de nuevas incidencias

**Trigger**: 
- S3 Event (cuando se sube nuevo archivo a `incidents-raw/`)
- EventBridge Schedule (procesamiento batch diario)

**Proceso**:
1. Leer incidencia del sistema origen
2. Extraer y estructurar metadatos
3. Procesar archivos adjuntos
4. Subir a S3 (metadata y files)
5. Actualizar Knowledge Base
6. Sincronizar índice vectorial

## 📊 Flujo de Datos Detallado

### Flujo Principal: Análisis de Incidencia

```
1. Usuario envía descripción de incidencia
   ↓
2. API Gateway valida y enruta a Lambda
   ↓
3. Lambda genera embedding de la consulta
   ↓
4. Bedrock Knowledge Base busca incidencias similares
   ↓
5. Lambda recupera top-N incidencias más similares
   ↓
6. Para cada incidencia similar:
   a. Obtener metadata de S3 (incidents-metadata/)
   b. Obtener archivos adjuntos de S3 (incidents-files/)
   c. Procesar archivos (PDF, imágenes, logs)
   ↓
7. Construir contexto enriquecido:
   - Descripción de incidencia actual
   - Incidencias similares con metadata
   - Contenido de archivos adjuntos
   ↓
8. Invocar Claude con prompt estructurado:
   """
   Analiza la siguiente incidencia y proporciona:
   1. Diagnóstico y causa raíz probable
   2. Acciones recomendadas paso a paso
   3. Resumen de incidencias similares utilizadas
   
   Incidencia actual: {descripción}
   
   Incidencias históricas similares:
   {contexto de incidencias}
   
   Documentos adjuntos:
   {contenido de archivos}
   """
   ↓
9. Claude genera respuesta estructurada
   ↓
10. Lambda formatea respuesta JSON
   ↓
11. API Gateway devuelve respuesta al usuario
```

## 🔐 Seguridad

### Autenticación y Autorización

**Opción 1: API Keys**
```yaml
API Gateway:
  - API Key requerida
  - Usage Plans con límites
  - Rotación automática cada 90 días
```

**Opción 2: AWS Cognito**
```yaml
Cognito User Pool:
  - Autenticación de usuarios
  - MFA opcional
  - Grupos de usuarios (admin, analyst, viewer)
  
API Gateway:
  - Cognito Authorizer
  - Validación de tokens JWT
```

### Encriptación

- **En tránsito**: TLS 1.3
- **En reposo**: 
  - S3: SSE-S3 o SSE-KMS
  - Knowledge Base: Encriptación por defecto
  - Lambda: Variables de entorno encriptadas con KMS

### Auditoría

- **CloudTrail**: Registro de todas las llamadas API
- **CloudWatch Logs**: Logs de Lambda y API Gateway
- **S3 Access Logs**: Acceso a buckets

## 💰 Estimación de Costos (Mensual)

### Escenario: 10,000 consultas/mes

| Servicio | Uso | Costo Estimado |
|----------|-----|----------------|
| API Gateway | 10,000 requests | $0.04 |
| Lambda (Analyzer) | 10,000 invocaciones × 5s × 2GB | $1.67 |
| Bedrock Knowledge Base | 10,000 queries | $10.00 |
| Bedrock Claude 3.5 Sonnet | ~25M tokens | $75.00 |
| S3 Storage | 100GB | $2.30 |
| S3 Requests | 50,000 GET | $0.02 |
| OpenSearch Serverless | 1 OCU | $700.00 |
| **TOTAL** | | **~$789/mes** |

**Nota**: OpenSearch Serverless es el componente más costoso. Alternativas:
- Usar Amazon Aurora con pgvector (más económico)
- Usar FAISS en Lambda (sin servidor adicional)

## 🚀 Plan de Implementación

### Fase 1: Infraestructura Base (Semana 1-2)
- [ ] Crear buckets S3
- [ ] Configurar IAM roles y políticas
- [ ] Desplegar Lambda básica
- [ ] Configurar API Gateway

### Fase 2: Knowledge Base (Semana 2-3)
- [ ] Crear Knowledge Base en Bedrock
- [ ] Configurar data source (S3)
- [ ] Preparar datos de incidencias históricas
- [ ] Realizar ingesta inicial
- [ ] Probar búsqueda semántica

### Fase 3: Integración con Claude (Semana 3-4)
- [ ] Implementar lógica de recuperación de contexto
- [ ] Diseñar prompts optimizados
- [ ] Integrar procesamiento de archivos adjuntos
- [ ] Implementar formateo de respuestas

### Fase 4: Testing y Optimización (Semana 4-5)
- [ ] Tests unitarios
- [ ] Tests de integración
- [ ] Pruebas de carga
- [ ] Optimización de costos
- [ ] Ajuste de prompts

### Fase 5: Producción (Semana 5-6)
- [ ] Configurar monitoreo
- [ ] Implementar alertas
- [ ] Documentación
- [ ] Despliegue a producción
- [ ] Capacitación de usuarios

## 📈 Monitoreo y Métricas

### CloudWatch Dashboards

**Métricas Clave**:
- Latencia de API Gateway (p50, p95, p99)
- Duración de Lambda
- Errores de Lambda
- Tokens consumidos en Bedrock
- Tasa de aciertos en Knowledge Base
- Costos por consulta

**Alarmas**:
- Latencia > 10 segundos
- Error rate > 5%
- Costos diarios > umbral
- Concurrencia Lambda > 80%

## 🔄 Mejoras Futuras

1. **Cache de Resultados**: Redis/ElastiCache para consultas frecuentes
2. **Feedback Loop**: Capturar feedback de usuarios para mejorar
3. **A/B Testing**: Probar diferentes prompts y modelos
4. **Análisis Predictivo**: ML para predecir incidencias
5. **Integración con ITSM**: ServiceNow, Jira Service Management
6. **Multi-idioma**: Soporte para múltiples idiomas
7. **Visualizaciones**: Dashboard con gráficos de incidencias

## 📝 Consideraciones Adicionales

### Alternativas a OpenSearch Serverless

**Opción 1: Amazon Aurora PostgreSQL con pgvector**
- Más económico (~$100/mes vs $700/mes)
- Requiere gestión de base de datos
- Excelente para volúmenes medios

**Opción 2: FAISS en Lambda**
- Sin costos de base de datos vectorial
- Índice almacenado en S3
- Carga en memoria en Lambda
- Limitado por memoria de Lambda (10GB max)

**Opción 3: Pinecone**
- Servicio gestionado especializado
- Pricing basado en uso
- Excelente rendimiento

### Optimización de Costos

1. **Usar Lambda con ARM (Graviton2)**: 20% más económico
2. **Reserved Capacity en OpenSearch**: Descuento significativo
3. **S3 Intelligent-Tiering**: Optimización automática de costos
4. **Batch Processing**: Agrupar consultas cuando sea posible
5. **Cache**: Reducir llamadas a Bedrock
