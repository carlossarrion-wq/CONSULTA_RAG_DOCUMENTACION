# Sistema de Análisis de Incidencias con RAG

Sistema inteligente de análisis de incidencias técnicas que utiliza RAG (Retrieval-Augmented Generation) con AWS Bedrock, Claude Sonnet 4.5, Aurora PostgreSQL con pgvector, y S3 para proporcionar diagnósticos automáticos, identificación de causa raíz y recomendaciones basadas en histórico de incidencias similares.

## 🚀 Características Principales

### Análisis Inteligente de Incidencias
- ✅ **Búsqueda semántica** de incidencias similares en base de conocimiento
- ✅ **Diagnóstico automático** basado en patrones históricos
- ✅ **Identificación de causa raíz** con análisis contextual
- ✅ **Recomendaciones de resolución** paso a paso
- ✅ **Score de confianza** del análisis realizado

### Arquitectura RAG Completa
- ✅ **Knowledge Base** en AWS Bedrock con búsqueda vectorial
- ✅ **Aurora PostgreSQL 15.4** con extensión pgvector (1024 dimensiones)
- ✅ **Embeddings** con Amazon Titan v2
- ✅ **Búsqueda híbrida**: Semántica (vectorial) + Keywords
- ✅ **Claude Sonnet 4.5**: Modelo de última generación

### Gestión de Documentos
- ✅ **Multi-formato**: PDF, imágenes, Excel, Word, texto, logs
- ✅ **Archivos adjuntos**: Almacenamiento en S3 con recuperación automática
- ✅ **Metadata enriquecida**: Sincronización con Knowledge Base
- ✅ **Procesamiento inteligente**: Conversión automática de formatos

### API y Dashboard
- ✅ **API REST** con autenticación y rate limiting
- ✅ **Dashboard web interactivo** con visualizaciones en tiempo real
- ✅ **Gráficos de historial**: Tiempos de respuesta y niveles de confianza
- ✅ **Indicadores visuales**: Círculo de confianza con código de colores

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

### Dashboard Web Interactivo

La forma más sencilla de usar el sistema es a través del dashboard web:

```bash
# Abrir el dashboard en el navegador
open dashboard/index.html
```

El dashboard incluye:
- 📊 **Métricas en tiempo real**: Consultas realizadas, confianza promedio, tiempos
- 📝 **Formulario de consulta**: Describe la incidencia y obtén análisis instantáneo
- 📈 **Gráficos de historial**: Visualiza tiempos de respuesta y niveles de confianza
- 🎨 **Indicadores visuales**: Círculo de confianza con código de colores
- 🔍 **Incidencias similares**: Ve casos históricos relacionados con badges de similitud

### API REST - Análisis de Incidencias

#### Endpoint Principal: `/analyze-incident`

```bash
# Analizar una incidencia
curl -X POST https://your-api-url/dev/analyze-incident \
  -H 'Content-Type: application/json' \
  -H 'x-api-key: YOUR_API_KEY' \
  -d '{
    "incident_description": "El servidor web no responde en el puerto 443. Los usuarios reportan error de conexión SSL."
  }'
```

**Respuesta**:
```json
{
  "diagnosis": "Basado en el análisis de incidencias similares, el problema parece estar relacionado con un certificado SSL expirado...",
  "root_cause": "Certificado SSL expirado en el servidor web principal",
  "recommended_actions": [
    "Verificar estado del certificado: openssl x509 -in cert.pem -noout -dates",
    "Renovar certificado: certbot renew",
    "Reiniciar servidor web: systemctl restart nginx"
  ],
  "confidence_score": 0.92,
  "similar_incidents": [
    {
      "incident_id": "INC-2024-001",
      "title": "Certificado SSL expirado",
      "similarity_score": 0.95,
      "description": "Servidor web principal no responde..."
    }
  ]
}
```

#### Health Check

```bash
curl https://your-api-url/dev/health
```

### CLI Local (Para desarrollo y pruebas)

#### Probar conexión con Bedrock

```bash
python -m src.cli.main test
```

#### Consulta con documentos

```bash
python -m src.cli.main query \
  -p "Analiza este log de errores" \
  -f error_log.txt \
  -f screenshot.png
```

### Despliegue Completo

Para desplegar toda la infraestructura (Aurora, Lambda, API Gateway, Knowledge Base):

```bash
cd scripts
./deploy-complete.sh
```

Este script automatiza:
1. ✅ Despliegue de infraestructura con CloudFormation/SAM
2. ✅ Inicialización de Aurora PostgreSQL con pgvector
3. ✅ Creación de Knowledge Base en Bedrock
4. ✅ Sincronización de datos de ejemplo
5. ✅ Configuración de API Gateway con CORS

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
