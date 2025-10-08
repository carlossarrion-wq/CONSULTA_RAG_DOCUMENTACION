#!/usr/bin/env python3
"""
Script para probar el rendimiento de la función Lambda del incident analyzer
"""
import json
import time
import boto3
from datetime import datetime

# Configuración
FUNCTION_NAME = "incident-analyzer-dev-incident-analyzer"
REGION = "eu-west-1"

# Cliente Lambda
lambda_client = boto3.client('lambda', region_name=REGION)

def invoke_lambda(payload):
    """Invoca la función Lambda y mide el tiempo"""
    start_time = time.time()
    
    response = lambda_client.invoke(
        FunctionName=FUNCTION_NAME,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    # Parsear respuesta
    response_payload = json.loads(response['Payload'].read())
    
    return {
        'execution_time': execution_time,
        'status_code': response['StatusCode'],
        'response': response_payload
    }

def main():
    print("=" * 80)
    print("TEST DE RENDIMIENTO - Incident Analyzer Lambda")
    print("=" * 80)
    print(f"Función: {FUNCTION_NAME}")
    print(f"Región: {REGION}")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    # Payload de prueba
    test_payload = {
        "body": json.dumps({
            "incident_description": "El servidor de aplicaciones está consumiendo mucha CPU, alrededor del 95% constantemente. La aplicación se pone muy lenta y algunos procesos se quedan colgados.",
            "optimize_query": False,  # Deshabilitado por defecto ahora
            "max_similar_incidents": 3  # Reducido de 5 a 3
        })
    }
    
    print("📋 Payload de prueba:")
    print(json.dumps(json.loads(test_payload["body"]), indent=2))
    print()
    
    # Realizar 3 invocaciones para obtener un promedio
    print("🚀 Ejecutando pruebas...")
    print()
    
    results = []
    for i in range(3):
        print(f"Prueba {i+1}/3...")
        try:
            result = invoke_lambda(test_payload)
            results.append(result)
            
            # Extraer información de la respuesta
            if result['status_code'] == 200:
                body = json.loads(result['response'].get('body', '{}'))
                
                print(f"  ✅ Éxito")
                print(f"  ⏱️  Tiempo total: {result['execution_time']:.2f}s")
                
                if 'input_tokens' in body:
                    print(f"  📊 Input tokens: {body['input_tokens']}")
                if 'output_tokens' in body:
                    print(f"  📊 Output tokens: {body['output_tokens']}")
                if 'similar_incidents' in body:
                    print(f"  🔍 Incidencias similares: {len(body['similar_incidents'])}")
                
                # Verificar si hay información de caché
                response_str = json.dumps(result['response'])
                if 'cache' in response_str.lower():
                    print(f"  💾 Caché detectado en respuesta")
            else:
                print(f"  ❌ Error: Status {result['status_code']}")
                print(f"  Respuesta: {result['response']}")
            
            print()
            
            # Esperar un poco entre invocaciones
            if i < 2:
                time.sleep(2)
                
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            print()
    
    # Calcular estadísticas
    if results:
        print("=" * 80)
        print("📊 RESULTADOS")
        print("=" * 80)
        
        execution_times = [r['execution_time'] for r in results if r['status_code'] == 200]
        
        if execution_times:
            avg_time = sum(execution_times) / len(execution_times)
            min_time = min(execution_times)
            max_time = max(execution_times)
            
            print(f"Invocaciones exitosas: {len(execution_times)}/3")
            print(f"Tiempo promedio: {avg_time:.2f}s")
            print(f"Tiempo mínimo: {min_time:.2f}s")
            print(f"Tiempo máximo: {max_time:.2f}s")
            print()
            
            # Comparación con baseline
            baseline_time = 22.27  # Tiempo anterior
            improvement = ((baseline_time - avg_time) / baseline_time) * 100
            
            print("🎯 COMPARACIÓN CON BASELINE")
            print(f"Tiempo anterior (baseline): {baseline_time:.2f}s")
            print(f"Tiempo actual (promedio): {avg_time:.2f}s")
            print(f"Mejora: {improvement:.1f}% más rápido")
            print(f"Ahorro de tiempo: {baseline_time - avg_time:.2f}s")
            print()
            
            # Mostrar detalles de la última respuesta exitosa
            last_success = next((r for r in reversed(results) if r['status_code'] == 200), None)
            if last_success:
                body = json.loads(last_success['response'].get('body', '{}'))
                
                print("📋 DETALLES DE LA ÚLTIMA RESPUESTA")
                if 'diagnosis' in body:
                    print(f"Diagnóstico: {body['diagnosis'][:100]}...")
                if 'root_cause' in body:
                    print(f"Causa raíz: {body['root_cause'][:100]}...")
                if 'recommended_actions' in body:
                    print(f"Acciones recomendadas: {len(body['recommended_actions'])} acciones")
                if 'confidence_score' in body:
                    print(f"Confianza: {body['confidence_score']:.2%}")
        else:
            print("❌ No se obtuvieron resultados exitosos")
    
    print("=" * 80)

if __name__ == "__main__":
    main()
