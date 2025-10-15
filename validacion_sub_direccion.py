"""
Archivo de validación para el router de Sub-Dirección.
Este archivo prueba el endpoint creado y debe eliminarse una vez validado.

Endpoint a validar:
- GET /sub-direccion/listar/usuario?user_id={id}

Funcionalidades implementadas:
- Listar subdirecciones únicas de un usuario específico
- El usuario debe ser jefe de producto de al menos un programa
- Retorna solo subdirecciones únicas (sin duplicados)
- Formato: { "items": [ { "sub-direccion": "..." } ] }
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"


def test_listar_con_usuario_existente():
    """Test: Listar subdirecciones únicas de un usuario que es jefe de producto"""
    print("\n" + "="*60)
    print("TEST 1: Listar subdirecciones únicas de un usuario existente")
    print("="*60)
    
    # Probar con usuario ID 46 (Jefe grado según los datos de ejemplo)
    user_id = 46
    
    url = f"{BASE_URL}/sub-direccion/listar/usuario?user_id={user_id}"
    response = requests.get(url)
    
    print(f"URL: {url}")
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        items = data.get('items', [])
        print(f"\nTotal de subdirecciones únicas: {len(items)}")
        print(f"\nRespuesta completa:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        # Verificar que no hay duplicados
        subdirecciones = [item.get('sub-direccion') for item in items]
        tiene_duplicados = len(subdirecciones) != len(set(subdirecciones))
        print(f"\n{'❌' if tiene_duplicados else '✅'} Sin duplicados: {not tiene_duplicados}")
    else:
        print(f"Error: {response.text}")
    
    return response.status_code == 200


def test_listar_con_usuario_inexistente():
    """Test: Intentar listar con un usuario que no existe"""
    print("\n" + "="*60)
    print("TEST 2: Listar con usuario inexistente")
    print("="*60)
    
    # Usar un ID de usuario que probablemente no exista
    user_id = 99999
    
    url = f"{BASE_URL}/sub-direccion/listar/usuario?user_id={user_id}"
    response = requests.get(url)
    
    print(f"URL: {url}")
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nRespuesta:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        # Verificar que retorne lista vacía
        items = data.get('items', [])
        print(f"\n✅ Usuario sin programas: items vacío = {len(items) == 0}")
        return True
    else:
        print(f"Error: {response.text}")
        return False


def test_listar_con_multiples_usuarios():
    """Test: Listar subdirecciones de diferentes usuarios"""
    print("\n" + "="*60)
    print("TEST 3: Listar subdirecciones de múltiples usuarios")
    print("="*60)
    
    # IDs de usuarios jefes de producto según los datos de ejemplo
    usuarios_ids = [46, 47, 48]  # Jefe grado, Jefe ee, Jefe CentrumX
    
    resultados = []
    for user_id in usuarios_ids:
        url = f"{BASE_URL}/sub-direccion/listar/usuario?user_id={user_id}"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])
            subdirecciones = [item.get('sub-direccion') for item in items]
            resultados.append({
                "user_id": user_id,
                "total_subdirecciones": len(items),
                "subdirecciones": subdirecciones
            })
    
    print(f"\nResultados obtenidos: {len(resultados)}")
    for resultado in resultados:
        print(f"  - Usuario {resultado['user_id']}: "
              f"{resultado['total_subdirecciones']} subdirección(es) - {resultado['subdirecciones']}")
    
    return len(resultados) > 0


def test_sin_parametro_usuario():
    """Test: Intentar listar sin proporcionar user_id"""
    print("\n" + "="*60)
    print("TEST 4: Intentar listar sin parámetro user_id")
    print("="*60)
    
    url = f"{BASE_URL}/sub-direccion/listar/usuario"
    response = requests.get(url)
    
    print(f"URL: {url}")
    print(f"Status Code: {response.status_code}")
    
    # Debe retornar error 422 (Unprocessable Entity) porque falta el parámetro requerido
    if response.status_code == 422:
        print(f"\n✅ Validación correcta: FastAPI requiere el parámetro obligatorio")
        print(f"Detalle del error:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        return True
    else:
        print(f"\n❌ Debería retornar error 422, pero retornó {response.status_code}")
        return False


def run_all_tests():
    """Ejecutar todos los tests"""
    print("\n" + "🔍" * 30)
    print("VALIDACIÓN DEL ROUTER SUB-DIRECCIÓN")
    print("🔍" * 30)
    
    tests = [
        ("Listar usuario existente", test_listar_con_usuario_existente),
        ("Listar usuario inexistente", test_listar_con_usuario_inexistente),
        ("Listar múltiples usuarios", test_listar_con_multiples_usuarios),
        ("Validar parámetro obligatorio", test_sin_parametro_usuario),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, "✅ PASS" if result else "❌ FAIL"))
        except Exception as e:
            results.append((test_name, f"❌ ERROR: {str(e)}"))
    
    # Resumen
    print("\n" + "="*60)
    print("RESUMEN DE VALIDACIONES")
    print("="*60)
    for test_name, result in results:
        print(f"{test_name}: {result}")
    
    # Contar exitosos
    passed = sum(1 for _, result in results if "✅" in result)
    total = len(results)
    
    print(f"\n✨ Resultado: {passed}/{total} tests pasaron")
    print("\n📝 Nota: Este archivo debe ser eliminado una vez validado.")
    

if __name__ == "__main__":
    print("\n⚠️  IMPORTANTE: Asegúrate de que el servidor esté corriendo en http://127.0.0.1:8000")
    print("Ejecuta: uvicorn fastapi_app.main:app --reload\n")
    
    try:
        # Verificar que el servidor esté disponible
        response = requests.get(f"{BASE_URL}/docs")
        if response.status_code == 200:
            print("✅ Servidor disponible\n")
            run_all_tests()
        else:
            print("❌ El servidor no responde correctamente")
    except requests.exceptions.ConnectionError:
        print("❌ No se pudo conectar al servidor. Asegúrate de que esté corriendo.")
