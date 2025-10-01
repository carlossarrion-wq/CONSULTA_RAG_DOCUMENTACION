# Comparación de Knowledge Bases

## Knowledge Base Piloto vs Nuestro Proyecto

### Knowledge Base Piloto (piloto-plan-pruebas-e2e-rag-knowledgebase-pgvector)

**Configuración:**
- **KB ID**: VH6SRH9ZNO
- **Estado**: ACTIVE
- **Embedding Model**: Amazon Titan Embeddings v2
  - Dimensiones: 1024
  - Tipo de datos: FLOAT32
- **Storage**: RDS (Aurora PostgreSQL)
  - Cluster: piloto-plan-pruebas-aurora-cluster
  - **Engine Version**: 17.4 ✅
  - **HTTP Endpoint Enabled**: true ✅
  - Database: pgvectordb
  - Table: piloto_plan_pruebas_knowledge_base_embeddings
  - Serverless v2: 0.5 - 16.0 ACU
- **Supplemental Data Storage**: S3 (s3://piloto-plan-pruebas-origen-datos-source)

### Nuestro Proyecto (incident-analyzer-dev)

**Configuración Actual:**
- **KB**: No creada aún
- **Embedding Model**: Amazon Titan Embeddings v2 (mismo que piloto)
  - Dimensiones: 1024
  - Tipo de datos: FLOAT32
- **Storage**: RDS (Aurora PostgreSQL)
  - Cluster: incident-analyzer-dev-auroradbcluster-yfyflevgsyk5
  - **Engine Version**: 15.4 ❌ (PROBLEMA)
  - **HTTP Endpoint Enabled**: false ❌ (PROBLEMA)
  - Database: incidents_kb
  - Table: incidents_knowledge_base_embeddings
  - Serverless v2: 0.5 - 2.0 ACU
- **S3 Bucket**: incident-analyzer-dev-incidents-dev

## Análisis de Diferencias

### ✅ Compatibilidades
1. **Embedding Model**: Ambos usan Amazon Titan Embeddings v2 con 1024 dimensiones
2. **Storage Type**: Ambos usan Aurora PostgreSQL con pgvector
3. **Serverless v2**: Ambos usan Aurora Serverless v2
4. **Arquitectura**: Misma arquitectura RDS + S3

### ❌ Problemas Identificados

#### 1. Versión de Aurora PostgreSQL
- **Piloto**: 17.4 (soporta Data API)
- **Nuestro**: 15.4 (NO soporta Data API)
- **Impacto**: Bedrock Knowledge Base requiere Data API v2 para acceder a Aurora
- **Solución Requerida**: Actualizar a PostgreSQL 16.x o 17.x

#### 2. HTTP Endpoint (Data API)
- **Piloto**: Habilitado
- **Nuestro**: Deshabilitado
- **Impacto**: Sin Data API, Bedrock no puede conectarse a Aurora
- **Solución Requerida**: Habilitar después de actualizar versión

## Recomendaciones

### Opción 1: Actualizar Aurora a PostgreSQL 17.4 (RECOMENDADA)
**Ventajas:**
- Misma configuración que el piloto (probada y funcionando)
- Versión más reciente con mejoras de rendimiento
- Soporte completo para Data API
- Compatibilidad total con Bedrock Knowledge Base

**Pasos:**
1. Actualizar cluster de 15.4 → 17.4
2. Habilitar HTTP Endpoint
3. Crear Knowledge Base con script existente

**Tiempo estimado:** 10-15 minutos (actualización de Aurora)

### Opción 2: Usar OpenSearch Serverless
**Ventajas:**
- No requiere actualización de Aurora
- Totalmente gestionado
- Sin problemas de versiones

**Desventajas:**
- Diferente arquitectura que el piloto
- Costos potencialmente más altos
- Menos control sobre la infraestructura

## Decisión Recomendada

**Actualizar Aurora a PostgreSQL 17.4** para mantener la misma arquitectura que el piloto exitoso.

### Comando de Actualización

```bash
# Actualizar cluster a PostgreSQL 17.4
aws rds modify-db-cluster \
  --db-cluster-identifier incident-analyzer-dev-auroradbcluster-yfyflevgsyk5 \
  --engine-version 17.4 \
  --db-cluster-parameter-group-name default.aurora-postgresql17 \
  --allow-major-version-upgrade \
  --apply-immediately \
  --region eu-west-1

# Habilitar Data API
aws rds modify-db-cluster \
  --db-cluster-identifier incident-analyzer-dev-auroradbcluster-yfyflevgsyk5 \
  --enable-http-endpoint \
  --apply-immediately \
  --region eu-west-1
```

### Verificación Post-Actualización

```bash
# Verificar versión y Data API
aws rds describe-db-clusters \
  --db-cluster-identifier incident-analyzer-dev-auroradbcluster-yfyflevgsyk5 \
  --query 'DBClusters[0].[EngineVersion,HttpEndpointEnabled]' \
  --output table \
  --region eu-west-1
```

## Conclusión

La configuración del piloto es **100% compatible** con nuestros requisitos. Solo necesitamos actualizar la versión de Aurora PostgreSQL de 15.4 a 17.4 para habilitar el Data API y poder crear la Knowledge Base exitosamente.
