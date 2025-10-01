"""
Modelos de datos compartidos
"""
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """Tipos de documentos soportados"""
    PDF = "pdf"
    IMAGE = "image"
    EXCEL = "excel"
    WORD = "word"
    TEXT = "text"
    UNKNOWN = "unknown"


class Document(BaseModel):
    """Modelo para un documento"""
    file_path: str
    file_name: str
    document_type: DocumentType
    content: Optional[str] = None
    base64_content: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: int = 0
    
    class Config:
        use_enum_values = True


class QueryRequest(BaseModel):
    """Modelo para una solicitud de consulta"""
    prompt: str = Field(..., description="Pregunta o prompt del usuario")
    documents: List[Document] = Field(default_factory=list, description="Lista de documentos adjuntos")
    max_tokens: int = Field(default=4096, description="Máximo de tokens en la respuesta")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0, description="Temperatura del modelo")
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "¿Qué información contienen estos documentos?",
                "documents": [],
                "max_tokens": 4096,
                "temperature": 0.7
            }
        }


class QueryResponse(BaseModel):
    """Modelo para la respuesta de una consulta"""
    response: str = Field(..., description="Respuesta del modelo")
    model_id: str = Field(..., description="ID del modelo utilizado")
    input_tokens: int = Field(default=0, description="Tokens de entrada")
    output_tokens: int = Field(default=0, description="Tokens de salida")
    stop_reason: Optional[str] = Field(None, description="Razón de parada")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadatos adicionales")
    
    class Config:
        json_schema_extra = {
            "example": {
                "response": "Basándome en los documentos proporcionados...",
                "model_id": "eu.anthropic.claude-sonnet-4-5-20250929-v1:0",
                "input_tokens": 1500,
                "output_tokens": 500,
                "stop_reason": "end_turn"
            }
        }


class BedrockConfig(BaseModel):
    """Configuración para AWS Bedrock"""
    region: str = Field(default="eu-west-1", description="Región de AWS")
    model_id: str = Field(
        default="eu.anthropic.claude-sonnet-4-5-20250929-v1:0",
        description="ID del modelo en Bedrock"
    )
    max_tokens: int = Field(default=4096, description="Máximo de tokens")
    temperature: float = Field(default=0.7, description="Temperatura")
    profile_name: Optional[str] = Field(default=None, description="Perfil de AWS")
