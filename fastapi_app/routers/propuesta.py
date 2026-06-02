from fastapi import APIRouter, BackgroundTasks, Depends, Query, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Dict
from sqlalchemy.orm import load_only, selectinload
from sqlalchemy import or_
from typing import List, Optional
from ..database import get_db
from ..models.propuesta import Propuesta
from ..models.cartera import Cartera
from ..models.solicitud import Solicitud as SolicitudModel
from ..models.solicitud import ValorSolicitud, TipoSolicitud
from ..models.usuario import Usuario
from ..models.rol_permiso import Rol
from ..schemas.propuesta import PropuestaListadoPage
from ..services.propuesta_filter_service import PropuestaFilterService
from ..models.programa import Programa as ProgramaModel
from ..models.oportunidad import Oportunidad
from ..services.crm_service import actualizar_conciliado_crm_batch, marcar_conciliada_crm_batch
from datetime import datetime

router = APIRouter(prefix="/propuesta", tags=["Propuesta"])


@router.get("/{propuesta_id}/programas-conciliacion")
def obtener_programas_conciliacion(
    propuesta_id: int,
    user_id: Optional[int] = Query(None, description="ID del usuario para filtrar programas por rol"),
    db: Session = Depends(get_db),
):
    """
    Obtiene los programas de una propuesta separados en mes_conciliado y meses_anteriores.
    Igual que informacion_preconciliacion pero para la vista de Conciliaciones.
    """
    propuesta = db.query(Propuesta).filter(Propuesta.id == propuesta_id).first()
    if not propuesta:
        raise HTTPException(status_code=404, detail="Propuesta no encontrada")

    fecha_propuesta = propuesta.fechaPropuesta
    if not fecha_propuesta:
        raise HTTPException(status_code=400, detail="La propuesta no tiene fecha")

    # Calcular mes conciliado (mes anterior a la fecha de propuesta)
    if fecha_propuesta.month == 1:
        mes_conciliado = 12
        anio_conciliado = fecha_propuesta.year - 1
    else:
        mes_conciliado = fecha_propuesta.month - 1
        anio_conciliado = fecha_propuesta.year

    # Calcular tres meses anteriores al mes conciliado (offsets 2, 3, 4)
    meses_anteriores = []
    for offset in [2, 3, 4]:
        mes = fecha_propuesta.month - offset
        anio = fecha_propuesta.year
        while mes <= 0:
            mes += 12
            anio -= 1
        meses_anteriores.append((mes, anio))

    # Filtrar programas según rol del usuario
    if user_id:
        usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
        roles_usuario = {rol.nombre for rol in usuario.roles} if usuario and usuario.roles else set()

        roles_daf = {"DAF - Supervisor", "DAF - Subdirector", "DAF - Admin"}
        roles_ver_todo = roles_daf | {"Comercial - Director"}
        if roles_usuario & roles_ver_todo:
            programas_all = db.query(ProgramaModel).filter(
                ProgramaModel.idPropuesta == propuesta_id
            ).order_by(ProgramaModel.fechaInaguracionPropuesta.desc()).all()
        elif "Comercial - Subdirector" in roles_usuario or "Comercial - Jefe de producto" in roles_usuario:
            condiciones = []
            if "Comercial - Jefe de producto" in roles_usuario:
                condiciones.append(ProgramaModel.idJefeProducto == user_id)
            if "Comercial - Subdirector" in roles_usuario:
                condiciones.append(ProgramaModel.idSubdirector == user_id)
            programas_all = db.query(ProgramaModel).filter(
                ProgramaModel.idPropuesta == propuesta_id,
                or_(*condiciones)
            ).order_by(ProgramaModel.fechaInaguracionPropuesta.desc()).all()
        else:
            programas_all = []
    else:
        programas_all = db.query(ProgramaModel).filter(
            ProgramaModel.idPropuesta == propuesta_id
        ).order_by(ProgramaModel.fechaInaguracionPropuesta.desc()).all()

    # Excluir programas cancelados de los listados (siguen contando para Meta BP en /meta-bp)
    programas_all = [p for p in programas_all if (p.estado or "").strip().lower() != "cancelado"]

    # Separar programas por mes
    programas_mes_conciliado = [
        p for p in programas_all
        if p.fechaInaguracionPropuesta
        and p.fechaInaguracionPropuesta.month == mes_conciliado
        and p.fechaInaguracionPropuesta.year == anio_conciliado
    ]
    programas_tres_meses = [
        p for p in programas_all
        if p.fechaInaguracionPropuesta
        and any(
            p.fechaInaguracionPropuesta.month == m and p.fechaInaguracionPropuesta.year == a
            for m, a in meses_anteriores
        )
    ]

    # Excluir oportunidades eliminadas y en etapas no válidas
    etapas_excluir = ["1 - Interés", "2 - Calificación", "5 - Cerrada/Perdida", "Agregado CRM"]
    oportunidades_all = db.query(Oportunidad).filter(
        Oportunidad.idPropuesta == propuesta_id,
        Oportunidad.etapaVentaPropuesta.notin_(etapas_excluir),
        Oportunidad.eliminado == False
    ).all()

    oportunidades_por_programa = {}
    for o in oportunidades_all:
        oportunidades_por_programa.setdefault(o.idPrograma, []).append(o)

    def build_programa_item(p):
        oportunidades = oportunidades_por_programa.get(p.id, [])
        # Retrocedidos no suman al monto/count real, pero sí al conciliado
        oportunidades_activas = [o for o in oportunidades if not o.retrocedioEnCRM]
        agregados_ultimo = [o for o in oportunidades_activas if o.agregadoUltimoMomento and not o.becado]
        agregados_count = len(agregados_ultimo)
        agregados_monto = sum(o.monto or 0 for o in agregados_ultimo)
        oportunidades_conciliadas = [o for o in oportunidades_activas if not o.agregadoUltimoMomento]
        monto_opty = sum(o.montoPropuesto or 0 for o in oportunidades_conciliadas)
        monto_actual = sum(o.monto or 0 for o in oportunidades_activas)
        count_opty = len(oportunidades_activas)

        alumnos = []
        for o in oportunidades:
            monto_editado = o.montoPropuesto != o.monto if o.monto else False
            alumnos.append({
                "id": o.id,
                "nombre": o.nombre,
                "documentoIdentidad": o.documentoIdentidad,
                "descuento": o.descuento,
                "monto": o.monto,
                "montoPropuesto": o.montoPropuesto,
                "montoEditado": bool(monto_editado),
                "moneda": o.moneda,
                "etapaVentaPropuesta": o.etapaVentaPropuesta,
                "becado": bool(o.becado),
                "posibleAtipico": bool(o.posibleAtipico),
                "conciliado": bool(o.conciliado),
                "retrocedioEnCRM": bool(o.retrocedioEnCRM),
                "agregadoUltimoMomento": bool(o.agregadoUltimoMomento),
                "optyNumber": o.optyNumber,
                "optyId": o.optyId,
            })

        return {
            "id": p.id,
            "codigo": p.codigo,
            "nombre": p.nombre,
            "subdireccion": p.subdireccion,
            "cartera": p.cartera,
            "mes": p.mes,
            "fechaDeInaguracion": p.fechaInaguracionPropuesta,
            "metaDeVenta": p.metaDeVenta,
            "metaDeAlumnos": p.metaDeAlumnos,
            "alumnosReales": count_opty,
            "montoReal": monto_opty,
            "montoActual": monto_actual,
            "enRiesgo": bool(p.enRiesgo),
            "comentario": p.comentario,
            "fijoFueraDeCounter": (p.fijoFueraDeCounter or 0) + agregados_count,
            "montoFijoFueraDeCounter": (p.montoFijoFueraDeCounter or 0.0) + agregados_monto,
            "alumnos": alumnos,
        }

    items_conciliado = [build_programa_item(p) for p in programas_mes_conciliado]
    items_anteriores = [build_programa_item(p) for p in programas_tres_meses]

    # === FLAGS DE SOLICITUDES DE CONCILIACION ===
    estado_nombre = propuesta.estadoPropuesta.nombre if propuesta.estadoPropuesta else None
    es_conciliada = estado_nombre == "CONCILIADA"

    tipo_aprobacion_conc = db.query(TipoSolicitud).filter_by(nombre="APROBACION_JP_CONCILIACION").first()
    solicitudes_conciliacion = []
    if tipo_aprobacion_conc:
        solicitudes_conciliacion = db.query(SolicitudModel).filter(
            SolicitudModel.idPropuesta == propuesta_id,
            SolicitudModel.tipoSolicitud_id == tipo_aprobacion_conc.id,
        ).all()

    flags = {}
    solicitudes_resumen = []
    # Cache de nombres de usuario para no repetir queries
    _user_name_cache = {}
    def _get_user_name(uid):
        if uid not in _user_name_cache:
            u = db.query(Usuario).filter(Usuario.id == uid).first()
            _user_name_cache[uid] = u.nombre if u else None
        return _user_name_cache[uid]

    for s in solicitudes_conciliacion:
        solicitudes_resumen.append({
            "id": s.id,
            "idUsuarioGenerador": s.idUsuarioGenerador,
            "idUsuarioReceptor": s.idUsuarioReceptor,
            "nombreGenerador": _get_user_name(s.idUsuarioGenerador),
            "nombreReceptor": _get_user_name(s.idUsuarioReceptor),
            "tipoSolicitud": s.tipoSolicitud.nombre if s.tipoSolicitud else None,
            "valorSolicitud": s.valorSolicitud.nombre if s.valorSolicitud else None,
            "abierta": s.abierta,
            "comentario": s.comentario,
        })

    es_proyectada = estado_nombre == "PROYECTADA"

    # Determinar roles del usuario actual (necesario tanto para CONCILIADA como para PROYECTADA)
    es_jp = es_subdirector = es_director_comercial = es_daf = False
    if user_id:
        usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
        roles_usuario = {rol.nombre for rol in (usuario.roles if usuario and usuario.roles else [])}
        es_jp = "Comercial - Jefe de producto" in roles_usuario
        es_subdirector = "Comercial - Subdirector" in roles_usuario
        es_director_comercial = "Comercial - Director" in roles_usuario
        es_daf = any(r.startswith("DAF") for r in roles_usuario)

    # Filtrar solicitudes_resumen según el rol:
    # - PROYECTADA: todos ven todas (modo solo lectura)
    # - Director Comercial: ve todas
    # - Subdirector (y también JP): ve las que le corresponde aprobar (receptor)
    # - JP puro: ve solo las que él generó
    # - Sin rol conocido: no ve ninguna
    if es_proyectada:
        pass  # modo solo lectura: todos ven todas las solicitudes
    elif user_id:
        if es_director_comercial:
            pass  # ve todas, no filtrar
        elif es_subdirector:
            # Subdirector (con o sin rol JP): ve las que son para él como receptor
            # Si además es JP, también ve las que generó
            if es_jp:
                solicitudes_resumen = [r for r in solicitudes_resumen
                                       if r["idUsuarioReceptor"] == user_id or r["idUsuarioGenerador"] == user_id]
            else:
                solicitudes_resumen = [r for r in solicitudes_resumen if r["idUsuarioReceptor"] == user_id]
        elif es_jp:
            # JP puro: solo ve las suyas propias
            solicitudes_resumen = [r for r in solicitudes_resumen if r["idUsuarioGenerador"] == user_id]
        else:
            solicitudes_resumen = []
    else:
        solicitudes_resumen = []

    if user_id and es_conciliada:
        if es_jp:
            # Solicitudes que ESTE JP generó
            mis_solicitudes = [s for s in solicitudes_conciliacion if s.idUsuarioGenerador == user_id]
            ya_solicito = len(mis_solicitudes) > 0 and all(not s.abierta for s in mis_solicitudes)
            alguna_rechazada = any(s.abierta for s in mis_solicitudes)

            flags["verBotonSolicitarAprobacion"] = True
            flags["yaSolicito"] = ya_solicito and not alguna_rechazada
            flags["solicitudRechazada"] = alguna_rechazada

        if es_subdirector:
            # Solicitudes donde ESTE subdirector es receptor y están pendientes
            solicitudes_para_mi = [s for s in solicitudes_conciliacion
                                   if s.idUsuarioReceptor == user_id
                                   and not s.abierta
                                   and s.valorSolicitud and s.valorSolicitud.nombre == "PENDIENTE"]
            flags["verBotonAprobarConciliacion"] = len(solicitudes_para_mi) > 0
            flags["solicitudesPendientesParaMi"] = [{"id": s.id, "idJP": s.idUsuarioGenerador} for s in solicitudes_para_mi]

        if es_director_comercial:
            todas_aceptadas = (
                len(solicitudes_conciliacion) > 0
                and all(
                    s.valorSolicitud and s.valorSolicitud.nombre == "ACEPTADO"
                    for s in solicitudes_conciliacion
                )
            )
            flags["verBotonProyectar"] = True
            flags["puedeProyectar"] = todas_aceptadas

    # Subdirector puro, Director y DAF no pueden sincronizar programas
    # (Subdirector que además es JP sí puede)
    if (es_subdirector and not es_jp) or (es_director_comercial and not es_jp) or es_daf:
        flags["noActualizar"] = True

    if es_proyectada:
        flags["noVerBotones"] = True
        flags["noEditarNada"] = True

    return {
        "propuesta": {
            "id": propuesta.id,
            "nombre": propuesta.nombre,
            "fechaPropuesta": propuesta.fechaPropuesta,
            "horaPropuesta": propuesta.horaPropuesta,
            "estado": estado_nombre,
        },
        "mesConciliado": items_conciliado,
        "mesesAnteriores": items_anteriores,
        "solicitudesConciliacion": solicitudes_resumen,
        "flags": flags,
    }


# Meta de venta BP (Business Plan) dictada manualmente por (año, mes).
# Valores fijos: NO se calculan desde la BD ni desde el Excel.
META_VENTA_BP_POR_MES = {
    (2026, 1): 1463749.9,
    (2026, 2): 1796625.0,
    (2026, 3): 3421088.0,
    (2026, 4): 19389925.0,
    (2026, 5): 10191727.7,
    (2026, 6): 11506703.0,
    (2026, 7): 5860700.0,
    (2026, 8): 17639585.0,
    (2026, 9): 10918190.0,
    (2026, 10): 8359688.0,
    (2026, 11): 21939385.0,
    (2026, 12): 3526263.0,
}


@router.get("/{propuesta_id}/meta-bp")
def obtener_meta_bp(
    propuesta_id: int,
    user_id: Optional[int] = Query(None, description="(no usado) compatibilidad con el cliente"),
    db: Session = Depends(get_db),
):
    """
    Devuelve las metas de venta BP (Business Plan) de una propuesta.

    Los valores son fijos y dictados manualmente por (año, mes) en
    META_VENTA_BP_POR_MES. NO se calculan desde programas ni desde el Excel.
    Solo se usa la fecha de la propuesta para determinar qué meses aplican.

    Se entrega separado en dos sumas no solapadas:
      - metaVentaBpMesConciliado: meta BP del mes conciliado.
      - metaVentaBpTresMeses:     suma de la meta BP de los 3 meses anteriores.
    """
    propuesta = db.query(Propuesta).filter(Propuesta.id == propuesta_id).first()
    if not propuesta:
        raise HTTPException(status_code=404, detail="Propuesta no encontrada")

    fecha_propuesta = propuesta.fechaPropuesta
    if not fecha_propuesta:
        raise HTTPException(status_code=400, detail="La propuesta no tiene fecha")

    # Mes conciliado = mes anterior a la fecha de propuesta (mismo cálculo que el endpoint principal)
    if fecha_propuesta.month == 1:
        mes_conciliado = 12
        anio_conciliado = fecha_propuesta.year - 1
    else:
        mes_conciliado = fecha_propuesta.month - 1
        anio_conciliado = fecha_propuesta.year

    # Tres meses anteriores al mes conciliado (offsets 2, 3, 4)
    meses_anteriores = []
    for offset in [2, 3, 4]:
        mes = fecha_propuesta.month - offset
        anio = fecha_propuesta.year
        while mes <= 0:
            mes += 12
            anio -= 1
        meses_anteriores.append((mes, anio))

    meta_bp_mes_conciliado = META_VENTA_BP_POR_MES.get((anio_conciliado, mes_conciliado), 0.0)
    meta_bp_tres_meses = sum(
        META_VENTA_BP_POR_MES.get((anio, mes), 0.0) for mes, anio in meses_anteriores
    )

    return {
        "metaVentaBpMesConciliado": meta_bp_mes_conciliado,
        "metaVentaBpTresMeses": meta_bp_tres_meses,
    }


@router.get("/conciliaciones-comparables")
def listar_conciliaciones_comparables(
    excluir_id: Optional[int] = Query(None, description="ID de propuesta a excluir (la actual)"),
    db: Session = Depends(get_db),
):
    """
    Lista las propuestas en estado CONCILIADA o PROYECTADA (no GENERADA ni CANCELADA),
    para usarlas como baseline en el Control de Cambios.
    """
    from ..models.propuesta import EstadoPropuesta as EstadoPropuestaModel
    q = (
        db.query(Propuesta)
        .join(Propuesta.estadoPropuesta)
        .filter(EstadoPropuestaModel.nombre.in_(["CONCILIADA", "PROYECTADA"]))
    )
    if excluir_id:
        q = q.filter(Propuesta.id != excluir_id)
    propuestas = q.order_by(Propuesta.id.desc()).all()
    return [
        {
            "id": p.id,
            "nombre": p.nombre,
            "fechaPropuesta": p.fechaPropuesta,
            "horaPropuesta": p.horaPropuesta,
            "estado": p.estadoPropuesta.nombre if p.estadoPropuesta else None,
        }
        for p in propuestas
    ]


# Único cambio de etapa relevante: pasar de Matrícula o Cerrada/Ganada a Cerrada/Perdida
# (una venta que estaba ganada/matriculada y terminó dada de baja).
_ETAPA_PERDIDA = "5 - Cerrada/Perdida"
_ETAPAS_ORIGEN_BAJA = {"3 - Matrícula", "4 - Cerrada/Ganada"}


@router.get("/{propuesta_id}/control-de-cambios")
def control_de_cambios(
    propuesta_id: int,
    baseline_id: int = Query(..., description="ID de la conciliación seleccionada (baseline a comparar)"),
    db: Session = Depends(get_db),
):
    """
    Compara los programas de los '3 meses anteriores' de la propuesta actual contra una
    conciliación previa (baseline), a nivel alumno, enfocándose en los conciliados.

    - Match de programas por `codigo` CRM.
    - Match de alumnos por documentoIdentidad DENTRO del mismo programa (son únicos ahí).
    - Universo: alumnos con conciliado=True en cualquiera de las dos conciliaciones.
    - Cambios detectados por alumno: etapa, monto, dejó de estar conciliado, desapareció/eliminado, nuevo.
    """
    actual = db.query(Propuesta).filter(Propuesta.id == propuesta_id).first()
    if not actual:
        raise HTTPException(status_code=404, detail="Propuesta actual no encontrada")
    baseline = db.query(Propuesta).filter(Propuesta.id == baseline_id).first()
    if not baseline:
        raise HTTPException(status_code=404, detail="Conciliación baseline no encontrada")
    if not actual.fechaPropuesta:
        raise HTTPException(status_code=400, detail="La propuesta actual no tiene fecha")

    # 3 meses anteriores al mes conciliado de la propuesta ACTUAL (offsets 2,3,4)
    meses_anteriores = []
    for offset in [2, 3, 4]:
        mes = actual.fechaPropuesta.month - offset
        anio = actual.fechaPropuesta.year
        while mes <= 0:
            mes += 12
            anio -= 1
        meses_anteriores.append((mes, anio))

    programas_actual = [
        p for p in db.query(ProgramaModel).filter(ProgramaModel.idPropuesta == propuesta_id).all()
        if p.fechaInaguracionPropuesta
        and any(p.fechaInaguracionPropuesta.month == m and p.fechaInaguracionPropuesta.year == a
                for m, a in meses_anteriores)
    ]

    # Programas del baseline indexados por codigo
    programas_baseline = db.query(ProgramaModel).filter(ProgramaModel.idPropuesta == baseline_id).all()
    baseline_por_codigo = {}
    for p in programas_baseline:
        if p.codigo is not None:
            baseline_por_codigo.setdefault(str(p.codigo).strip(), p)

    # Oportunidades de ambas propuestas, indexadas por idPrograma
    def opps_por_programa(prop_id):
        d = {}
        for o in db.query(Oportunidad).filter(Oportunidad.idPropuesta == prop_id).all():
            d.setdefault(o.idPrograma, []).append(o)
        return d

    opps_actual = opps_por_programa(propuesta_id)
    opps_baseline = opps_por_programa(baseline_id)

    def norm_dni(o):
        return str(o.documentoIdentidad or "").strip()

    items = []
    for p in programas_actual:
        codigo = str(p.codigo).strip() if p.codigo is not None else None
        base_prog = baseline_por_codigo.get(codigo) if codigo else None

        cur_list = [o for o in opps_actual.get(p.id, []) if not o.agregadoUltimoMomento]
        base_list = opps_baseline.get(base_prog.id, []) if base_prog else []

        cur_by_dni = {norm_dni(o): o for o in cur_list if norm_dni(o)}
        base_by_dni = {norm_dni(o): o for o in base_list if norm_dni(o)}

        # Universo: conciliado=True en cualquiera de las dos
        universo = set()
        for dni, o in cur_by_dni.items():
            if o.conciliado:
                universo.add(dni)
        for dni, o in base_by_dni.items():
            if o.conciliado:
                universo.add(dni)

        alumnos_cambios = []
        for dni in universo:
            cur = cur_by_dni.get(dni)
            base = base_by_dni.get(dni)
            cambios = []

            if base and cur:
                base_etapa = (base.etapaVentaPropuesta or "").strip()
                cur_etapa = (cur.etapaVentaPropuesta or "").strip()
                # Solo interesa la baja: Matrícula/Cerrada-Ganada -> Cerrada/Perdida
                if base_etapa in _ETAPAS_ORIGEN_BAJA and cur_etapa == _ETAPA_PERDIDA:
                    cambios.append("etapa")
                # Y cambios de monto entre conciliadas
                if round(base.monto or 0, 2) != round(cur.monto or 0, 2):
                    cambios.append("monto")

            if not cambios:
                continue

            ref = cur or base
            alumnos_cambios.append({
                "nombre": ref.nombre if ref else None,
                "documentoIdentidad": dni,
                "cambios": cambios,
                "antes": None if not base else {
                    "etapa": base.etapaVentaPropuesta,
                    "monto": base.monto,
                    "moneda": base.moneda,
                    "conciliado": bool(base.conciliado),
                },
                "ahora": None if not cur else {
                    "etapa": cur.etapaVentaPropuesta,
                    "monto": cur.monto,
                    "moneda": cur.moneda,
                    "conciliado": bool(cur.conciliado),
                    "eliminado": bool(cur.eliminado),
                },
            })

        items.append({
            "id": p.id,
            "codigo": p.codigo,
            "nombre": p.nombre,
            "subdireccion": p.subdireccion,
            "cartera": p.cartera,
            "fechaDeInaguracion": p.fechaInaguracionPropuesta,
            "metaDeVenta": p.metaDeVenta,
            "existeEnBaseline": base_prog is not None,
            "tieneCambio": len(alumnos_cambios) > 0,
            "cantidadCambios": len(alumnos_cambios),
            "alumnosCambios": alumnos_cambios,
        })

    # Programas con cambios primero
    items.sort(key=lambda x: (not x["tieneCambio"], x["nombre"] or ""))

    return {
        "propuestaActual": {"id": actual.id, "nombre": actual.nombre},
        "baseline": {
            "id": baseline.id,
            "nombre": baseline.nombre,
            "estado": baseline.estadoPropuesta.nombre if baseline.estadoPropuesta else None,
        },
        "totalProgramasConCambio": sum(1 for it in items if it["tieneCambio"]),
        "items": items,
    }


@router.post("/{propuesta_id}/sync-todos-fijo-fuera-counter")
def sync_todos_fijo_fuera_counter(propuesta_id: int, db: Session = Depends(get_db)):
    """
    Consulta Oracle Sales Cloud y actualiza el conteo de 'Fijo fuera de counter'
    para todos los programas de una propuesta.
    """
    from ..services.crm_service import obtener_fijos_fuera_counter, obtener_etapas_actuales_convertidos

    propuesta = db.query(Propuesta).filter(Propuesta.id == propuesta_id).first()
    if not propuesta:
        raise HTTPException(status_code=404, detail="Propuesta no encontrada")

    programas = db.query(ProgramaModel).filter(
        ProgramaModel.idPropuesta == propuesta_id,
        ProgramaModel.codigo.isnot(None),
    ).all()

    _ETAPAS_RETROCESO = {"1 - Interés", "2 - Calificación", "5 - Cerrada/Perdida"}
    resultados = []
    errores = 0
    total_retrocesos = 0

    for p in programas:
        try:
            resultado = obtener_fijos_fuera_counter(p.codigo)
            p.fijoFueraDeCounter = resultado["count"]
            p.montoFijoFueraDeCounter = resultado["monto"]

            # Detectar retrocesos de etapa para este programa — marcar flag, NO cambiar etapa
            by_party, by_dni = obtener_etapas_actuales_convertidos(p.codigo)
            oportunidades_db = db.query(Oportunidad).filter(
                Oportunidad.idPrograma == p.id,
                Oportunidad.eliminado == False,
            ).all()
            retrocesos = 0
            for opp in oportunidades_db:
                party = str(opp.partyNumber).strip() if opp.partyNumber else None
                dni = str(opp.documentoIdentidad).strip() if opp.documentoIdentidad else None
                etapa_crm = (party and by_party.get(party)) or (dni and by_dni.get(dni)) or ""
                retrocedio = bool(etapa_crm and etapa_crm in _ETAPAS_RETROCESO)
                if opp.retrocedioEnCRM != retrocedio:
                    opp.retrocedioEnCRM = retrocedio
                    if retrocedio:
                        retrocesos += 1
            total_retrocesos += retrocesos

            agregados_ultimo = [
                o for o in oportunidades_db
                if o.agregadoUltimoMomento and not o.retrocedioEnCRM and not o.becado
            ]
            agregados_count = len(agregados_ultimo)
            agregados_monto = sum(o.monto or 0 for o in agregados_ultimo)

            resultados.append({
                "idPrograma": p.id,
                "fijoFueraDeCounter": resultado["count"] + agregados_count,
                "montoFijoFueraDeCounter": resultado["monto"] + agregados_monto,
                "retrocesos_actualizados": retrocesos,
            })
        except Exception as e:
            errores += 1
            resultados.append({"idPrograma": p.id, "error": str(e)})

    db.commit()

    return {
        "actualizados": len(resultados) - errores,
        "errores": errores,
        "retrocesos_actualizados": total_retrocesos,
        "resultados": resultados,
    }


@router.get("/{propuesta_id}/detalle")
def obtener_resumen_propuesta(
    propuesta_id: int,
    db: Session = Depends(get_db),
):
    propuesta = (
        db.query(Propuesta)
        .options(load_only(Propuesta.nombre, Propuesta.fechaPropuesta, Propuesta.horaPropuesta))
        .join(Propuesta.estadoPropuesta)
        .filter(Propuesta.id == propuesta_id)
        .first()
    )

    if not propuesta:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Propuesta no encontrada")

    return {
        "nombre": propuesta.nombre,
        "fechaPropuesta": propuesta.fechaPropuesta,
        "horaPropuesta": propuesta.horaPropuesta,
        "estadoPropuesta": propuesta.estadoPropuesta.nombre if propuesta.estadoPropuesta else None,
    }


@router.get("/estados-conciliaciones")
def obtener_estados_conciliaciones(db: Session = Depends(get_db)):
    """
    Obtiene el conteo de propuestas para la vista de Conciliaciones.
    Returns:
        - conciliadas: conteo de propuestas en estado CONCILIADA
        - proyectadas: conteo de propuestas en estado PROYECTADA
        - canceladas: conteo de propuestas en estado CANCELADA
    """
    from ..models.propuesta import EstadoPropuesta as EstadoPropuestaModel
    conciliadas = db.query(Propuesta).join(EstadoPropuestaModel).filter(EstadoPropuestaModel.nombre == "CONCILIADA").count()
    proyectadas = db.query(Propuesta).join(EstadoPropuestaModel).filter(EstadoPropuestaModel.nombre == "PROYECTADA").count()
    canceladas = db.query(Propuesta).join(EstadoPropuestaModel).filter(EstadoPropuestaModel.nombre == "CANCELADA").count()
    return {"conciliadas": conciliadas, "proyectadas": proyectadas, "canceladas": canceladas}


@router.get("/estados")
def obtener_estados_propuesta(db: Session = Depends(get_db)):
    """
    Obtiene el conteo de propuestas por categoría de estado.
    
    Returns:
        - activos: conteo de propuestas en estados activos (todos excepto CONCILIADA y CANCELADA)
        - conciliadas: conteo de propuestas en estado CONCILIADA
        - canceladas: conteo de propuestas en estado CANCELADA
    """
    counts = PropuestaFilterService.get_estado_counts(db)
    # Incluir PROYECTADA en el conteo de "conciliadas" para la vista de Conciliaciones
    from ..models.propuesta import EstadoPropuesta as EstadoPropuestaModel
    proyectadas_count = db.query(Propuesta).join(EstadoPropuestaModel).filter(
        EstadoPropuestaModel.nombre == "PROYECTADA"
    ).count()
    counts["conciliadas"] = counts.get("conciliadas", 0) + proyectadas_count
    return counts


@router.get("/listar", response_model=PropuestaListadoPage)
def listar_propuestas(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1),
    fechaDesde: str = Query(None, description="Fecha desde (YYYY-MM-DD)", alias="fechaDesde"),
    fechaHasta: str = Query(None, description="Fecha hasta (YYYY-MM-DD)", alias="fechaHasta"),
    nombre: str = Query(None, description="Filtrar por nombre de propuesta (búsqueda parcial)", alias="nombre"),
    estado: Optional[List[str]] = Query(None, description="Filtrar por nombres de estado de propuesta (ej: CONCILIADA, CANCELADA)", alias="estado"),
    db: Session = Depends(get_db),
):
    """
    Lista propuestas con filtros aplicados.
    
    Reglas de filtrado de estados:
    - Sin parámetro estado: muestra todas las propuestas excepto CONCILIADA y CANCELADA
    - Con parámetro estado: muestra únicamente las propuestas de los estados especificados
    
    Estados disponibles: PROGRAMADA, GENERADA, PRECONCILIADA, APROBADA, CONCILIADA, CANCELADA
    """
    # Validar nombres de estado si se proporcionan
    if estado:
        # Asegurar que estado sea una lista
        if isinstance(estado, str):
            estado_list = [estado]
        else:
            estado_list = estado
        
        valid_estado_names, errors = PropuestaFilterService.validate_state_names(estado_list)
        if errors:
            raise HTTPException(status_code=400, detail=f"Estados inválidos: {', '.join(errors)}")
        estado_names = valid_estado_names
    else:
        estado_names = None

    # Query base con carga de relaciones necesarias
    base_query = db.query(Propuesta).options(
        selectinload(Propuesta.estadoPropuesta),
        selectinload(Propuesta.carteras).load_only(Cartera.nombre),
    )

    # Aplicar filtro de estados usando el servicio
    base_query = PropuestaFilterService.apply_state_filter(base_query, estado_names)

    # Filtrado por fechas
    if fechaDesde:
        try:
            fecha_desde_dt = datetime.strptime(fechaDesde, "%Y-%m-%d")
            base_query = base_query.filter(Propuesta.fechaPropuesta >= fecha_desde_dt)
        except Exception:
            pass
    if fechaHasta:
        try:
            fecha_hasta_dt = datetime.strptime(fechaHasta, "%Y-%m-%d")
            base_query = base_query.filter(Propuesta.fechaPropuesta <= fecha_hasta_dt)
        except Exception:
            pass
    
    # Filtrado por nombre
    if nombre:
        base_query = base_query.filter(Propuesta.nombre.ilike(f"%{nombre}%"))

    total = base_query.count()
    offset = (page - 1) * size

    propuestas: List[Propuesta] = (
        base_query.order_by(Propuesta.id.desc()).offset(offset).limit(size).all()
    )

    items = [
        {
            "id": p.id,
            "nombre": p.nombre,
            "fechaPropuesta": p.fechaPropuesta,
            "estado": p.estadoPropuesta.nombre if p.estadoPropuesta else None,
            "carteras": [c.nombre for c in p.carteras] if p.carteras else [],
        }
        for p in propuestas
    ]

    pages = (total + size - 1) // size if size else 0

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
    }


@router.patch("/avanzar-estado")
def avanzar_estado_propuesta(
    body: dict = Body(..., example={"idUsuario": 1, "idPropuesta": 2}),
    db: Session = Depends(get_db),
):
    """
    Avanza el estado de la propuesta en +1
    """
    propuesta_id = body.get("idPropuesta")
    
    # Buscar propuesta
    propuesta = db.query(Propuesta).filter(Propuesta.id == propuesta_id).first()
    
    if not propuesta:
        raise HTTPException(status_code=404, detail="Propuesta no encontrada")
    
    # Incrementar el estado en +1
    nuevo_estado_id = propuesta.estadoPropuesta_id + 1
    propuesta.estadoPropuesta_id = nuevo_estado_id
    db.commit()
    db.refresh(propuesta)
    
    return {
        "msg": "Estado de propuesta actualizado correctamente",
        "idPropuesta": propuesta.id,
        "estadoAnterior": propuesta.estadoPropuesta_id - 1,
        "estadoNuevo": propuesta.estadoPropuesta_id,
        "nombreEstado": propuesta.estadoPropuesta.nombre if propuesta.estadoPropuesta else None
    }


@router.patch("/cancelar")
def cancelar_propuesta(
    body: dict = Body(..., example={"id": 1}),
    db: Session = Depends(get_db),
):
    """
    Cancela una propuesta cambiando su estado a CANCELADA
    """
    propuesta_id = body.get("id")
    
    if not propuesta_id:
        raise HTTPException(status_code=400, detail="El campo 'id' es requerido")
    
    # Buscar el estado CANCELADA en la base de datos
    from ..models.propuesta import EstadoPropuesta
    estado_cancelada = db.query(EstadoPropuesta).filter(EstadoPropuesta.nombre == "CANCELADA").first()
    
    if not estado_cancelada:
        raise HTTPException(status_code=500, detail="Estado CANCELADA no encontrado en la base de datos")
    
    # Buscar propuesta
    propuesta = db.query(Propuesta).filter(Propuesta.id == propuesta_id).first()
    
    if not propuesta:
        raise HTTPException(status_code=404, detail="Propuesta no encontrada")
    
    # Verificar que la propuesta no esté ya cancelada
    if propuesta.estadoPropuesta_id == estado_cancelada.id:
        raise HTTPException(status_code=400, detail="La propuesta ya está cancelada")
    
    # Guardar estado anterior para la respuesta
    estado_anterior_id = propuesta.estadoPropuesta_id
    estado_anterior_nombre = propuesta.estadoPropuesta.nombre if propuesta.estadoPropuesta else None
    
    # Cambiar estado a CANCELADA
    propuesta.estadoPropuesta_id = estado_cancelada.id
    db.commit()
    db.refresh(propuesta)
    
    return {
        "msg": "Propuesta cancelada exitosamente",
        "idPropuesta": propuesta.id,
        "estadoAnterior": {
            "id": estado_anterior_id,
            "nombre": estado_anterior_nombre
        },
        "estadoNuevo": {
            "id": propuesta.estadoPropuesta_id,
            "nombre": propuesta.estadoPropuesta.nombre if propuesta.estadoPropuesta else "CANCELADA"
        }
    }


# Progress tracker para sync CRM en background (por propuesta_id)
_crm_progress: Dict[int, dict] = {}


def _sync_crm_background(propuesta_id: int, opty_data_validas: list, opty_numbers_cerrada: list):
    """Ejecuta los PATCHes al CRM en background y actualiza el progreso."""
    total = len(opty_data_validas) + len(opty_numbers_cerrada)
    _crm_progress[propuesta_id] = {"total": total, "done": 0, "errors": 0, "finished": False}

    from ..services.crm_service import marcar_conciliada_crm, actualizar_conciliado_crm
    from concurrent.futures import ThreadPoolExecutor, as_completed

    tasks = (
        [("valida", item) for item in opty_data_validas] +
        [("cerrada", opty) for opty in opty_numbers_cerrada]
    )

    def run_one(task):
        kind, data = task
        if kind == "valida":
            marcar_conciliada_crm(data["opty_number"], data["fecha_conciliacion"], data["ya_tiene_registro"])
        else:
            actualizar_conciliado_crm(data, conciliado=False)

    max_workers = min(len(tasks), 20) if tasks else 1
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(run_one, t): t for t in tasks}
        for future in as_completed(futures):
            try:
                future.result()
                _crm_progress[propuesta_id]["done"] += 1
            except Exception as e:
                _crm_progress[propuesta_id]["errors"] += 1
                print(f"[CRM BG] Error: {e}")

    _crm_progress[propuesta_id]["finished"] = True
    print(f"[CRM BG] Propuesta {propuesta_id}: {_crm_progress[propuesta_id]}")


@router.get("/{propuesta_id}/crm-sync-progress")
def get_crm_sync_progress(propuesta_id: int):
    """Retorna el progreso del sync CRM en background para una propuesta."""
    return _crm_progress.get(propuesta_id, {"total": 0, "done": 0, "errors": 0, "finished": True})


@router.patch("/conciliar")
def conciliar_propuesta(
    background_tasks: BackgroundTasks,
    body: dict = Body(
        ...,
        example={
            "idPropuesta": 1
        }
    ),
    db: Session = Depends(get_db)
):
    """
    Concilia una propuesta cambiando su estado de PRECONCILIADA a CONCILIADA
    """
    id_propuesta = body.get("idPropuesta")
    
    if not id_propuesta:
        raise HTTPException(status_code=400, detail="El campo 'idPropuesta' es requerido")
    
    # Buscar el estado CONCILIADA en la base de datos
    from ..models.propuesta import EstadoPropuesta
    estado_conciliada = db.query(EstadoPropuesta).filter(EstadoPropuesta.nombre == "CONCILIADA").first()
    
    if not estado_conciliada:
        raise HTTPException(status_code=500, detail="Estado CONCILIADA no encontrado en la base de datos")
    
    # Buscar propuesta
    propuesta = db.query(Propuesta).filter(Propuesta.id == id_propuesta).first()
    
    if not propuesta:
        raise HTTPException(status_code=404, detail="Propuesta no encontrada")
    
    # Verificar que la propuesta esté en estado PRECONCILIADA
    estado_actual_nombre = propuesta.estadoPropuesta.nombre if propuesta.estadoPropuesta else None
    if estado_actual_nombre != "PRECONCILIADA":
        raise HTTPException(
            status_code=400, 
            detail=f"La propuesta debe estar en estado PRECONCILIADA para ser conciliada. Estado actual: {estado_actual_nombre}"
        )
    
    # Guardar estado anterior para la respuesta
    estado_anterior_id = propuesta.estadoPropuesta_id
    estado_anterior_nombre = estado_actual_nombre
    
    # Cambiar estado a CONCILIADA
    propuesta.estadoPropuesta_id = estado_conciliada.id

    from datetime import date as _date
    fecha_conciliacion = _date.today().isoformat()

    # Calcular rango de fechas en scope (mismo criterio que la vista de conciliación)
    fp = propuesta.fechaPropuesta
    mes_conc = fp.month - 1 if fp.month > 1 else 12
    anio_conc = fp.year if fp.month > 1 else fp.year - 1
    meses_scope = [(mes_conc, anio_conc)]
    for offset in [2, 3, 4]:
        m = fp.month - offset
        a = fp.year
        while m <= 0:
            m += 12
            a -= 1
        meses_scope.append((m, a))

    # IDs de programas en scope (mes conciliado + 3 meses anteriores)
    programas_scope = db.query(ProgramaModel).filter(
        ProgramaModel.idPropuesta == id_propuesta
    ).all()
    ids_programas_scope = {
        p.id for p in programas_scope
        if p.fechaInaguracionPropuesta
        and any(
            p.fechaInaguracionPropuesta.month == m and p.fechaInaguracionPropuesta.year == a
            for m, a in meses_scope
        )
    }

    # Marcar como conciliadas solo las oportunidades de programas en scope
    etapas_excluir = ["1 - Interés", "2 - Calificación", "5 - Cerrada/Perdida", "Agregado CRM"]
    oportunidades_validas = db.query(Oportunidad).filter(
        Oportunidad.idPropuesta == id_propuesta,
        Oportunidad.idPrograma.in_(ids_programas_scope),
        Oportunidad.eliminado == False,
        Oportunidad.etapaVentaPropuesta.notin_(etapas_excluir),
    ).all()

    for opp in oportunidades_validas:
        opp.conciliado = True
        opp.CTRFechaDeUltimaConciliacion_c = _date.today()
        if not opp.CTRRegistroDeVentaConciliada_c:
            opp.CTRRegistroDeVentaConciliada_c = "Y"

    # Recopilar datos para actualizar en CRM (optyNumbers válidos)
    opty_data_validas = [
        {
            "opty_number": str(opp.optyNumber),
            "fecha_conciliacion": fecha_conciliacion,
            "ya_tiene_registro": bool(opp.CTRRegistroDeVentaConciliada_c),
        }
        for opp in oportunidades_validas
        if opp.optyNumber
    ]

    # Recopilar optyNumbers a marcar como N: Cerrada/Perdida + descartados
    oportunidades_n = db.query(Oportunidad.optyNumber).filter(
        Oportunidad.idPropuesta == id_propuesta,
        Oportunidad.idPrograma.in_(ids_programas_scope),
        Oportunidad.optyNumber.isnot(None),
        or_(
            Oportunidad.etapaVentaPropuesta == "5 - Cerrada/Perdida",
            Oportunidad.eliminado == True,
        )
    ).all()
    opty_numbers_cerrada = [str(row[0]) for row in oportunidades_n if row[0]]

    db.commit()
    db.refresh(propuesta)

    # Lanzar sync CRM en background (no bloquea la respuesta)
    total_crm = len(opty_data_validas) + len(opty_numbers_cerrada)
    background_tasks.add_task(_sync_crm_background, id_propuesta, opty_data_validas, opty_numbers_cerrada)

    return {
        "msg": "Propuesta conciliada exitosamente",
        "idPropuesta": propuesta.id,
        "total_crm": total_crm,
        "estadoAnterior": {
            "id": estado_anterior_id,
            "nombre": estado_anterior_nombre
        },
        "estadoNuevo": {
            "id": propuesta.estadoPropuesta_id,
            "nombre": propuesta.estadoPropuesta.nombre if propuesta.estadoPropuesta else "CONCILIADA"
        },
    }


@router.patch("/proyectar")
def proyectar_propuesta(
    body: dict = Body(
        ...,
        example={
            "idPropuesta": 1
        }
    ),
    db: Session = Depends(get_db)
):
    """
    Proyecta una propuesta cambiando su estado de CONCILIADA a PROYECTADA.
    Solo se permite si todas las solicitudes APROBACION_JP_CONCILIACION están ACEPTADAS.
    """
    id_propuesta = body.get("idPropuesta")

    if not id_propuesta:
        raise HTTPException(status_code=400, detail="El campo 'idPropuesta' es requerido")

    from ..models.propuesta import EstadoPropuesta
    estado_proyectada = db.query(EstadoPropuesta).filter(EstadoPropuesta.nombre == "PROYECTADA").first()
    if not estado_proyectada:
        raise HTTPException(status_code=500, detail="Estado PROYECTADA no encontrado en la base de datos")

    propuesta = db.query(Propuesta).filter(Propuesta.id == id_propuesta).first()
    if not propuesta:
        raise HTTPException(status_code=404, detail="Propuesta no encontrada")

    estado_actual = propuesta.estadoPropuesta.nombre if propuesta.estadoPropuesta else None
    if estado_actual != "CONCILIADA":
        raise HTTPException(
            status_code=400,
            detail=f"La propuesta debe estar en estado CONCILIADA para ser proyectada. Estado actual: {estado_actual}"
        )

    # Verificar que todas las solicitudes de conciliación estén aprobadas
    tipo_aprobacion = db.query(TipoSolicitud).filter_by(nombre="APROBACION_JP_CONCILIACION").first()
    if tipo_aprobacion:
        solicitudes = db.query(SolicitudModel).filter(
            SolicitudModel.idPropuesta == id_propuesta,
            SolicitudModel.tipoSolicitud_id == tipo_aprobacion.id,
        ).all()
        if solicitudes:
            todas_aceptadas = all(
                s.valorSolicitud and s.valorSolicitud.nombre == "ACEPTADO"
                for s in solicitudes
            )
            if not todas_aceptadas:
                raise HTTPException(
                    status_code=400,
                    detail="No se puede proyectar: hay solicitudes de aprobación pendientes"
                )

    estado_anterior_id = propuesta.estadoPropuesta_id
    propuesta.estadoPropuesta_id = estado_proyectada.id
    db.commit()
    db.refresh(propuesta)

    return {
        "msg": "Propuesta proyectada exitosamente",
        "idPropuesta": propuesta.id,
        "estadoAnterior": {
            "id": estado_anterior_id,
            "nombre": "CONCILIADA"
        },
        "estadoNuevo": {
            "id": propuesta.estadoPropuesta_id,
            "nombre": "PROYECTADA"
        }
    }
