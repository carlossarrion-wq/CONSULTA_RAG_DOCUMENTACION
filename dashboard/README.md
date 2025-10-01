# Dashboard de Análisis de Incidencias

Dashboard web interactivo para probar el sistema de análisis de incidencias con RAG (Retrieval-Augmented Generation) usando AWS Bedrock.

## 🎨 Características

- **Interfaz moderna** con colores teal/green inspirados en AWS
- **Estadísticas en tiempo real**: consultas realizadas, confianza promedio, tiempo de respuesta
- **Ejemplos predefinidos** para pruebas rápidas
- **Visualización completa** de resultados:
  - Diagnóstico detallado
  - Causa raíz identificada
  - Acciones recomendadas (3-7 acciones)
  - **Indicador circular de confianza** con código de colores:
    - 🟢 Verde (≥70%): Alta confianza
    - 🟠 Ámbar (40-69%): Confianza media
    - 🔴 Rojo (<40%): Baja confianza
  - Incidencias similares encontradas con badges de similitud codificados por color
- **Indicador de estado** del servicio
- **Diseño responsive** adaptable a diferentes tamaños de pantalla
- **Tipografía optimizada** para mejor legibilidad en todos los elementos

## 🚀 Uso

### Opción 1: Abrir directamente en el navegador

```bash
# Desde el directorio del proyecto
open dashboard/index.html
```

O simplemente haz doble clic en el archivo `index.html` desde tu explorador de archivos.

### Opción 2: Servir con un servidor HTTP local

```bash
# Con Python 3
cd dashboard
python3 -m http.server 8000

# Luego abre en el navegador:
# http://localhost:8000
```

```bash
# Con Node.js (si tienes http-server instalado)
cd dashboard
npx http-server -p 8000
```

## 📝 Cómo realizar una consulta

1. **Ingresa la descripción de la incidencia** en el área de texto
   - Puedes escribir tu propia descripción
   - O hacer clic en uno de los ejemplos predefinidos

2. **Haz clic en "Analizar Incidencia"**
   - El sistema mostrará un spinner mientras procesa
   - Verás el mensaje "Analizando incidencia..."

3. **Revisa los resultados**:
   - **Diagnóstico**: Análisis del problema
   - **Causa Raíz**: Identificación de la causa principal
   - **Acciones Recomendadas**: Lista de pasos a seguir
   - **Nivel de Confianza**: Indicador circular animado con código de colores en la esquina superior derecha
   - **Incidencias Similares**: Casos históricos relacionados con badges de similitud codificados por color

## 🔧 Configuración

El dashboard está preconfigurado con:

```javascript
const API_CONFIG = {
    endpoint: 'https://k1n3got8n7.execute-api.eu-west-1.amazonaws.com/dev/analyze',
    apiKey: 'ZVITNxyrLA24lBvrwQk6da2McY75iZKg7r6Tqv8y'
};
```

Si necesitas cambiar la configuración:

1. Abre `index.html` en un editor de texto
2. Busca la sección `API_CONFIG` en el JavaScript
3. Modifica el `endpoint` y/o `apiKey` según sea necesario
4. Guarda los cambios

## 📊 Estadísticas

El dashboard rastrea automáticamente:

- **Consultas Realizadas**: Contador total de análisis
- **Última Confianza**: Score de confianza del último análisis (0-100%)
- **Tiempo Promedio**: Tiempo promedio de respuesta del API en segundos
- **Estado del Servicio**: Indicador visual (🟢/🔴)

## 🎨 Mejoras de UI Recientes

### Indicador Circular de Confianza
- Gráfico circular SVG animado que muestra el nivel de confianza
- Código de colores dinámico:
  - Verde: ≥70% (alta confianza)
  - Ámbar: 40-69% (confianza media)
  - Rojo: <40% (baja confianza)
- Posicionado en la esquina superior derecha de los resultados
- Animación suave al actualizar valores

### Badges de Similitud
- Badges codificados por color para incidencias similares
- Mismo esquema de colores que el indicador de confianza
- Gradientes visuales para mejor apariencia

### Tipografía Mejorada
- Tamaños de fuente optimizados para mejor legibilidad:
  - Títulos de tarjetas: 1.35rem
  - Etiquetas de formulario: 1rem
  - Áreas de texto: 1.1rem
  - Botones: 1.1rem
  - Contenido de resultados: 1.1rem
  - Descripciones de incidencias: 1rem

## 💡 Ejemplos de Consultas

El dashboard incluye 3 ejemplos predefinidos:

1. **Error de conexión a base de datos**
   - Simula problemas de conectividad con PostgreSQL
   - Útil para probar diagnósticos de infraestructura

2. **Alto consumo de CPU**
   - Simula problemas de rendimiento
   - Útil para probar análisis de recursos

3. **Fallos intermitentes de autenticación**
   - Simula problemas de servicios
   - Útil para probar análisis de servicios distribuidos

## 🎯 Casos de Uso

### Para Desarrolladores
- Probar el API sin necesidad de curl o Postman
- Validar respuestas del modelo Claude
- Verificar el funcionamiento del sistema RAG

### Para QA/Testing
- Realizar pruebas funcionales del sistema
- Validar diferentes escenarios de incidencias
- Verificar tiempos de respuesta

### Para Demos
- Mostrar capacidades del sistema a stakeholders
- Demostrar análisis en tiempo real
- Visualizar resultados de forma profesional

## 🔍 Troubleshooting

### El dashboard muestra 🔴 en "Estado del Servicio"
- Verifica que el API Gateway esté desplegado
- Confirma que la API Key sea correcta
- Revisa que el endpoint sea accesible

### Error al analizar incidencia
- Verifica la consola del navegador (F12) para más detalles
- Confirma que el Lambda tenga permisos correctos
- Revisa los logs de CloudWatch

### No se muestran incidencias similares
- Verifica que el Knowledge Base tenga datos indexados
- Confirma que la sincronización se haya completado
- Revisa que los embeddings estén generados

## 🛠️ Tecnologías Utilizadas

- **HTML5**: Estructura semántica
- **CSS3**: Estilos modernos con gradientes, animaciones y SVG
- **JavaScript (ES6+)**: Lógica de interacción y llamadas al API
- **SVG**: Gráficos vectoriales para el indicador circular de confianza
- **Fetch API**: Comunicación con el backend
- **AWS API Gateway**: Endpoint REST
- **AWS Bedrock**: Modelo de IA para análisis

## 📱 Compatibilidad

- ✅ Chrome/Edge (últimas versiones)
- ✅ Firefox (últimas versiones)
- ✅ Safari (últimas versiones)
- ✅ Responsive (móvil, tablet, desktop)

## 🔐 Seguridad

⚠️ **IMPORTANTE**: Este dashboard incluye la API Key en el código JavaScript por simplicidad. Para producción:

1. Implementa un backend proxy que maneje la API Key
2. Usa variables de entorno
3. Implementa autenticación de usuarios
4. Considera usar AWS Cognito para autenticación

## 📄 Licencia

Este dashboard es parte del sistema de análisis de incidencias y sigue la misma licencia del proyecto principal.
