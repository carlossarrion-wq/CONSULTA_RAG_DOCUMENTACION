#!/usr/bin/env python3
"""
Script para generar datos de ejemplo de incidencias para testing
"""
import json
import os
import sys
from datetime import datetime, timedelta
import random

# Datos de ejemplo de incidencias
SAMPLE_INCIDENTS = [
    {
        "incident_id": "INC-2024-001",
        "title": "Servidor web no responde",
        "description": "El servidor web principal (web-prod-01) no responde a las peticiones HTTP. Los usuarios reportan error 503 Service Unavailable. El servidor está activo pero el servicio nginx no responde.",
        "category": "Infrastructure",
        "severity": "Critical",
        "status": "Resolved",
        "resolution": "Se reinició el servicio nginx después de identificar un problema de memoria. Se aumentó el límite de memoria del proceso de 2GB a 4GB para prevenir futuros problemas.",
        "resolution_time": "45 minutos",
        "root_cause": "Fuga de memoria en nginx causada por un módulo de terceros mal configurado",
        "created_at": "2024-01-15T10:30:00Z",
        "resolved_at": "2024-01-15T11:15:00Z"
    },
    {
        "incident_id": "INC-2024-002",
        "title": "Base de datos lenta",
        "description": "Las consultas a la base de datos PostgreSQL están tardando más de 30 segundos. Los usuarios experimentan timeouts en la aplicación. El CPU del servidor de base de datos está al 95%.",
        "category": "Database",
        "severity": "High",
        "status": "Resolved",
        "resolution": "Se identificaron queries sin índices apropiados. Se crearon índices en las columnas user_id y created_at de la tabla transactions. Se ejecutó VACUUM ANALYZE para optimizar el plan de ejecución.",
        "resolution_time": "2 horas",
        "root_cause": "Falta de índices en tablas con alto volumen de datos",
        "created_at": "2024-01-20T14:00:00Z",
        "resolved_at": "2024-01-20T16:00:00Z"
    },
    {
        "incident_id": "INC-2024-003",
        "title": "Disco lleno en servidor de logs",
        "description": "El servidor de logs (log-server-01) tiene el disco al 98% de capacidad. Los servicios están fallando al intentar escribir logs. Alerta de CloudWatch activada.",
        "category": "Infrastructure",
        "severity": "High",
        "status": "Resolved",
        "resolution": "Se implementó rotación automática de logs con logrotate. Se configuró compresión de logs antiguos y eliminación de logs mayores a 30 días. Se aumentó el tamaño del disco de 100GB a 200GB.",
        "resolution_time": "1 hora",
        "root_cause": "Falta de política de rotación de logs",
        "created_at": "2024-02-01T09:00:00Z",
        "resolved_at": "2024-02-01T10:00:00Z"
    },
    {
        "incident_id": "INC-2024-004",
        "title": "Certificado SSL expirado",
        "description": "El certificado SSL del dominio principal expiró. Los usuarios reciben advertencias de seguridad en el navegador. El tráfico HTTPS está siendo rechazado.",
        "category": "Security",
        "severity": "Critical",
        "status": "Resolved",
        "resolution": "Se renovó el certificado SSL usando Let's Encrypt. Se configuró renovación automática con certbot. Se implementó monitoreo de expiración de certificados con alertas 30 días antes.",
        "resolution_time": "30 minutos",
        "root_cause": "Falta de renovación automática de certificados SSL",
        "created_at": "2024-02-10T08:00:00Z",
        "resolved_at": "2024-02-10T08:30:00Z"
    },
    {
        "incident_id": "INC-2024-005",
        "title": "API Gateway con alta latencia",
        "description": "El API Gateway está respondiendo con latencias superiores a 5 segundos. Los clientes reportan timeouts. El dashboard muestra un incremento del 300% en el tiempo de respuesta.",
        "category": "Application",
        "severity": "High",
        "status": "Resolved",
        "resolution": "Se identificó un endpoint sin caché que estaba haciendo múltiples llamadas a servicios externos. Se implementó caché de Redis con TTL de 5 minutos. Se optimizaron las queries agregando paginación.",
        "resolution_time": "3 horas",
        "root_cause": "Falta de caché en endpoints de alta demanda",
        "created_at": "2024-02-15T11:00:00Z",
        "resolved_at": "2024-02-15T14:00:00Z"
    },
    {
        "incident_id": "INC-2024-006",
        "title": "Fallo en backup automático",
        "description": "El backup automático de la base de datos falló durante 3 días consecutivos. Los logs muestran error de conexión al bucket S3. No hay backups recientes disponibles.",
        "category": "Backup",
        "severity": "High",
        "status": "Resolved",
        "resolution": "Se actualizaron las credenciales IAM del servicio de backup. Se verificó la conectividad con S3. Se ejecutó backup manual exitoso. Se configuró alerta para fallos de backup.",
        "resolution_time": "1 hora",
        "root_cause": "Credenciales IAM expiradas",
        "created_at": "2024-02-20T07:00:00Z",
        "resolved_at": "2024-02-20T08:00:00Z"
    },
    {
        "incident_id": "INC-2024-007",
        "title": "Servicio de email no envía mensajes",
        "description": "El servicio de email (SES) no está enviando correos. Los usuarios no reciben notificaciones. La cola de mensajes tiene 5000 emails pendientes.",
        "category": "Application",
        "severity": "Medium",
        "status": "Resolved",
        "resolution": "Se identificó que la cuenta de SES estaba en sandbox mode con límite de 200 emails/día. Se solicitó salida de sandbox. Se implementó sistema de reintentos con backoff exponencial.",
        "resolution_time": "4 horas",
        "root_cause": "Límites de SES en modo sandbox",
        "created_at": "2024-03-01T10:00:00Z",
        "resolved_at": "2024-03-01T14:00:00Z"
    },
    {
        "incident_id": "INC-2024-008",
        "title": "Memoria insuficiente en Lambda",
        "description": "Las funciones Lambda están fallando con error 'Task timed out after 3.00 seconds'. Los logs muestran 'Memory Size: 128 MB Max Memory Used: 127 MB'.",
        "category": "Serverless",
        "severity": "Medium",
        "status": "Resolved",
        "resolution": "Se aumentó la memoria de las funciones Lambda de 128MB a 512MB. Se optimizó el código para reducir el uso de memoria. Se implementó monitoreo de uso de memoria.",
        "resolution_time": "1 hora",
        "root_cause": "Configuración insuficiente de memoria en Lambda",
        "created_at": "2024-03-05T13:00:00Z",
        "resolved_at": "2024-03-05T14:00:00Z"
    }
]


def generate_metadata_file(incident: dict, output_dir: str):
    """Genera archivo de metadata para una incidencia"""
    filename = f"{incident['incident_id']}_metadata.json"
    filepath = os.path.join(output_dir, filename)
    
    # Agregar metadata adicional
    metadata = {
        **incident,
        "attachments_metadata": [
            {
                "filename": f"{incident['incident_id']}_screenshot.png",
                "type": "image",
                "description": "Captura de pantalla del error"
            },
            {
                "filename": f"{incident['incident_id']}_logs.txt",
                "type": "text",
                "description": "Logs del sistema durante el incidente"
            }
        ]
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    return filename


def generate_sample_attachment(incident_id: str, output_dir: str, attachment_type: str):
    """Genera archivos de ejemplo de adjuntos"""
    if attachment_type == "logs":
        filename = f"{incident_id}_logs.txt"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w') as f:
            f.write(f"=== Logs del incidente {incident_id} ===\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write("\n")
            f.write("[ERROR] Service unavailable\n")
            f.write("[WARN] High memory usage detected\n")
            f.write("[INFO] Attempting restart\n")
            f.write("[INFO] Service restarted successfully\n")
        
        return filename
    
    elif attachment_type == "screenshot":
        # Para screenshots, solo creamos un placeholder
        filename = f"{incident_id}_screenshot.png"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w') as f:
            f.write(f"# Placeholder for screenshot {incident_id}\n")
        
        return filename


def main():
    """Función principal"""
    # Crear directorios
    metadata_dir = "sample-data/incidents-metadata"
    files_dir = "sample-data/incidents-files"
    
    os.makedirs(metadata_dir, exist_ok=True)
    os.makedirs(files_dir, exist_ok=True)
    
    print("Generando datos de ejemplo de incidencias...")
    print(f"Directorio metadata: {metadata_dir}")
    print(f"Directorio archivos: {files_dir}")
    print()
    
    generated_files = []
    
    for incident in SAMPLE_INCIDENTS:
        # Generar metadata
        metadata_file = generate_metadata_file(incident, metadata_dir)
        generated_files.append(f"metadata: {metadata_file}")
        
        # Generar archivos adjuntos
        logs_file = generate_sample_attachment(
            incident['incident_id'], 
            files_dir, 
            "logs"
        )
        generated_files.append(f"  - {logs_file}")
        
        screenshot_file = generate_sample_attachment(
            incident['incident_id'], 
            files_dir, 
            "screenshot"
        )
        generated_files.append(f"  - {screenshot_file}")
        
        print(f"✓ Generado: {incident['incident_id']} - {incident['title']}")
    
    print()
    print(f"✓ Generados {len(SAMPLE_INCIDENTS)} incidencias de ejemplo")
    print()
    print("Para subir a S3:")
    print(f"  aws s3 cp {metadata_dir}/ s3://YOUR-BUCKET/incidents-metadata/ --recursive")
    print(f"  aws s3 cp {files_dir}/ s3://YOUR-BUCKET/incidents-files/ --recursive")
    print()
    print("Luego sincroniza la Knowledge Base:")
    print("  bash scripts/sync-knowledge-base.sh YOUR-STACK-NAME")


if __name__ == "__main__":
    main()
