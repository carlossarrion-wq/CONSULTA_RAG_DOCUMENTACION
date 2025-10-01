# Consulta RAG con AWS Bedrock

Sistema de consultas RAG (Retrieval-Augmented Generation) que permite realizar preguntas a Claude 3.5 Sonnet en AWS Bedrock incluyendo documentos de múltiples formatos como contexto.

## 🚀 Características

- ✅ **Multi-modal**: Soporte para PDF, imágenes (JPG, PNG, GIF, WebP), Excel, Word y texto
- ✅ **Dos modos de operación**: CLI local o Lambda con API Gateway
- ✅ **Procesamiento inteligente**: Conversión automática de formatos no soportados nativamente
- ✅ **Claude 3.5 Sonnet**: Modelo de última generación en AWS Bedrock
- ✅ **Interfaz rica**: CLI con colores y formato Markdown
- ✅ **Validación**: Verificación de archivos antes del procesamiento

## 📋 Requisitos

- Python 3.11+
- AWS CLI configurado con credenciales
- Acceso a AWS Bedrock en la región `eu-west-1`
- (Opcional) AWS SAM CLI para despliegue de Lambda

## 🛠️ Instalación

### 1. Clonar el repositorio

```bash
git clone <repository-url>
cd CONSULTA_RAG_DOCUMENTACION
```

### 2. Crear entorno virtual

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tu configuración
```

Variables disponibles en `.env`:

```bash
# AWS Configuration
AWS_REGION=eu-west-1
AWS_PROFILE=default

# Bedrock Configuration
BEDROCK_MODEL_ID=eu.anthropic.claude-sonnet-4-5-20250929-v1:0
BEDROCK_MAX_TOKENS=4096
BEDROCK_TEMPERATURE=0.7

# Logging
LOG_LEVEL=INFO
```

## 🎯 Uso

### Opción 1: CLI Local (Recomendado para pruebas)

#### Probar conexión con Bedrock

```bash
python -m src.cli.main test
```

#### Realizar una consulta simple

```bash
python -m src.cli.main query -p "¿Cuál es la capital de Francia?"
```

#### Consulta con documentos

```bash
python -m src.cli.main query \
  -p "Resume el contenido de estos documentos" \
  -f documento.pdf \
  -f imagen.jpg \
  -f datos.xlsx
```

#### Consulta con parámetros personalizados

```bash
python -m src.cli.main query \
  -p "Analiza estos datos" \
  -f reporte.pdf \
  --max-tokens 8000 \
  --temperature 0.5 \
  --verbose
```

#### Validar archivos antes de enviar

```bash
python -m src.cli.main validate documento.pdf imagen.jpg datos.xlsx
```

### Opción 2: Lambda con API Gateway

#### Desplegar Lambda

```bash
cd infrastructure
./deploy.sh
```

El script creará:
- Función Lambda
- API Gateway
- Roles y permisos IAM
- CloudWatch Logs

#### Usar la API

```bash
# Health check
curl https://your-api-url/prod/health

# Consulta simple
curl -X POST https://your-api-url/prod/query \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt": "¿Cuál es la capital de España?",
    "max_tokens": 4096,
    "temperature": 0.7
  }'

# Consulta con documentos (documentos deben estar en base64)
curl -X POST https://your-api-url/prod/query \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt": "Resume este documento",
    "documents": [
      {
        "file_name": "doc.pdf",
        "document_type": "pdf",
        "base64_content": "JVBERi0xLjQK...",
        "mime_type": "application/pdf"
      }
    ]
  }'
```

## 📁 Estructura del Proyecto

```
CONSULTA_RAG_DOCUMENTACION/
├── src/
│   ├── cli/                    # Aplicación CLI
│   │   ├── main.py            # Punto de entrada CLI
│   │   ├── bedrock_client.py  # Cliente Bedrock
│   │   └── config.py          # Configuración
│   │
│   ├── lambda/                 # Función Lambda
│   │   ├── handler.py         # Lambda handler
│   │   ├── bedrock_client.py  # Cliente Bedrock
│   │   └── requirements.txt   # Dependencias Lambda
│   │
│   └── shared/                 # Código compartido
│       ├── models.py          # Modelos de datos
│       ├── document_processor.py  # Procesamiento de documentos
│       └── utils.py           # Utilidades
│
├── infrastructure/             # IaC para Lambda
│   ├── template.yaml          # SAM template
│   └── deploy.sh              # Script de despliegue
│
├── requirements.txt            # Dependencias del proyecto
├── .env.example               # Ejemplo de configuración
└── README.md                  # Este archivo
```

## 🔧 Tipos de Documentos Soportados

### Procesamiento Nativo (Claude)
- **PDF**: Hasta 32MB, máximo 100 páginas
- **Imágenes**: JPG, PNG, GIF, WebP (hasta 5MB)

### Procesamiento con Conversión
- **Excel**: .xlsx, .xls, .csv → Convertido a texto
- **Word**: .docx, .doc → Extraído como texto
- **Texto**: .txt, .md → Leído directamente

## 📊 Ejemplos de Uso

### Análisis de documentos PDF

```bash
python -m src.cli.main query \
  -p "Extrae los puntos clave de este informe" \
  -f informe_anual.pdf
```

### Análisis de imágenes

```bash
python -m src.cli.main query \
  -p "Describe lo que ves en esta imagen" \
  -f grafico.png
```

### Análisis de datos Excel

```bash
python -m src.cli.main query \
  -p "Resume las tendencias en estos datos" \
  -f ventas_2024.xlsx
```

### Múltiples documentos

```bash
python -m src.cli.main query \
  -p "Compara la información de estos documentos" \
  -f doc1.pdf \
  -f doc2.pdf \
  -f imagen.jpg
```

## 🔐 Permisos AWS Requeridos

Para usar este sistema, necesitas los siguientes permisos en AWS:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:ListFoundationModels"
      ],
      "Resource": "*"
    }
  ]
}
```

## 🐛 Troubleshooting

### Error: "No module named 'src'"

Asegúrate de ejecutar los comandos desde el directorio raíz del proyecto:

```bash
cd CONSULTA_RAG_DOCUMENTACION
python -m src.cli.main query -p "test"
```

### Error: "AccessDeniedException"

Verifica que:
1. Tus credenciales AWS están configuradas correctamente
2. Tienes acceso a Bedrock en la región `eu-west-1`
3. El modelo Claude está habilitado en tu cuenta

### Error: "File size exceeds limit"

Los límites son:
- PDFs: 32MB
- Imágenes: 5MB

Reduce el tamaño del archivo antes de procesarlo.

### Error al instalar dependencias

Si tienes problemas con `pdfplumber` o `Pillow`:

```bash
# macOS
brew install poppler

# Ubuntu/Debian
sudo apt-get install poppler-utils

# Windows
# Descargar poppler desde: https://github.com/oschwartz10612/poppler-windows
```

## 📈 Costos

El uso de este sistema genera costos en AWS:

- **Bedrock**: Cobro por tokens de entrada y salida
- **Lambda** (si se usa): Cobro por invocaciones y tiempo de ejecución
- **API Gateway** (si se usa): Cobro por requests
- **CloudWatch Logs**: Cobro por almacenamiento de logs

Consulta la [calculadora de precios de AWS](https://calculator.aws/) para estimar costos.

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 🔗 Enlaces Útiles

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Claude API Documentation](https://docs.anthropic.com/claude/reference/getting-started-with-the-api)
- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)

## 📧 Soporte

Para preguntas o problemas, abre un issue en el repositorio.
