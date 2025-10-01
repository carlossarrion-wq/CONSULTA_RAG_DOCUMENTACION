"""
Configuración para el CLI
"""
import os
from pathlib import Path
from dotenv import load_dotenv

from ..shared.models import BedrockConfig

# Cargar variables de entorno
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


def get_bedrock_config() -> BedrockConfig:
    """
    Obtiene la configuración de Bedrock desde variables de entorno
    
    Returns:
        Configuración de Bedrock
    """
    return BedrockConfig(
        region=os.getenv("AWS_REGION", "eu-west-1"),
        model_id=os.getenv(
            "BEDROCK_MODEL_ID",
            "eu.anthropic.claude-sonnet-4-5-20250929-v1:0"
        ),
        max_tokens=int(os.getenv("BEDROCK_MAX_TOKENS", "4096")),
        temperature=float(os.getenv("BEDROCK_TEMPERATURE", "0.7")),
        profile_name=os.getenv("AWS_PROFILE")
    )


def get_log_level() -> str:
    """
    Obtiene el nivel de logging desde variables de entorno
    
    Returns:
        Nivel de logging
    """
    return os.getenv("LOG_LEVEL", "INFO")
