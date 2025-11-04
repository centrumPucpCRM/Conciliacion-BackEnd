"""
Servicio para interactuar con la API de CRM de Oracle Cloud.
Optimizado para máximo rendimiento con procesamiento paralelo y reutilización de conexiones.
"""
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
import threading


# =========================
# Config base
# =========================
BASE = "https://cang.fa.us2.oraclecloud.com/crmRestApi/resources/11.13.18.05"
HEADERS = {
    "Authorization": "Basic QVBJQ1JNOlZ3ZXVlMTIzNDU=",
    "Content-Type": "application/json",
}
DEFAULT_FIELDS_OPTY = (
    "CTRCodigoDeProgramaCRM_c,CTRPorctDescVentas_c,Revenue,CTRVentaConciliada_c,"
    "CTRPrecioLista_c,CTRMoneda_c,CTRFMatricula_c,CTRInstanteCerradaGamada_c,"
    "CreationDate,OwnerPartyNumber"
)
DEFAULT_FIELDS_CONTACT = (
    "ContactName,PersonDEO_CTRNrodedocumento_c,EmailAddress,OverallPrimaryFormattedPhoneNumber"
)

# Sesión HTTP reutilizable por thread (ThreadLocal)
_thread_local = threading.local()


def get_session() -> requests.Session:
    """Obtiene o crea una sesión HTTP para el thread actual."""
    if not hasattr(_thread_local, 'session'):
        _thread_local.session = requests.Session()
        _thread_local.session.headers.update(HEADERS)
    return _thread_local.session


# =========================
# Utilitario de paginación optimizado
# =========================
def _get_all_items(url: str, params: dict) -> list:
    """Hace llamadas paginadas hasta que hasMore sea False. Optimizado con sesión reutilizable."""
    items = []
    offset = 0
    session = get_session()
    
    while True:
        paged = dict(params) if params else {}
        paged["offset"] = offset
        
        try:
            res = session.get(url, params=paged, timeout=20)
            res.raise_for_status()
            data = res.json()
            page_items = data.get("items", [])
            items.extend(page_items)
            
            has_more = data.get("hasMore", False)
            page_limit = data.get("limit", len(page_items))
            
            if not has_more:
                break
            
            offset += page_limit if page_limit else len(page_items)
            if offset == 0:
                break
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error al obtener datos de CRM: {str(e)}")
    
    return items


# =========================
# Endpoints
# =========================
def obtener_leads_convertidos(codigo_crm: str) -> List[Dict[str, Any]]:
    """Obtiene los leads convertidos para un código CRM específico."""
    url = f"{BASE}/leads"
    params = {
        "q": f"CTRProductoAsociado_Id_c={codigo_crm};StatusCode=CONVERTED",
        "fields": "AccountPartyNumber",
        "onlyData": "true",
    }
    return _get_all_items(url, params)


def leer_oportunidades_por_account(party: int) -> List[Dict[str, Any]]:
    """Lee las oportunidades asociadas a un account party."""
    url = f"{BASE}/opportunities"
    params = {
        "onlyData": "true",
        "q": f"AccountPartyNumber={party}",
        "fields": DEFAULT_FIELDS_OPTY,
    }
    return _get_all_items(url, params)


def leer_cliente(party: int) -> Dict[str, Any]:
    """Lee la información de un cliente por su party number. Optimizado con sesión reutilizable."""
    url = f"{BASE}/contacts/{party}"
    params = {"onlyData": "true", "fields": DEFAULT_FIELDS_CONTACT}
    session = get_session()
    
    try:
        res = session.get(url, params=params, timeout=15)
        res.raise_for_status()
        return res.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error al obtener cliente del CRM: {str(e)}")


def obtener_nombre_vendedora(owner_party: Optional[int]) -> Optional[str]:
    """Obtiene el nombre de la vendedora por su owner party number. Optimizado con sesión reutilizable."""
    if not owner_party:
        return None
    
    url = f"{BASE}/resources/{owner_party}"
    params = {"onlyData": "true", "fields": "PartyName"}
    session = get_session()
    
    try:
        res = session.get(url, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()
        return data.get("PartyName")
    except requests.exceptions.RequestException:
        return None


# =========================
# Worker paralelizado optimizado
# =========================
def procesar_party(codigo_crm: str, party: int) -> List[Dict[str, Any]]:
    """Procesa un party específico para obtener oportunidades relacionadas. Optimizado con paralelismo interno."""
    try:
        # Obtener cliente y oportunidades en paralelo (son independientes)
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_cliente = executor.submit(leer_cliente, party)
            future_optys = executor.submit(leer_oportunidades_por_account, party)
            
            cliente = future_cliente.result()
            optys = future_optys.result()
        
        # Filtrar oportunidades que coincidan con el código CRM
        oportunidades_filtradas = [
            op for op in optys 
            if str(op.get("CTRCodigoDeProgramaCRM_c")) == str(codigo_crm)
        ]
        
        if not oportunidades_filtradas:
            return []
        
        # Obtener owner IDs únicos para procesar vendedoras en batch
        owner_ids = list({op.get("OwnerPartyNumber") for op in oportunidades_filtradas if op.get("OwnerPartyNumber")})
        
        # Obtener nombres de vendedoras en paralelo si hay múltiples
        owner_names_map = {}
        if len(owner_ids) > 1:
            with ThreadPoolExecutor(max_workers=min(len(owner_ids), 10)) as executor:
                futures = {executor.submit(obtener_nombre_vendedora, oid): oid for oid in owner_ids}
                for future in as_completed(futures):
                    owner_id = futures[future]
                    try:
                        owner_names_map[owner_id] = future.result()
                    except:
                        owner_names_map[owner_id] = None
        else:
            # Si solo hay uno, hacerlo directamente
            if owner_ids:
                owner_names_map[owner_ids[0]] = obtener_nombre_vendedora(owner_ids[0])
        
        # Construir resultados
        resultados = []
        for op in oportunidades_filtradas:
            owner_id = op.get("OwnerPartyNumber")
            owner_name = owner_names_map.get(owner_id) if owner_id else None
            
            resultados.append({
                **cliente,
                **op,
                "OwnerPartyName": owner_name,
            })
        
        return resultados
    except Exception as e:
        # Log error pero continúa con otros parties
        print(f"Error procesando party {party}: {str(e)}")
        return []


# =========================
# Orquestador con HILOS optimizado
# =========================
def obtener_oportunidades_desde_leads(codigo_crm: str) -> List[Dict[str, Any]]:
    """
    Obtiene oportunidades desde leads convertidos usando procesamiento paralelo optimizado.
    Maximiza el paralelismo con más workers y reutilización de conexiones HTTP.
    
    Args:
        codigo_crm: Código CRM del programa
        
    Returns:
        Lista de oportunidades con información combinada de cliente y oportunidad
    """
    try:
        leads = obtener_leads_convertidos(codigo_crm)
        
        party_numbers = list({l.get("AccountPartyNumber") for l in leads if l.get("AccountPartyNumber")})
        
        if not party_numbers:
            return []
        
        resultados = []
        # Aumentar significativamente el número de workers para máximo paralelismo
        # Usar mínimo entre número de parties y 50 workers para evitar sobrecarga
        max_workers = min(len(party_numbers), 50)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(procesar_party, codigo_crm, p): p for p in party_numbers}
            
            for future in as_completed(futures):
                try:
                    resultados.extend(future.result())
                except Exception as e:
                    party = futures[future]
                    print(f"Error procesando party {party}: {str(e)}")
                    continue
        
        return resultados
    except Exception as e:
        raise Exception(f"Error al obtener oportunidades desde CRM: {str(e)}")

