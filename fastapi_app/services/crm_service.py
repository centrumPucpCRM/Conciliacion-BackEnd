"""
Servicio para interactuar con la API de CRM de Oracle Cloud.
Optimizado para máximo rendimiento con procesamiento paralelo y reutilización de conexiones.
"""
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
import threading
from datetime import datetime, date
from sqlalchemy.orm import Session
from ..models.oportunidad import Oportunidad
from ..models.programa import Programa
from ..models.tipo_cambio import TipoCambio


# =========================
# Config base
# =========================
BASE = "https://cang.fa.us2.oraclecloud.com/crmRestApi/resources/11.13.18.05"
HEADERS = {
    "Authorization": "Basic QVBJQ1JNOlZ3ZXVlMTIzNDU=",
    "Content-Type": "application/json",
}
DEFAULT_FIELDS_OPTY = (
    "OptyNumber,CTRCodigoDeProgramaCRM_c,CTRPorctDescVentas_c,Revenue,CTRVentaConciliada_c,"
    "CTRPrecioLista_c,CTRMoneda_c,CTRFMatricula_c,CTRInstanteCerradaGamada_c,"
    "CreationDate,OwnerPartyNumber,CTRFechaDeUltimaConciliacion_c,CTRRegistroDeVentaConciliada_c"
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


_ETAPAS_NO_CP = {"1 - Interés", "2 - Calificación"}

def obtener_fijos_fuera_counter(codigo_crm: str) -> Dict[str, Any]:
    """
    Obtiene el conteo y monto total de 'Fijo fuera de counter' para un programa:
      1. Leads HOT + QUALIFIED (fijos fuera de counter directos)
      2. Leads CONVERTED cuya etapa (CTRFannelDataEstudioEtapaOpty_c) sea
         "1 - Interés" o "2 - Calificación" (no CP)
    Retorna: {"count": int, "monto": float}
    """
    url = f"{BASE}/leads"

    # --- Grupo 1: HOT + QUALIFIED ---
    items_ffc = _get_all_items(url, {
        "onlyData": "true",
        "q": f"CTRProductoAsociado_Id_c={codigo_crm};Rank=HOT;StatusCode=QUALIFIED",
        "fields": "LeadNumber,DealAmount",
    })

    # --- Grupo 2: CONVERTED con etapa no-CP ---
    items_converted = _get_all_items(url, {
        "onlyData": "true",
        "q": f"CTRProductoAsociado_Id_c={codigo_crm};StatusCode=CONVERTED",
        "fields": "LeadNumber,DealAmount,CTRFannelDataEstudioEtapaOpty_c",
    })
    items_no_cp = [
        i for i in items_converted
        if i.get("CTRFannelDataEstudioEtapaOpty_c") in _ETAPAS_NO_CP
    ]

    todos = items_ffc + items_no_cp
    total_monto = sum(i.get("DealAmount", 0) or 0 for i in todos)
    return {"count": len(todos), "monto": float(total_monto)}


def obtener_detalle_fijos_fuera_counter(codigo_crm: str) -> List[Dict[str, Any]]:
    """
    Retorna la lista completa de leads 'Fijo fuera de counter' para un programa:
      1. Leads HOT + QUALIFIED
      2. Leads CONVERTED con etapa no-CP ("1 - Interés" o "2 - Calificación")
    """
    url = f"{BASE}/leads"
    FIELDS = (
        "LeadNumber,CustomerPartyName,DealAmount,CurrencyCode,"
        "StatusCode,CTRFannelDataEstudioEtapaOpty_c,CTRDsctoVentas_c,OwnerPartyName,"
        "CTRNumDocumento_c"
    )

    items_ffc = _get_all_items(url, {
        "onlyData": "true",
        "q": f"CTRProductoAsociado_Id_c={codigo_crm};Rank=HOT;StatusCode=QUALIFIED",
        "fields": FIELDS,
    })

    items_converted = _get_all_items(url, {
        "onlyData": "true",
        "q": f"CTRProductoAsociado_Id_c={codigo_crm};StatusCode=CONVERTED",
        "fields": FIELDS,
    })
    items_no_cp = [
        i for i in items_converted
        if i.get("CTRFannelDataEstudioEtapaOpty_c") in _ETAPAS_NO_CP
    ]

    todos = items_ffc + items_no_cp
    return [
        {
            "leadNumber": i.get("LeadNumber"),
            "nombre": i.get("CustomerPartyName"),
            "dni": i.get("CTRNumDocumento_c"),
            "monto": float(i.get("DealAmount") or 0),
            "moneda": i.get("CurrencyCode"),
            "estado": i.get("StatusCode"),
            "etapa": i.get("CTRFannelDataEstudioEtapaOpty_c"),
            "descuento": i.get("CTRDsctoVentas_c"),
            "vendedor": i.get("OwnerPartyName"),
        }
        for i in todos
    ]


_ETAPAS_CERRADAS = {"3 - Matrícula", "4 - Cerrada/Ganada"}

def obtener_alumnos_ultimo_momento(codigo_crm: str) -> List[Dict[str, Any]]:
    """
    Retorna leads CONVERTED en etapas '3 - Matrícula' o '4 - Cerrada/Ganada'.
    Estos pasaron a esas etapas después del snapshot de conciliación.
    La exclusión de los ya conciliados se hace en el router comparando partyNumber.
    """
    url = f"{BASE}/leads"
    FIELDS = (
        "LeadNumber,CustomerPartyName,DealAmount,CurrencyCode,"
        "StatusCode,CTRFannelDataEstudioEtapaOpty_c,CTRDsctoVentas_c,OwnerPartyName,"
        "AccountPartyNumber,CTRNumDocumento_c"
    )
    items_converted = _get_all_items(url, {
        "onlyData": "true",
        "q": f"CTRProductoAsociado_Id_c={codigo_crm};StatusCode=CONVERTED",
        "fields": FIELDS,
    })
    return [
        {
            "leadNumber": i.get("LeadNumber"),
            "nombre": i.get("CustomerPartyName"),
            "dni": i.get("CTRNumDocumento_c"),
            "monto": float(i.get("DealAmount") or 0),
            "moneda": i.get("CurrencyCode"),
            "etapa": i.get("CTRFannelDataEstudioEtapaOpty_c"),
            "descuento": i.get("CTRDsctoVentas_c"),
            "vendedor": i.get("OwnerPartyName"),
            "partyNumber": str(i.get("AccountPartyNumber") or ""),
        }
        for i in items_converted
        if i.get("CTRFannelDataEstudioEtapaOpty_c") in _ETAPAS_CERRADAS
    ]


def obtener_etapas_actuales_leads(codigo_crm: str) -> Dict[str, str]:
    """
    Retorna dos dicts para detectar retrocesos durante sync:
      - by_party: {str(AccountPartyNumber): etapa_crm}
      - by_dni:   {str(CTRNumDocumento_c): etapa_crm}
    Consulta TODOS los leads del programa (cualquier status) para capturar
    también leads QUALIFIED que hayan retrocedido desde CONVERTED.
    """
    url = f"{BASE}/leads"
    items = _get_all_items(url, {
        "onlyData": "true",
        "q": f"CTRProductoAsociado_Id_c={codigo_crm}",
        "fields": "AccountPartyNumber,CTRFannelDataEstudioEtapaOpty_c,CTRNumDocumento_c",
    })
    by_party: Dict[str, str] = {}
    by_dni: Dict[str, str] = {}
    for i in items:
        etapa = (i.get("CTRFannelDataEstudioEtapaOpty_c") or "").strip()
        party = str(i.get("AccountPartyNumber") or "").strip()
        dni = str(i.get("CTRNumDocumento_c") or "").strip()
        if party:
            by_party[party] = etapa
        if dni:
            by_dni[dni] = etapa
    return by_party, by_dni


# Alias para compatibilidad con imports existentes
def obtener_etapas_actuales_convertidos(codigo_crm: str):
    return obtener_etapas_actuales_leads(codigo_crm)


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
                "PartyNumber":party,
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


# =========================
# Transformación y sincronización con BD
# =========================
def _transformar_oportunidad_crm(data_crm: Dict[str, Any], id_programa: int, id_propuesta: int, id_tipo_cambio: int) -> Dict[str, Any]:
    """Transforma los datos del CRM al formato requerido por el modelo Oportunidad."""
    
    # Calcular descuento
    descuento = data_crm.get("CTRPorctDescVentas_c", 0.0)
    if descuento is None:
        descuento = 0.0
    
    # Calcular monto
    monto = data_crm.get("Revenue", 0.0)
    if monto is None:
        monto = 0.0
    
    # Calcular becado (descuento > 99% o monto < 10)
    becado = descuento > 0.99 or monto < 10
    
    # Calcular fecha de matrícula (la mayor de las tres fechas)
    fechas = []
    
    # CTRFMatricula_c
    if data_crm.get("CTRFMatricula_c"):
        try:
            fecha_matricula = datetime.strptime(data_crm["CTRFMatricula_c"], "%Y-%m-%d").date()
            fechas.append(fecha_matricula)
        except:
            pass
    
    # CTRInstanteCerradaGamada_c
    if data_crm.get("CTRInstanteCerradaGamada_c"):
        try:
            fecha_cerrada = datetime.fromisoformat(data_crm["CTRInstanteCerradaGamada_c"].replace('Z', '+00:00')).date()
            fechas.append(fecha_cerrada)
        except:
            pass
    
    # CreationDate
    if data_crm.get("CreationDate"):
        try:
            fecha_creacion = datetime.fromisoformat(data_crm["CreationDate"].replace('Z', '+00:00')).date()
            fechas.append(fecha_creacion)
        except:
            pass
    
    fecha_matricula = max(fechas) if fechas else None
    
    # Calcular posible atípico (Revenue/CTRPrecioLista_c)
    posible_atipico = True  # Por ahora siempre True como solicitado
    precio_lista = data_crm.get("CTRPrecioLista_c")
    if precio_lista and precio_lista > 0 and monto:
        ratio = monto / precio_lista
        # Se puede ajustar esta lógica después
        posible_atipico = isinstance(ratio, float)
    
    return {
        "nombre": data_crm.get("ContactName", ""),
        "documentoIdentidad": data_crm.get("PersonDEO_CTRNrodedocumento_c", ""),
        "correo": data_crm.get("EmailAddress", ""),
        "telefono": data_crm.get("OverallPrimaryFormattedPhoneNumber", ""),
        "etapaDeVentas": "Agregado CRM",
        "descuento": descuento,
        "monto": monto,
        "becado": becado,
        "partyNumber": data_crm.get("PartyNumber"),
        "optyNumber": str(data_crm.get("OptyNumber", "")) or None,
        "conciliado": data_crm.get("CTRVentaConciliada_c", False),
        "posibleAtipico": posible_atipico,
        "moneda": data_crm.get("CTRMoneda_c", ""),
        "fechaMatricula": fecha_matricula,
        "idPropuesta": id_propuesta,
        "idPrograma": id_programa,
        "idTipoCambio": id_tipo_cambio,
        "montoPropuesto": monto,  # Mismo monto por ahora
        "descuentoPropuesto": descuento,  # Mismo descuento por ahora
        "etapaVentaPropuesta": "Agregado CRM",
        "fechaMatriculaPropuesta": fecha_matricula,
        "eliminado": False,
        "vendedora": data_crm.get("OwnerPartyName", "")
    }


def _obtener_tipo_cambio_por_moneda_fecha(db: Session, moneda: str, fecha: date) -> Optional[int]:
    """Obtiene el ID del tipo de cambio más reciente para una moneda y fecha."""
    tipo_cambio = db.query(TipoCambio).filter(
        TipoCambio.moneda_origen == moneda,
        TipoCambio.fecha_tipo_cambio <= fecha
    ).order_by(TipoCambio.fecha_tipo_cambio.desc()).first()
    
    return tipo_cambio.id if tipo_cambio else None


def sincronizar_oportunidades_crm(db: Session, programa_id: int) -> Dict[str, Any]:
    """
    Sincroniza las oportunidades del CRM con la base de datos.

    Args:
        db: Sesión de base de datos
        programa_id: ID del programa (PK en la tabla `programa`)

    Returns:
        Diccionario con estadísticas de la sincronización
    """
    try:
        # Obtener el programa por ID (no por código, porque el código se repite
        # entre filas de programa de distintas propuestas).
        programa = db.query(Programa).filter(Programa.id == programa_id).first()
        if not programa:
            raise Exception(f"No se encontró programa con id: {programa_id}")
        if not programa.codigo:
            raise Exception(f"El programa {programa_id} no tiene código CRM asociado")

        codigo_crm = str(programa.codigo)

        # Obtener oportunidades del CRM
        oportunidades_crm = obtener_oportunidades_desde_leads(codigo_crm)
        
        if not oportunidades_crm:
            return {
                "total_crm": 0,
                "nuevas_insertadas": 0,
                "ya_existentes": 0,
                "errores": 0
            }
        
        # Obtener party numbers existentes en BD para este programa y convertir a strings
        party_numbers_existentes_query = (
            db.query(Oportunidad.partyNumber)
            .filter(Oportunidad.idPrograma == programa.id)
            .filter(Oportunidad.partyNumber.isnot(None))
            .all()
        )
        party_numbers_existentes = {str(pn[0]) for pn in party_numbers_existentes_query}
        
        # Obtener party numbers del CRM como strings
        party_numbers_crm = {str(op.get("PartyNumber")) for op in oportunidades_crm if op.get("PartyNumber")}
        
        # Debug: imprimir información de comparación
        print(f"DEBUG - Programa ID: {programa.id}")
        print(f"DEBUG - Party numbers en BD (str): {party_numbers_existentes}")
        print(f"DEBUG - Party numbers en CRM (str): {party_numbers_crm}")
        print(f"DEBUG - Intersección: {party_numbers_existentes.intersection(party_numbers_crm)}")
        
        # Filtrar oportunidades nuevas comparando strings
        oportunidades_nuevas = [
            op for op in oportunidades_crm 
            if str(op.get("PartyNumber")) not in party_numbers_existentes
        ]
        
        print(f"DEBUG - Total CRM: {len(oportunidades_crm)}, Nuevas: {len(oportunidades_nuevas)}, Ya existentes: {len(oportunidades_crm) - len(oportunidades_nuevas)}")
        
        estadisticas = {
            "total_crm": len(oportunidades_crm),
            "nuevas_insertadas": 0,
            "ya_existentes": len(oportunidades_crm) - len(oportunidades_nuevas),
            "errores": 0
        }
        
        # Insertar oportunidades nuevas
        for op_crm in oportunidades_nuevas:
            try:
                # Obtener tipo de cambio
                moneda = op_crm.get("CTRMoneda_c", "USD")
                fecha_consulta = date.today()
                id_tipo_cambio = _obtener_tipo_cambio_por_moneda_fecha(db, moneda, fecha_consulta)
                
                # Transformar datos
                datos_oportunidad = _transformar_oportunidad_crm(
                    op_crm, 
                    programa.id, 
                    programa.idPropuesta,
                    id_tipo_cambio
                )
                
                # Crear nueva oportunidad
                nueva_oportunidad = Oportunidad(**datos_oportunidad)
                db.add(nueva_oportunidad)
                
                estadisticas["nuevas_insertadas"] += 1
                
            except Exception as e:
                print(f"Error insertando oportunidad con PartyNumber {op_crm.get('PartyNumber')}: {str(e)}")
                estadisticas["errores"] += 1
                continue
        
        # Confirmar cambios
        db.commit()
        
        return estadisticas
        
    except Exception as e:
        db.rollback()
        raise Exception(f"Error en sincronización CRM: {str(e)}")


def actualizar_conciliado_crm(opty_number: str, conciliado: bool) -> Dict[str, Any]:
    """
    Actualiza el campo CTRVentaConciliada_c de una oportunidad en el CRM.

    Args:
        opty_number: OptyNumber de la oportunidad en el CRM
        conciliado: True → "Y", False → "N"
    """
    url = f"{BASE}/opportunities/{opty_number}"
    session = get_session()
    params = {"onlyData": "true", "fields": "CTRVentaConciliada_c"}
    payload = {"CTRVentaConciliada_c": "Y" if conciliado else "N"}

    try:
        res = session.patch(url, json=payload, params=params, timeout=15)
        res.raise_for_status()
        return res.json()
    except requests.exceptions.RequestException as e:
        print(f"Error actualizando oportunidad {opty_number} en CRM: {str(e)}")
        raise


def actualizar_conciliado_crm_batch(opty_numbers: List[str], conciliado: bool) -> Dict[str, Any]:
    """
    Actualiza CTRVentaConciliada_c para múltiples oportunidades en paralelo.

    Returns:
        Dict con estadísticas: exitosos, errores
    """
    if not opty_numbers:
        return {"exitosos": 0, "errores": 0}

    estadisticas = {"exitosos": 0, "errores": 0}
    max_workers = min(len(opty_numbers), 20)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(actualizar_conciliado_crm, opty, conciliado): opty
            for opty in opty_numbers
        }
        for future in as_completed(futures):
            opty = futures[future]
            try:
                future.result()
                estadisticas["exitosos"] += 1
            except Exception as e:
                print(f"Error actualizando opty {opty}: {str(e)}")
                estadisticas["errores"] += 1

    return estadisticas


def marcar_conciliada_crm(opty_number: str, fecha_conciliacion: str, ya_tiene_registro: bool) -> Dict[str, Any]:
    """
    Marca una oportunidad como conciliada en CRM actualizando los 3 campos:
    - CTRVentaConciliada_c = "Y" (transaccional)
    - CTRFechaDeUltimaConciliacion_c = fecha actual (siempre se actualiza)
    - CTRRegistroDeVentaConciliada_c = "Y" (solo si aún no tenía valor — inmutable)
    """
    url = f"{BASE}/opportunities/{opty_number}"
    session = get_session()
    params = {"onlyData": "true"}
    payload: Dict[str, Any] = {
        "CTRVentaConciliada_c": "Y",
        "CTRFechaDeUltimaConciliacion_c": fecha_conciliacion,
    }
    if not ya_tiene_registro:
        payload["CTRRegistroDeVentaConciliada_c"] = "Y"

    try:
        res = session.patch(url, json=payload, params=params, timeout=15)
        res.raise_for_status()
        return res.json()
    except requests.exceptions.RequestException as e:
        print(f"Error marcando conciliada opty {opty_number} en CRM: {str(e)}")
        raise


def marcar_conciliada_crm_batch(opty_data: List[Dict]) -> Dict[str, Any]:
    """
    Marca múltiples oportunidades como conciliadas en CRM en paralelo.
    opty_data: lista de dicts con keys: opty_number, fecha_conciliacion, ya_tiene_registro
    """
    if not opty_data:
        return {"exitosos": 0, "errores": 0}

    estadisticas = {"exitosos": 0, "errores": 0}
    max_workers = min(len(opty_data), 20)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                marcar_conciliada_crm,
                item["opty_number"],
                item["fecha_conciliacion"],
                item["ya_tiene_registro"],
            ): item["opty_number"]
            for item in opty_data
        }
        for future in as_completed(futures):
            opty = futures[future]
            try:
                future.result()
                estadisticas["exitosos"] += 1
            except Exception as e:
                print(f"Error marcando conciliada opty {opty}: {str(e)}")
                estadisticas["errores"] += 1

    return estadisticas

