"""
Lambda handler para análisis de incidencias con RAG
"""
import json
import logging
import os
from typing import Dict, Any

from incident_analyzer import (
    IncidentAnalyzer,
    IncidentAnalysisRequest,
    IncidentAnalysisResponse,
    SimilarIncident
)

# Configurar logging
logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handler principal de Lambda para análisis de incidencias
    
    Args:
        event: Evento de Lambda (API Gateway)
        context: Contexto de Lambda
        
    Returns:
        Respuesta HTTP con el análisis
    """
    try:
        logger.info("Iniciando análisis de incidencia")
        
        # Parsear el body del request
        if isinstance(event.get("body"), str):
            body = json.loads(event["body"])
        else:
            body = event.get("body", event)
        
        # Validar request
        if "incident_description" not in body:
            return create_response(400, {
                "error": "El campo 'incident_description' es requerido"
            })
        
        # Obtener configuración desde variables de entorno
        knowledge_base_id = os.getenv("KNOWLEDGE_BASE_ID")
        s3_bucket = os.getenv("S3_BUCKET")
        model_id = os.getenv(
            "BEDROCK_MODEL_ID",
            "eu.anthropic.claude-sonnet-4-5-20250929-v1:0"
        )
        region = os.getenv("AWS_REGION", "eu-west-1")
        
        if not knowledge_base_id:
            return create_response(500, {
                "error": "KNOWLEDGE_BASE_ID no configurado"
            })
        
        if not s3_bucket:
            return create_response(500, {
                "error": "S3_BUCKET no configurado"
            })
        
        # Crear request de análisis
        analysis_request = IncidentAnalysisRequest(
            incident_description=body["incident_description"],
            incident_id=body.get("incident_id"),
            max_similar_incidents=body.get("max_similar_incidents", 5),
            include_attachments=body.get("include_attachments", True),
            optimize_query=body.get("optimize_query", True)
        )
        
        logger.info(f"Analizando incidencia: {analysis_request.incident_id or 'nueva'}")
        
        # Inicializar analizador
        analyzer = IncidentAnalyzer(
            knowledge_base_id=knowledge_base_id,
            s3_bucket=s3_bucket,
            model_id=model_id,
            region=region
        )
        
        # Realizar análisis
        response = analyzer.analyze_incident(analysis_request)
        
        # Preparar respuesta
        response_data = {
            "diagnosis": response.diagnosis,
            "root_cause": response.root_cause,
            "recommended_actions": response.recommended_actions,
            "confidence_score": response.confidence_score,
            "original_query": response.original_query,
            "optimized_query": response.optimized_query,
            "similar_incidents": [
                {
                    "incident_id": inc.incident_id,
                    "title": inc.title,
                    "description": inc.description,
                    "resolution": inc.resolution,
                    "similarity_score": inc.similarity_score,
                    "attachments": inc.attachments,
                    "metadata": inc.metadata
                }
                for inc in response.similar_incidents
            ],
            "model_info": {
                "model_id": response.model_id,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "total_tokens": response.input_tokens + response.output_tokens
            }
        }
        
        logger.info(
            f"Análisis completado - Confianza: {response.confidence_score:.2f}, "
            f"Tokens: {response.input_tokens + response.output_tokens}"
        )
        
        return create_response(200, response_data)
        
    except ValueError as e:
        logger.error(f"Error de validación: {str(e)}")
        return create_response(400, {"error": str(e)})
        
    except Exception as e:
        logger.error(f"Error procesando análisis: {str(e)}", exc_info=True)
        return create_response(500, {"error": f"Error interno: {str(e)}"})


def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea una respuesta HTTP formateada para API Gateway
    
    Args:
        status_code: Código de estado HTTP
        body: Cuerpo de la respuesta
        
    Returns:
        Respuesta formateada
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "POST, OPTIONS"
        },
        "body": json.dumps(body, ensure_ascii=False, default=str)
    }


def health_check_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handler para health check
    
    Args:
        event: Evento de Lambda
        context: Contexto de Lambda
        
    Returns:
        Respuesta de health check
    """
    # Verificar configuración
    knowledge_base_id = os.getenv("KNOWLEDGE_BASE_ID")
    s3_bucket = os.getenv("S3_BUCKET")
    
    status = "healthy"
    issues = []
    
    if not knowledge_base_id:
        status = "degraded"
        issues.append("KNOWLEDGE_BASE_ID no configurado")
    
    if not s3_bucket:
        status = "degraded"
        issues.append("S3_BUCKET no configurado")
    
    return create_response(200, {
        "status": status,
        "service": "incident-analyzer",
        "version": "1.0.0",
        "configuration": {
            "knowledge_base_configured": bool(knowledge_base_id),
            "s3_bucket_configured": bool(s3_bucket),
            "model_id": os.getenv("BEDROCK_MODEL_ID", "default"),
            "region": os.getenv("AWS_REGION", "eu-west-1")
        },
        "issues": issues if issues else None
    })
