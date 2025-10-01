"""
Cliente para AWS Bedrock (versión Lambda)
"""
import json
import logging
from typing import List, Dict, Any

import boto3
from botocore.exceptions import ClientError

from ..shared.models import Document, QueryRequest, QueryResponse, BedrockConfig, DocumentType

logger = logging.getLogger(__name__)


class BedrockClient:
    """Cliente para interactuar con AWS Bedrock desde Lambda"""
    
    def __init__(self, config: BedrockConfig):
        """
        Inicializa el cliente de Bedrock
        
        Args:
            config: Configuración de Bedrock
        """
        self.config = config
        
        # En Lambda, usar las credenciales del rol de ejecución
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=config.region
        )
        
        logger.info(f"Cliente Bedrock inicializado - Región: {config.region}, Modelo: {config.model_id}")
    
    def invoke_model(self, request: QueryRequest) -> QueryResponse:
        """
        Invoca el modelo de Bedrock con la consulta y documentos
        
        Args:
            request: Solicitud de consulta
            
        Returns:
            Respuesta del modelo
            
        Raises:
            Exception: Si hay error en la invocación
        """
        try:
            # Construir el mensaje para Claude
            messages = self._build_messages(request)
            
            # Construir el body de la solicitud
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "messages": messages
            }
            
            logger.info(f"Invocando modelo {self.config.model_id}...")
            logger.debug(f"Número de documentos: {len(request.documents)}")
            
            # Invocar el modelo
            response = self.client.invoke_model(
                modelId=self.config.model_id,
                body=json.dumps(body)
            )
            
            # Parsear respuesta
            response_body = json.loads(response["body"].read())
            
            # Extraer información
            content = response_body.get("content", [])
            text_response = ""
            
            for item in content:
                if item.get("type") == "text":
                    text_response += item.get("text", "")
            
            usage = response_body.get("usage", {})
            
            result = QueryResponse(
                response=text_response,
                model_id=self.config.model_id,
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                stop_reason=response_body.get("stop_reason"),
                metadata={
                    "model": response_body.get("model"),
                    "role": response_body.get("role")
                }
            )
            
            logger.info(f"✓ Respuesta recibida - Tokens entrada: {result.input_tokens}, salida: {result.output_tokens}")
            
            return result
            
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            logger.error(f"Error de AWS: {error_code} - {error_message}")
            raise Exception(f"Error invocando Bedrock: {error_message}")
        except Exception as e:
            logger.error(f"Error inesperado: {str(e)}")
            raise
    
    def _build_messages(self, request: QueryRequest) -> List[Dict[str, Any]]:
        """
        Construye los mensajes en formato Claude para Bedrock
        
        Args:
            request: Solicitud de consulta
            
        Returns:
            Lista de mensajes formateados
        """
        content = []
        
        # Agregar documentos primero
        for doc in request.documents:
            if doc.document_type == DocumentType.PDF and doc.base64_content:
                # PDF como documento
                content.append({
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": doc.base64_content
                    }
                })
                logger.debug(f"Agregado PDF: {doc.file_name}")
                
            elif doc.document_type == DocumentType.IMAGE and doc.base64_content:
                # Imagen
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": doc.mime_type or "image/jpeg",
                        "data": doc.base64_content
                    }
                })
                logger.debug(f"Agregada imagen: {doc.file_name}")
                
            elif doc.content:
                # Texto extraído (Excel, Word, Text)
                content.append({
                    "type": "text",
                    "text": f"=== Contenido de {doc.file_name} ===\n\n{doc.content}"
                })
                logger.debug(f"Agregado texto de: {doc.file_name}")
        
        # Agregar el prompt del usuario al final
        content.append({
            "type": "text",
            "text": request.prompt
        })
        
        # Construir mensaje
        messages = [
            {
                "role": "user",
                "content": content
            }
        ]
        
        return messages
