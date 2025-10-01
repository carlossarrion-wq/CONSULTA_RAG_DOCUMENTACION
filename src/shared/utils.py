"""
Utilidades compartidas
"""
import base64
import mimetypes
import os
from pathlib import Path
from typing import Optional, Tuple
import logging

from .models import DocumentType

logger = logging.getLogger(__name__)


def get_file_size(file_path: str) -> int:
    """
    Obtiene el tamaño de un archivo en bytes
    
    Args:
        file_path: Ruta al archivo
        
    Returns:
        Tamaño en bytes
    """
    return os.path.getsize(file_path)


def encode_file_to_base64(file_path: str) -> str:
    """
    Codifica un archivo a base64
    
    Args:
        file_path: Ruta al archivo
        
    Returns:
        Contenido del archivo en base64
    """
    with open(file_path, "rb") as file:
        return base64.b64encode(file.read()).decode("utf-8")


def get_mime_type(file_path: str) -> Optional[str]:
    """
    Obtiene el tipo MIME de un archivo
    
    Args:
        file_path: Ruta al archivo
        
    Returns:
        Tipo MIME o None si no se puede determinar
    """
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type


def detect_document_type(file_path: str) -> DocumentType:
    """
    Detecta el tipo de documento basándose en la extensión
    
    Args:
        file_path: Ruta al archivo
        
    Returns:
        Tipo de documento
    """
    extension = Path(file_path).suffix.lower()
    
    type_mapping = {
        '.pdf': DocumentType.PDF,
        '.jpg': DocumentType.IMAGE,
        '.jpeg': DocumentType.IMAGE,
        '.png': DocumentType.IMAGE,
        '.gif': DocumentType.IMAGE,
        '.webp': DocumentType.IMAGE,
        '.xlsx': DocumentType.EXCEL,
        '.xls': DocumentType.EXCEL,
        '.csv': DocumentType.EXCEL,
        '.docx': DocumentType.WORD,
        '.doc': DocumentType.WORD,
        '.txt': DocumentType.TEXT,
        '.md': DocumentType.TEXT,
    }
    
    return type_mapping.get(extension, DocumentType.UNKNOWN)


def validate_file_size(file_path: str, max_size_mb: int = 32) -> Tuple[bool, str]:
    """
    Valida que el tamaño del archivo no exceda el límite
    
    Args:
        file_path: Ruta al archivo
        max_size_mb: Tamaño máximo en MB
        
    Returns:
        Tupla (es_válido, mensaje)
    """
    size_bytes = get_file_size(file_path)
    size_mb = size_bytes / (1024 * 1024)
    
    if size_mb > max_size_mb:
        return False, f"El archivo excede el tamaño máximo de {max_size_mb}MB (tamaño: {size_mb:.2f}MB)"
    
    return True, f"Tamaño válido: {size_mb:.2f}MB"


def validate_image_file(file_path: str) -> Tuple[bool, str]:
    """
    Valida un archivo de imagen para Bedrock
    
    Args:
        file_path: Ruta al archivo
        
    Returns:
        Tupla (es_válido, mensaje)
    """
    # Validar extensión
    extension = Path(file_path).suffix.lower()
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    
    if extension not in valid_extensions:
        return False, f"Extensión no válida. Extensiones permitidas: {', '.join(valid_extensions)}"
    
    # Validar tamaño (máximo 5MB para imágenes)
    return validate_file_size(file_path, max_size_mb=5)


def validate_pdf_file(file_path: str) -> Tuple[bool, str]:
    """
    Valida un archivo PDF para Bedrock
    
    Args:
        file_path: Ruta al archivo
        
    Returns:
        Tupla (es_válido, mensaje)
    """
    # Validar extensión
    if not file_path.lower().endswith('.pdf'):
        return False, "El archivo debe tener extensión .pdf"
    
    # Validar tamaño (máximo 32MB para PDFs)
    return validate_file_size(file_path, max_size_mb=32)


def format_file_size(size_bytes: int) -> str:
    """
    Formatea el tamaño de un archivo de forma legible
    
    Args:
        size_bytes: Tamaño en bytes
        
    Returns:
        Tamaño formateado (ej: "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def setup_logging(level: str = "INFO") -> None:
    """
    Configura el sistema de logging
    
    Args:
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
