"""
Lambda handler para consultas RAG con AWS Bedrock
"""
import json
import logging
import os
from typing import Dict, Any

from ..shared.models import QueryRequest, QueryResponse, BedrockConfig
from ..shared.document_processor import DocumentProcessor
from .bedrock_client import BedrockClient

# Configurar logging
logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handler principal de Lambda
    
    Args:
        event: Evento de Lambda (API Gateway o invocación directa)
        context: Contexto de Lambda
        
    Returns:
        Respuesta HTTP
    """
    try:
        logger.info("Iniciando procesamiento de consulta RAG")
        
        # Parsear el body del request
        if isinstance(event.get("body"), str):
            body = json.loads(event["body"])
        else:
            body = event.get("body", event)
        
        # Validar request
        if "prompt" not in body:
            return create_response(400, {"error": "El campo 'prompt' es requerido"})
        
        # Crear configuración de Bedrock
        config = BedrockConfig(
            region=os.getenv("AWS_REGION", "eu-west-1"),
            model_id=os.getenv(
                "BEDROCK_MODEL_ID",
                "eu.anthropic.claude-sonnet-4-5-20250929-v1:0"
            ),
            max_tokens=body.get("max_tokens", int(os.getenv("BEDROCK_MAX_TOKENS", "4096"))),
            temperature=body.get("temperature", float(os.getenv("BEDROCK_TEMPERATURE", "0.7")))
        )
        
        # Procesar documentos si existen
        documents = []
        if "documents" in body:
            processor = DocumentProcessor()
            for doc_data in body["documents"]:
                # Los documentos deben venir con base64_content o content ya procesados
                # desde el cliente, ya que Lambda no tiene acceso al filesystem local
                from ..shared.models import Document, DocumentType
                
                doc = Document(
                    file_path=doc_data.get("file_path", ""),
                    file_name=doc_data.get("file_name", "unknown"),
                    document_type=DocumentType(doc_data.get("document_type", "text")),
                    content=doc_data.get("content"),
                    base64_content=doc_data.get("base64_content"),
                    mime_type=doc_data.get("mime_type"),
                    size_bytes=doc_data.get("size_bytes", 0)
                )
                documents.append(doc)
        
        # Crear request
        request = QueryRequest(
            prompt=body["prompt"],
            documents=documents,
            max_tokens=config.max_tokens,
            temperature=config.temperature
        )
        
        logger.info(f"Procesando consulta con {len(documents)} documentos")
        
        # Invocar Bedrock
        client = BedrockClient(config)
        response = client.invoke_model(request)
        
        # Preparar respuesta
        response_data = {
            "response": response.response,
            "model_id": response.model_id,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "stop_reason": response.stop_reason,
            "metadata": response.metadata
        }
        
        logger.info(f"Consulta procesada exitosamente - Tokens: {response.input_tokens + response.output_tokens}")
        
        return create_response(200, response_data)
        
    except Exception as e:
        logger.error(f"Error procesando consulta: {str(e)}", exc_info=True)
        return create_response(500, {"error": str(e)})


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
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "POST, OPTIONS"
        },
        "body": json.dumps(body, ensure_ascii=False)
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
    return create_response(200, {
        "status": "healthy",
        "service": "consulta-rag-bedrock",
        "version": "1.0.0"
    })
