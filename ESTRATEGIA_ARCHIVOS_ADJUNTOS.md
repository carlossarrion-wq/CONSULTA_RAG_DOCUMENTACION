# Estrategia para Manejo de Archivos Adjuntos en Sistema de Incidencias

## 🎯 Problema Identificado

Los archivos adjuntos a incidencias **NO contienen información que los relacione directamente con la incidencia**. El único enlace es el **nombre del archivo** que incluye el ID de incidencia como prefijo.

Ejemplo:
```
INC-2024-001_error_log.txt
INC-2024-001_screenshot.png
INC-2024-002_network_trace.pcap
```

## 📊 Análisis de Opciones

### ❌ Opción NO Recomendada: Sincronizar archivos directamente con Knowledge Base

**Problemas**:
1. Los archivos no tienen contexto de la incidencia
2. La búsqueda semántica no encontraría relación
3. Desperdicio de espacio en el índice vectorial
4. Costos innecesarios de embeddings

### ✅ Opción Recomendada: Arquitectura de Dos Niveles (Tu Propuesta)

**Nivel 1: Knowledge Base** → Solo metadatos de incidencias
**Nivel 2: S3** → Archivos adjuntos organizados por ID

Esta es la **mejor solución** por las siguientes razones:

## 🏗️ Arquitectura Propuesta (Refinada)

```
┌─────────────────────────────────────────────────────────────────┐
│                    BEDROCK KNOWLEDGE BASE                        │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Documento: INC-2024-001                                     │ │
│  │ {                                                           │ │
│  │   "incident_id": "INC-2024-001",                           │ │
│  │   "description": "Servidor web no responde...",            │ │
│  │   "root_cause": "Certificado SSL expirado",                │ │
│  │   "resolution": "Renovar certificado...",                  │ │
│  │   "attachments_metadata": [                                │ │
│  │     {                                                       │ │
│  │       "file_name": "error_log.txt",                        │ │
│  │       "file_type": "log",                                  │ │
│  │       "description": "Log de errores del servidor",        │ │
│  │       "s3_path": "s3://incidents-files/INC-2024-001/..."   │ │
│  │     }                                                       │ │
│  │   ]                                                         │ │
│  │ }                                                           │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Búsqueda semántica
                              │ Retorna: incident_id + metadata
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         LAMBDA FUNCTION                          │
│  1. Recibe incidencias similares de Knowledge Base              │
│  2. Extrae incident_ids y attachments_metadata                  │
│  3. Para cada archivo en attachments_metadata:                  │
│     - Construye S3 path usando incident_id                      │
│     - Descarga archivo de S3                                    │
│     - Procesa contenido (PDF, imagen, log, etc.)                │
│  4. Construye contexto enriquecido para Claude                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         S3 BUCKETS                               │
│  incidents-files/                                                │
│  ├── INC-2024-001/                                              │
│  │   ├── error_log.txt                                          │
│  │   ├── screenshot.png                                         │
│  │   └── certificate_info.pdf                                   │
│  ├── INC-2024-002/                                              │
│  │   ├── network_trace.pcap                                     │
│  │   └── config_backup.conf                                     │
│  └── ...                                                         │
└─────────────────────────────────────────────────────────────────┘
```

## ✅ Ventajas de Esta Arquitectura

### 1. **Separación de Responsabilidades**
- **Knowledge Base**: Búsqueda semántica de incidencias
- **S3**: Almacenamiento eficiente de archivos binarios

### 2. **Optimización de Costos**
- No se generan embeddings innecesarios de archivos
- Solo se procesan archivos cuando son relevantes
- Almacenamiento S3 es más económico que OpenSearch

### 3. **Flexibilidad**
- Fácil agregar/eliminar archivos sin reindexar
- Soporta cualquier tipo de archivo
- No hay límites de tamaño en S3

### 4. **Rendimiento**
- Búsqueda rápida en Knowledge Base
- Descarga paralela de archivos desde S3
- Procesamiento bajo demanda

## 🔧 Mejoras Propuestas

### Mejora 1: Metadata Enriquecido en Knowledge Base

En lugar de solo el nombre del archivo, incluir **descripción semántica**:

```json
{
  "incident_id": "INC-2024-001",
  "description": "Servidor web no responde en puerto 443",
  "attachments_metadata": [
    {
      "file_name": "error_log.txt",
      "file_type": "log",
      "description": "Log de errores del servidor nginx mostrando fallos SSL",
      "summary": "Múltiples errores SSL_ERROR_EXPIRED_CERT_ALERT",
      "s3_path": "s3://incidents-files/INC-2024-001/error_log.txt",
      "size_bytes": 15420,
      "created_at": "2024-09-15T10:35:00Z"
    },
    {
      "file_name": "screenshot.png",
      "file_type": "image",
      "description": "Captura de pantalla del error en navegador",
      "summary": "Error NET::ERR_CERT_DATE_INVALID en Chrome",
      "s3_path": "s3://incidents-files/INC-2024-001/screenshot.png",
      "size_bytes": 245680,
      "created_at": "2024-09-15T10:36:00Z"
    }
  ]
}
```

**Ventajas**:
- La descripción y summary son indexables semánticamente
- Ayuda a Claude a entender qué archivos son más relevantes
- Permite filtrado inteligente de archivos

### Mejora 2: Procesamiento Selectivo de Archivos

No todos los archivos son igualmente relevantes. Implementar lógica de priorización:

```python
def prioritize_attachments(attachments_metadata, incident_context):
    """
    Prioriza qué archivos descargar basándose en:
    - Tipo de archivo (logs > screenshots > configs)
    - Relevancia semántica del summary
    - Tamaño (preferir archivos pequeños primero)
    """
    priorities = {
        'log': 10,
        'error_log': 15,
        'screenshot': 8,
        'config': 7,
        'trace': 6
    }
    
    scored_attachments = []
    for attachment in attachments_metadata:
        score = priorities.get(attachment['file_type'], 5)
        
        # Bonus por palabras clave en summary
        if 'error' in attachment.get('summary', '').lower():
            score += 5
        if 'critical' in attachment.get('summary', '').lower():
            score += 3
            
        # Penalización por tamaño grande
        if attachment['size_bytes'] > 10_000_000:  # 10MB
            score -= 2
            
        scored_attachments.append((score, attachment))
    
    # Ordenar por score descendente
    scored_attachments.sort(reverse=True, key=lambda x: x[0])
    
    # Retornar top N archivos más relevantes
    return [att for score, att in scored_attachments[:5]]
```

### Mejora 3: Cache de Archivos Procesados

Para archivos que se repiten en múltiples incidencias:

```python
# Usar hash del contenido como clave
file_hash = hashlib.sha256(file_content).hexdigest()
cache_key = f"processed_file:{file_hash}"

# Intentar obtener de cache (ElastiCache/Redis)
processed_content = cache.get(cache_key)

if not processed_content:
    # Procesar archivo (OCR, extracción de texto, etc.)
    processed_content = process_file(file_content)
    
    # Guardar en cache (TTL: 7 días)
    cache.set(cache_key, processed_content, ttl=604800)
```

## 🎯 Soluciones Alternativas (Si la Propuesta Actual No Funciona)

### Alternativa 1: Wrapper Documents en Knowledge Base

Crear documentos "wrapper" que combinen metadata + contenido de archivos:

```json
{
  "incident_id": "INC-2024-001",
  "description": "Servidor web no responde...",
  "attachment_1_content": "<<CONTENIDO EXTRAÍDO DEL LOG>>",
  "attachment_2_content": "<<TEXTO EXTRAÍDO DE SCREENSHOT VIA OCR>>",
  "attachment_3_content": "<<CONTENIDO DEL CONFIG FILE>>"
}
```

**Ventajas**:
- Todo en un solo lugar
- Búsqueda semántica incluye contenido de archivos

**Desventajas**:
- Documentos muy grandes
- Costos altos de embeddings
- Difícil actualizar archivos

### Alternativa 2: Knowledge Base Jerárquico

Dos Knowledge Bases separadas con relación:

```
KB1: Incidencias (principal)
  ↓ incident_id
KB2: Archivos (secundaria)
  - Indexa contenido de archivos
  - Cada documento tiene incident_id como metadata
```

**Ventajas**:
- Búsqueda granular
- Actualización independiente

**Desventajas**:
- Dos consultas necesarias
- Mayor complejidad
- Costos duplicados

### Alternativa 3: Embeddings On-Demand

No pre-indexar archivos. Generar embeddings en tiempo real:

```python
# Cuando se encuentra incidencia similar
for attachment in incident['attachments']:
    # Descargar y procesar archivo
    content = download_and_process(attachment['s3_path'])
    
    # Generar embedding on-the-fly
    embedding = generate_embedding(content)
    
    # Calcular similitud con query
    similarity = cosine_similarity(query_embedding, embedding)
    
    if similarity > threshold:
        # Incluir en contexto para Claude
        relevant_attachments.append(content)
```

**Ventajas**:
- Sin costos de indexación
- Siempre actualizado

**Desventajas**:
- Mayor latencia
- Costos de compute en Lambda

## 📋 Recomendación Final

**Mantener tu propuesta original** con las **Mejoras 1 y 2**:

1. ✅ **Metadata de incidencias en Knowledge Base** (con descripción enriquecida de archivos)
2. ✅ **Archivos en S3** organizados por incident_id
3. ✅ **Procesamiento selectivo** de archivos más relevantes
4. ✅ **Cache opcional** para archivos frecuentes

Esta arquitectura es:
- ✅ **Eficiente en costos**
- ✅ **Escalable**
- ✅ **Flexible**
- ✅ **Fácil de mantener**

## 🔄 Flujo Optimizado

```
1. Usuario consulta: "Servidor web no responde puerto 443"
   ↓
2. Knowledge Base retorna top 5 incidencias similares
   Incluye: incident_id + attachments_metadata con descriptions
   ↓
3. Lambda analiza attachments_metadata:
   - Prioriza por tipo y relevancia
   - Selecciona top 3-5 archivos más relevantes
   ↓
4. Lambda descarga archivos de S3 en paralelo
   - Solo los archivos priorizados
   - Usa cache si está disponible
   ↓
5. Lambda procesa archivos:
   - PDF → Texto
   - Imágenes → OCR
   - Logs → Parsing
   ↓
6. Lambda construye contexto para Claude:
   - Incidencia actual
   - Top 5 incidencias similares
   - Contenido de archivos relevantes
   ↓
7. Claude analiza y genera respuesta
```

## 💡 Conclusión

Tu propuesta de **separar metadata (KB) y archivos (S3)** es la **solución correcta**. 

La clave del éxito está en:
1. **Enriquecer el metadata** con descripciones semánticas de archivos
2. **Priorizar inteligentemente** qué archivos procesar
3. **Optimizar con cache** cuando sea posible

Esto te da lo mejor de ambos mundos: búsqueda semántica eficiente + acceso flexible a archivos.
