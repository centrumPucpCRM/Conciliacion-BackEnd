"""
Utilidades para el cálculo y gestión de estados de vacaciones
"""
from datetime import datetime, date
from typing import Dict, List, Optional, Literal


ESTADOS_PERMITIDOS = ["planificado", "activo", "finalizado", "cancelado"]


def calcular_estado_vacaciones(
    inicio: str,
    fin: str,
    estado_explicito: Optional[str] = None,
    es_cancelado: bool = False
) -> Literal["planificado", "activo", "finalizado", "cancelado"]:
    """
    Calcula el estado de un periodo o vacación extra según las fechas y reglas de negocio.
    
    Reglas:
    - cancelado: Si se indica explícitamente como cancelado
    - planificado: Si la fecha de inicio aún no ha llegado
    - activo: Si la fecha actual está dentro del rango (inicio ≤ hoy ≤ fin)
    - finalizado: Si la fecha de fin ya pasó
    
    Args:
        inicio: Fecha de inicio en formato YYYY-MM-DD
        fin: Fecha de fin en formato YYYY-MM-DD
        estado_explicito: Estado proporcionado explícitamente (tiene prioridad)
        es_cancelado: Indica si las vacaciones fueron canceladas
    
    Returns:
        Estado calculado: "planificado", "activo", "finalizado" o "cancelado"
    """
    # Si está cancelado explícitamente, retornar cancelado
    if es_cancelado or estado_explicito == "cancelado":
        return "cancelado"
    
    # Si se proporciona un estado explícito válido, usarlo
    if estado_explicito and estado_explicito in ESTADOS_PERMITIDOS:
        return estado_explicito
    
    # Parsear fechas
    try:
        fecha_inicio = datetime.strptime(inicio, '%Y-%m-%d').date()
        fecha_fin = datetime.strptime(fin, '%Y-%m-%d').date()
        fecha_actual = date.today()
    except ValueError as e:
        raise ValueError(f"Error al parsear fechas: {e}")
    
    # Validar que inicio <= fin
    if fecha_inicio > fecha_fin:
        raise ValueError("La fecha de inicio no puede ser posterior a la fecha de fin")
    
    # Calcular estado según fechas
    if fecha_actual < fecha_inicio:
        return "planificado"
    elif fecha_inicio <= fecha_actual <= fecha_fin:
        return "activo"
    else:  # fecha_actual > fecha_fin
        return "finalizado"


def procesar_periodos_con_estado(
    periodos: Optional[List[Dict]],
    recalcular_estados: bool = True
) -> List[Dict]:
    """
    Procesa una lista de periodos, calculando estados automáticamente si es necesario.
    
    Args:
        periodos: Lista de periodos (puede venir de JSON de BD)
        recalcular_estados: Si True, recalcula estados según fechas actuales
    
    Returns:
        Lista de periodos con estados calculados y validados
    """
    if not periodos:
        return []
    
    periodos_procesados = []
    for periodo in periodos:
        if not isinstance(periodo, dict):
            continue
        
        inicio = periodo.get("inicio")
        fin = periodo.get("fin")
        
        if not inicio or not fin:
            continue
        
        estado_actual = periodo.get("estado")
        observacion = periodo.get("observacion", "sin observaciones")
        es_cancelado = estado_actual == "cancelado"
        
        # Recalcular estado si es necesario
        if recalcular_estados and not es_cancelado:
            estado_calculado = calcular_estado_vacaciones(
                inicio=inicio,
                fin=fin,
                estado_explicito=estado_actual,
                es_cancelado=es_cancelado
            )
        else:
            estado_calculado = estado_actual or calcular_estado_vacaciones(
                inicio=inicio,
                fin=fin,
                es_cancelado=es_cancelado
            )
        
        periodo_procesado = {
            "inicio": inicio,
            "fin": fin,
            "estado": estado_calculado,
            "observacion": observacion
        }
        
        periodos_procesados.append(periodo_procesado)
    
    return periodos_procesados


def procesar_vacaciones_extras_con_estado(
    vacaciones_extras: Optional[Dict],
    recalcular_estados: bool = True
) -> Dict[str, List[Dict]]:
    """
    Procesa vacaciones extras, calculando estados automáticamente si es necesario.
    
    Args:
        vacaciones_extras: Diccionario con estructura {'medico': [...], 'otros': [...]}
        recalcular_estados: Si True, recalcula estados según fechas actuales
    
    Returns:
        Diccionario con vacaciones extras procesadas y estados calculados
    """
    if not vacaciones_extras:
        return {"medico": [], "otros": []}
    
    resultado = {
        "medico": procesar_periodos_con_estado(
            vacaciones_extras.get("medico", []),
            recalcular_estados
        ),
        "otros": procesar_periodos_con_estado(
            vacaciones_extras.get("otros", []),
            recalcular_estados
        )
    }
    
    return resultado


def validar_observacion_requerida(
    periodo_anterior: Optional[Dict],
    periodo_nuevo: Dict,
    accion: str = "actualizar"
) -> tuple[bool, Optional[str]]:
    """
    Valida si se requiere una observación para un cambio.
    
    Args:
        periodo_anterior: Periodo anterior (si existe)
        periodo_nuevo: Periodo nuevo o actualizado
        accion: Tipo de acción ('crear', 'actualizar', 'cancelar')
    
    Returns:
        Tupla (requiere_observacion, mensaje_error)
    """
    observacion = periodo_nuevo.get("observacion", "").strip()
    
    # Si es cancelación, siempre requiere observación
    if periodo_nuevo.get("estado") == "cancelado":
        if not observacion or observacion == "sin observaciones":
            return False, "Se requiere una observación cuando se cancela un periodo"
        if not observacion.lower().startswith("cancelado"):
            return False, "La observación de cancelación debe comenzar con 'cancelado -'"
    
    # Si hay cambio de fechas, requiere observación
    if periodo_anterior:
        fecha_inicio_anterior = periodo_anterior.get("inicio")
        fecha_fin_anterior = periodo_anterior.get("fin")
        fecha_inicio_nueva = periodo_nuevo.get("inicio")
        fecha_fin_nueva = periodo_nuevo.get("fin")
        
        if (fecha_inicio_anterior != fecha_inicio_nueva or 
            fecha_fin_anterior != fecha_fin_nueva):
            if not observacion or observacion == "sin observaciones":
                return False, "Se requiere una observación cuando se cambian las fechas de un periodo"
            if not observacion.lower().startswith("cambio de fecha"):
                return False, "La observación de cambio de fecha debe comenzar con 'cambio de fecha -'"
    
    return True, None

