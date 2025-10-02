"""
Analizador de incidencias usando RAG con AWS Bedrock Knowledge Base
"""
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


@dataclass
class IncidentAnalysisRequest:
    """Solicitud de análisis de incidencia"""
    incident_description: str
    incident_id: Optional[str] = None
    max_similar_incidents: int = 5
    include_attachments: bool = True
    optimize_query: bool = True


@dataclass
class SimilarIncident:
    """Incidencia similar encontrada"""
    incident_id: str
    title: str
    description: str
    resolution: str
    similarity_score: float
    metadata: Dict[str, Any]
    attachments: List[str] = None


@dataclass
class IncidentAnalysisResponse:
    """Respuesta del análisis de incidencia"""
    diagnosis: str
    root_cause: str
    recommended_actions: List[str]
    similar_incidents: List[SimilarIncident]
    confidence_score: float
    model_id: str
    input_tokens: int
    output_tokens: int
    original_query: str = ""
    optimized_query: str = ""


class IncidentAnalyzer:
    """Analizador de incidencias con RAG"""
    
    def __init__(
        self,
        knowledge_base_id: str,
        s3_bucket: str,
        model_id: str = "eu.anthropic.claude-sonnet-4-5-20250929-v1:0",
        region: str = "eu-west-1"
    ):
        """
        Inicializa el analizador de incidencias
        
        Args:
            knowledge_base_id: ID de la Knowledge Base en Bedrock
            s3_bucket: Bucket S3 con archivos de incidencias
            model_id: ID del modelo Claude a usar
            region: Región de AWS
        """
        self.knowledge_base_id = knowledge_base_id
        self.s3_bucket = s3_bucket
        self.model_id = model_id
        self.region = region
        
        # Clientes AWS
        self.bedrock_agent = boto3.client("bedrock-agent-runtime", region_name=region)
        self.bedrock_runtime = boto3.client("bedrock-runtime", region_name=region)
        self.s3_client = boto3.client("s3", region_name=region)
        
        logger.info(f"IncidentAnalyzer inicializado - KB: {knowledge_base_id}, Modelo: {model_id}")
    
    def analyze_incident(self, request: IncidentAnalysisRequest) -> IncidentAnalysisResponse:
        """
        Analiza una incidencia usando RAG
        
        Args:
            request: Solicitud de análisis
            
        Returns:
            Respuesta con diagnóstico y recomendaciones
        """
        try:
            logger.info(f"Iniciando análisis de incidencia: {request.incident_id or 'nueva'}")
            
            # 1. Normalizar/mejorar la consulta del usuario (si está habilitado)
            if request.optimize_query:
                optimized_query = self._optimize_query(request.incident_description)
                logger.info(f"Consulta optimizada: {optimized_query}")
            else:
                optimized_query = request.incident_description
                logger.info("Optimización de consulta deshabilitada, usando consulta original")
            
            # 2. Buscar incidencias similares en la Knowledge Base usando la consulta (optimizada o no)
            similar_incidents = self._search_similar_incidents(
                optimized_query,
                max_results=request.max_similar_incidents
            )
            
            logger.info(f"Encontradas {len(similar_incidents)} incidencias similares")
            
            # 3. Recuperar archivos adjuntos de S3 si es necesario
            if request.include_attachments:
                for incident in similar_incidents:
                    incident.attachments = self._get_incident_attachments(incident.incident_id)
            
            # 4. Construir contexto para Claude
            context = self._build_analysis_context(request, similar_incidents)
            
            # 5. Invocar Claude para análisis
            analysis_result = self._invoke_claude_analysis(context)
            
            # 6. Parsear y estructurar respuesta
            response = self._parse_analysis_response(
                analysis_result,
                similar_incidents
            )
            
            # 7. Agregar consultas original y optimizada a la respuesta
            response.original_query = request.incident_description
            response.optimized_query = optimized_query
            
            logger.info(f"Análisis completado - Confianza: {response.confidence_score:.2f}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error analizando incidencia: {str(e)}", exc_info=True)
            raise
    
    def _optimize_query(self, user_query: str) -> str:
        """
        Optimiza la consulta del usuario antes de buscar en la Knowledge Base
        
        Args:
            user_query: Consulta original del usuario
            
        Returns:
            Consulta optimizada para búsqueda
        """
        try:
            logger.info("Optimizando consulta del usuario...")
            
            # Prompt para optimización de consulta
            optimization_prompt = """Eres un agente de creación de consultas para un sistema de análisis de incidencias técnicas. Se te proporcionará una descripción de una incidencia técnica, y tu tarea será determinar la consulta óptima que se debe usar para buscar incidencias similares en una base de conocimiento.

Tu objetivo es:
1. Extraer los conceptos técnicos clave de la descripción
2. Normalizar términos técnicos a su forma estándar
3. Eliminar información redundante o poco relevante
4. Mantener los detalles técnicos importantes (códigos de error, componentes, síntomas)
5. Generar una consulta concisa pero completa

Aquí tienes algunos ejemplos de consultas optimizadas:

<examples>
<example>
<question>
El servidor de base de datos PostgreSQL está mostrando errores de conexión. Los usuarios reportan que no pueden acceder a la aplicación y reciben mensajes de timeout. El log muestra 'connection refused' repetidamente.
</question>
<generated_query>
PostgreSQL error conexión timeout connection refused servidor base datos
</generated_query>
</example>

<example>
<question>
Tenemos un problema con el servidor de aplicaciones que está consumiendo mucha CPU, como el 95% constantemente. La aplicación se pone muy lenta y algunos procesos se quedan colgados. También vemos que la memoria va subiendo poco a poco.
</question>
<generated_query>
servidor aplicaciones alto consumo CPU 95% rendimiento lento fuga memoria
</generated_query>
</example>

<example>
<question>
El servicio de autenticación OAuth falla a veces. Algunos usuarios pueden entrar bien pero otros reciben error 500. En los logs aparecen excepciones sobre tokens que han expirado.
</question>
<generated_query>
OAuth autenticación fallo intermitente error 500 token expirado
</generated_query>
</example>
</examples>

IMPORTANTE: Los ejemplos anteriores son solo para ilustrar el formato. NO debes asumir que esa información está disponible para ti.

Ahora, optimiza la siguiente consulta de incidencia:

<user_query>
{query}
</user_query>

Responde ÚNICAMENTE con la consulta optimizada, sin explicaciones adicionales ni formato especial. La consulta debe estar en el mismo idioma que la consulta original."""

            # Construir mensaje para Claude
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 500,
                "temperature": 0.1,  # Temperatura muy baja para consistencia
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": optimization_prompt.format(query=user_query)
                            }
                        ]
                    }
                ]
            }
            
            # Invocar modelo
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body)
            )
            
            # Parsear respuesta
            response_body = json.loads(response["body"].read())
            
            # Extraer texto optimizado
            optimized_query = ""
            for item in response_body.get("content", []):
                if item.get("type") == "text":
                    optimized_query += item.get("text", "")
            
            # Limpiar la respuesta (eliminar posibles marcadores de código o espacios extra)
            optimized_query = optimized_query.strip()
            
            # Si la optimización falla o está vacía, usar la consulta original
            if not optimized_query or len(optimized_query) < 10:
                logger.warning("Optimización de consulta produjo resultado vacío, usando consulta original")
                return user_query
            
            logger.info(f"Consulta optimizada exitosamente: '{optimized_query}'")
            return optimized_query
            
        except Exception as e:
            logger.error(f"Error optimizando consulta: {str(e)}")
            logger.warning("Usando consulta original debido al error")
            return user_query
    
    def _search_similar_incidents(
        self,
        query: str,
        max_results: int = 5
    ) -> List[SimilarIncident]:
        """
        Busca incidencias similares en la Knowledge Base
        
        Args:
            query: Descripción de la incidencia a buscar
            max_results: Número máximo de resultados
            
        Returns:
            Lista de incidencias similares
        """
        try:
            logger.info("Buscando incidencias similares en Knowledge Base...")
            
            response = self.bedrock_agent.retrieve(
                knowledgeBaseId=self.knowledge_base_id,
                retrievalQuery={
                    "text": query
                },
                retrievalConfiguration={
                    "vectorSearchConfiguration": {
                        "numberOfResults": max_results,
                        "overrideSearchType": "HYBRID"  # Búsqueda híbrida (semántica + keyword)
                    }
                }
            )
            
            similar_incidents = []
            
            for result in response.get("retrievalResults", []):
                content = result.get("content", {}).get("text", "")
                score = result.get("score", 0.0)
                metadata = result.get("metadata", {})
                
                # Parsear metadata JSON si existe
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except json.JSONDecodeError:
                        metadata = {}
                
                # Extraer información de la incidencia
                incident = SimilarIncident(
                    incident_id=metadata.get("incident_id", "unknown"),
                    title=metadata.get("title", "Sin título"),
                    description=content,
                    resolution=metadata.get("resolution", ""),
                    similarity_score=score,
                    metadata=metadata
                )
                
                similar_incidents.append(incident)
                
                logger.debug(f"Incidencia similar: {incident.incident_id} (score: {score:.3f})")
            
            return similar_incidents
            
        except ClientError as e:
            logger.error(f"Error buscando en Knowledge Base: {str(e)}")
            raise
    
    def _get_incident_attachments(self, incident_id: str) -> List[str]:
        """
        Recupera la lista de archivos adjuntos de una incidencia desde S3
        
        Args:
            incident_id: ID de la incidencia
            
        Returns:
            Lista de nombres de archivos adjuntos
        """
        try:
            prefix = f"incidents-files/{incident_id}_"
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.s3_bucket,
                Prefix=prefix
            )
            
            attachments = []
            for obj in response.get("Contents", []):
                key = obj["Key"]
                filename = key.split("/")[-1]
                attachments.append(filename)
            
            logger.debug(f"Archivos adjuntos para {incident_id}: {len(attachments)}")
            
            return attachments
            
        except ClientError as e:
            logger.warning(f"Error recuperando adjuntos de {incident_id}: {str(e)}")
            return []
    
    def _build_analysis_context(
        self,
        request: IncidentAnalysisRequest,
        similar_incidents: List[SimilarIncident]
    ) -> str:
        """
        Construye el contexto para el análisis de Claude
        
        Args:
            request: Solicitud original
            similar_incidents: Incidencias similares encontradas
            
        Returns:
            Contexto formateado para Claude
        """
        context_parts = [
            "# ANÁLISIS DE INCIDENCIA",
            "",
            "## Incidencia Actual",
            f"**Descripción:** {request.incident_description}",
            ""
        ]
        
        if similar_incidents:
            context_parts.extend([
                "## Incidencias Históricas Similares",
                ""
            ])
            
            for i, incident in enumerate(similar_incidents, 1):
                context_parts.extend([
                    f"### Incidencia Similar #{i}",
                    f"**ID:** {incident.incident_id}",
                    f"**Título:** {incident.title}",
                    f"**Similitud:** {incident.similarity_score:.1%}",
                    f"**Descripción:** {incident.description}",
                    f"**Resolución:** {incident.resolution}",
                    ""
                ])
                
                if incident.attachments:
                    context_parts.append(f"**Archivos adjuntos:** {', '.join(incident.attachments)}")
                    context_parts.append("")
                
                # Agregar metadata relevante
                if incident.metadata:
                    if "severity" in incident.metadata:
                        context_parts.append(f"**Severidad:** {incident.metadata['severity']}")
                    if "category" in incident.metadata:
                        context_parts.append(f"**Categoría:** {incident.metadata['category']}")
                    if "resolution_time" in incident.metadata:
                        context_parts.append(f"**Tiempo de resolución:** {incident.metadata['resolution_time']}")
                    context_parts.append("")
        
        return "\n".join(context_parts)
    
    def _invoke_claude_analysis(self, context: str) -> Dict[str, Any]:
        """
        Invoca Claude para realizar el análisis
        
        Args:
            context: Contexto con la incidencia y casos similares
            
        Returns:
            Respuesta de Claude
        """
        try:
            logger.info("Invocando Claude para análisis...")
            
            # Prompt para el análisis
            analysis_prompt = f"""Basándote en la incidencia actual y las incidencias históricas similares proporcionadas, realiza un análisis detallado y proporciona:

1. **DIAGNÓSTICO**: Un diagnóstico claro del problema basado en los patrones observados
2. **CAUSA RAÍZ**: Identifica la causa raíz más probable del problema
3. **ACCIONES RECOMENDADAS**: Lista de acciones concretas para resolver la incidencia (mínimo 3, máximo 7)
4. **CONFIANZA**: Un score de confianza del análisis (0.0 a 1.0)

Formato de respuesta (JSON):
```json
{{
  "diagnosis": "Diagnóstico detallado aquí",
  "root_cause": "Causa raíz identificada",
  "recommended_actions": [
    "Acción 1",
    "Acción 2",
    "Acción 3"
  ],
  "confidence_score": 0.85
}}
```

{context}

Proporciona tu análisis en formato JSON como se especifica arriba."""

            # Construir mensaje para Claude
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "temperature": 0.3,  # Temperatura baja para análisis más determinista
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": analysis_prompt
                            }
                        ]
                    }
                ]
            }
            
            # Invocar modelo
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body)
            )
            
            # Parsear respuesta
            response_body = json.loads(response["body"].read())
            
            logger.info("Análisis de Claude completado")
            
            return response_body
            
        except ClientError as e:
            logger.error(f"Error invocando Claude: {str(e)}")
            raise
    
    def _parse_analysis_response(
        self,
        claude_response: Dict[str, Any],
        similar_incidents: List[SimilarIncident]
    ) -> IncidentAnalysisResponse:
        """
        Parsea la respuesta de Claude y construye el objeto de respuesta
        
        Args:
            claude_response: Respuesta raw de Claude
            similar_incidents: Incidencias similares encontradas
            
        Returns:
            Respuesta estructurada del análisis
        """
        try:
            # Extraer texto de la respuesta
            content = claude_response.get("content", [])
            text_response = ""
            
            for item in content:
                if item.get("type") == "text":
                    text_response += item.get("text", "")
            
            # Extraer JSON de la respuesta
            # Claude puede envolver el JSON en ```json ... ```
            json_start = text_response.find("{")
            json_end = text_response.rfind("}") + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = text_response[json_start:json_end]
                analysis_data = json.loads(json_str)
            else:
                raise ValueError("No se encontró JSON válido en la respuesta de Claude")
            
            # Extraer tokens
            usage = claude_response.get("usage", {})
            
            # Construir respuesta
            response = IncidentAnalysisResponse(
                diagnosis=analysis_data.get("diagnosis", "No se pudo determinar"),
                root_cause=analysis_data.get("root_cause", "No se pudo determinar"),
                recommended_actions=analysis_data.get("recommended_actions", []),
                similar_incidents=similar_incidents,
                confidence_score=analysis_data.get("confidence_score", 0.5),
                model_id=self.model_id,
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0)
            )
            
            return response
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error parseando respuesta de Claude: {str(e)}")
            logger.debug(f"Respuesta raw: {text_response}")
            
            # Respuesta de fallback
            return IncidentAnalysisResponse(
                diagnosis="Error al parsear la respuesta del modelo",
                root_cause="No disponible",
                recommended_actions=["Revisar logs del sistema", "Contactar soporte técnico"],
                similar_incidents=similar_incidents,
                confidence_score=0.0,
                model_id=self.model_id,
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0)
            )
