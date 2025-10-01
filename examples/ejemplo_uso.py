"""
Ejemplo de uso del sistema de consultas RAG con AWS Bedrock
"""
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.shared.models import QueryRequest, Document, DocumentType
from src.shared.document_processor import DocumentProcessor
from src.cli.bedrock_client import BedrockClient
from src.cli.config import get_bedrock_config


def ejemplo_consulta_simple():
    """Ejemplo de consulta simple sin documentos"""
    print("=" * 80)
    print("EJEMPLO 1: Consulta Simple")
    print("=" * 80)
    
    # Configuración
    config = get_bedrock_config()
    client = BedrockClient(config)
    
    # Crear request
    request = QueryRequest(
        prompt="¿Cuál es la capital de España y cuántos habitantes tiene aproximadamente?",
        documents=[],
        max_tokens=1000,
        temperature=0.7
    )
    
    # Invocar modelo
    response = client.invoke_model(request)
    
    print(f"\nRespuesta:\n{response.response}")
    print(f"\nTokens: {response.input_tokens} entrada, {response.output_tokens} salida")


def ejemplo_con_documento():
    """Ejemplo de consulta con un documento"""
    print("\n" + "=" * 80)
    print("EJEMPLO 2: Consulta con Documento")
    print("=" * 80)
    
    # Nota: Este ejemplo requiere que tengas un archivo de prueba
    # Puedes crear un archivo de texto simple para probar
    
    archivo_ejemplo = Path(__file__).parent / "sample.txt"
    
    if not archivo_ejemplo.exists():
        print("\nCreando archivo de ejemplo...")
        with open(archivo_ejemplo, 'w', encoding='utf-8') as f:
            f.write("""
Informe de Ventas Q4 2024

Resumen Ejecutivo:
Las ventas del cuarto trimestre de 2024 alcanzaron los 2.5 millones de euros,
representando un crecimiento del 15% respecto al trimestre anterior.

Principales Logros:
- Incremento del 20% en ventas online
- Expansión a 3 nuevos mercados
- Lanzamiento exitoso de 5 nuevos productos

Desafíos:
- Competencia creciente en el sector
- Necesidad de optimizar la cadena de suministro
            """)
        print(f"✓ Archivo creado: {archivo_ejemplo}")
    
    # Procesar documento
    processor = DocumentProcessor()
    documento = processor.process_document(str(archivo_ejemplo))
    
    # Configuración
    config = get_bedrock_config()
    client = BedrockClient(config)
    
    # Crear request
    request = QueryRequest(
        prompt="Resume los puntos clave de este informe y sugiere 3 acciones prioritarias",
        documents=[documento],
        max_tokens=2000,
        temperature=0.7
    )
    
    # Invocar modelo
    response = client.invoke_model(request)
    
    print(f"\nRespuesta:\n{response.response}")
    print(f"\nTokens: {response.input_tokens} entrada, {response.output_tokens} salida")


def ejemplo_validacion():
    """Ejemplo de validación de archivos"""
    print("\n" + "=" * 80)
    print("EJEMPLO 3: Validación de Archivos")
    print("=" * 80)
    
    processor = DocumentProcessor()
    
    # Crear archivo de ejemplo si no existe
    archivo_ejemplo = Path(__file__).parent / "sample.txt"
    if not archivo_ejemplo.exists():
        with open(archivo_ejemplo, 'w', encoding='utf-8') as f:
            f.write("Este es un archivo de prueba.")
    
    try:
        doc = processor.process_document(str(archivo_ejemplo))
        print(f"\n✓ Archivo válido: {doc.file_name}")
        print(f"  Tipo: {doc.document_type}")
        print(f"  Tamaño: {doc.size_bytes} bytes")
        print(f"  MIME: {doc.mime_type}")
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")


if __name__ == "__main__":
    print("\n🚀 Ejemplos de Uso - Sistema RAG con AWS Bedrock\n")
    
    try:
        # Ejemplo 1: Consulta simple
        ejemplo_consulta_simple()
        
        # Ejemplo 2: Consulta con documento
        ejemplo_con_documento()
        
        # Ejemplo 3: Validación
        ejemplo_validacion()
        
        print("\n" + "=" * 80)
        print("✓ Todos los ejemplos completados exitosamente")
        print("=" * 80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
