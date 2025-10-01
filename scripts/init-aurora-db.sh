#!/bin/bash
# Script para inicializar la base de datos Aurora con pgvector

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
if [ $# -lt 1 ]; then
    log_error "Uso: $0 <aurora-secret-arn> [region]"
    exit 1
fi

AURORA_SECRET_ARN=$1
REGION=${2:-${AWS_REGION:-eu-west-1}}

log_info "Inicializando base de datos Aurora"
log_info "Región: $REGION"

# Obtener credenciales de Aurora
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
AURORA_PASSWORD=$(echo "$AURORA_CREDS" | jq -r '.password')

log_info "Conectando a Aurora: $AURORA_HOST:$AURORA_PORT/$AURORA_DB"

# Crear archivo SQL temporal
SQL_FILE=$(mktemp)
cat > "$SQL_FILE" <<'EOF'
-- Habilitar extensión pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Crear tabla para embeddings de la Knowledge Base
CREATE TABLE IF NOT EXISTS incidents_knowledge_base_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    embedding VECTOR(1024) NOT NULL,
    text_chunk TEXT NOT NULL,
    metadata JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Crear índice IVFFlat para búsqueda vectorial eficiente
-- Nota: El índice se crea después de tener datos, aquí solo preparamos la estructura
-- CREATE INDEX IF NOT EXISTS incidents_kb_embedding_idx 
-- ON incidents_knowledge_base_embeddings 
-- USING ivfflat (embedding vector_cosine_ops) 
-- WITH (lists = 100);

-- Crear índice GIN para búsqueda en metadata JSONB
CREATE INDEX IF NOT EXISTS incidents_kb_metadata_idx 
ON incidents_knowledge_base_embeddings 
USING GIN (metadata);

-- Crear índice para búsqueda por fecha
CREATE INDEX IF NOT EXISTS incidents_kb_created_at_idx 
ON incidents_knowledge_base_embeddings (created_at DESC);

-- Función para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger para actualizar updated_at
DROP TRIGGER IF EXISTS update_incidents_kb_updated_at ON incidents_knowledge_base_embeddings;
CREATE TRIGGER update_incidents_kb_updated_at
    BEFORE UPDATE ON incidents_knowledge_base_embeddings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Función auxiliar para búsqueda por similitud coseno
CREATE OR REPLACE FUNCTION search_similar_incidents(
    query_embedding VECTOR(1024),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    id UUID,
    text_chunk TEXT,
    metadata JSONB,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.id,
        e.text_chunk,
        e.metadata,
        1 - (e.embedding <=> query_embedding) AS similarity
    FROM incidents_knowledge_base_embeddings e
    WHERE 1 - (e.embedding <=> query_embedding) > match_threshold
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- Crear vista para estadísticas
CREATE OR REPLACE VIEW incidents_kb_stats AS
SELECT 
    COUNT(*) as total_embeddings,
    COUNT(DISTINCT metadata->>'incident_id') as unique_incidents,
    MIN(created_at) as first_entry,
    MAX(created_at) as last_entry,
    pg_size_pretty(pg_total_relation_size('incidents_knowledge_base_embeddings')) as table_size
FROM incidents_knowledge_base_embeddings;

-- Grants para el usuario de la aplicación (si es diferente del admin)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON incidents_knowledge_base_embeddings TO app_user;
-- GRANT EXECUTE ON FUNCTION search_similar_incidents TO app_user;
-- GRANT SELECT ON incidents_kb_stats TO app_user;

EOF

# Ejecutar SQL
log_info "Ejecutando script de inicialización..."

export PGPASSWORD="$AURORA_PASSWORD"

psql -h "$AURORA_HOST" \
     -p "$AURORA_PORT" \
     -U "$AURORA_USER" \
     -d "$AURORA_DB" \
     -f "$SQL_FILE"

PSQL_EXIT_CODE=$?

# Limpiar archivo temporal
rm -f "$SQL_FILE"
unset PGPASSWORD

if [ $PSQL_EXIT_CODE -ne 0 ]; then
    log_error "Error ejecutando script SQL"
    exit 1
fi

log_info "✓ Base de datos inicializada exitosamente"
log_info ""
log_info "Estructura creada:"
log_info "  - Extensión pgvector habilitada"
log_info "  - Tabla: incidents_knowledge_base_embeddings"
log_info "  - Índices: metadata (GIN), created_at (B-tree)"
log_info "  - Función: search_similar_incidents()"
log_info "  - Vista: incidents_kb_stats"
log_info ""
log_info "Nota: El índice IVFFlat se creará automáticamente después de ingerir datos"
log_info ""
log_info "Para verificar la instalación, ejecuta:"
log_info "  psql -h $AURORA_HOST -p $AURORA_PORT -U $AURORA_USER -d $AURORA_DB -c 'SELECT * FROM incidents_kb_stats;'"
