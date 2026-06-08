from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.programa import Programa
from ..services.crm_service import obtener_fijos_fuera_counter, obtener_detalle_fijos_fuera_counter, obtener_alumnos_ultimo_momento, obtener_etapas_actuales_convertidos
from ..models.oportunidad import Oportunidad
from ..models.proyeccion_excluido import ProyeccionExcluido

router = APIRouter(prefix="/programa", tags=["Programa"])


def _leadnumbers_excluidos(db: Session, programa_id: int) -> set:
    """Set de leadNumber excluidos manualmente de la proyección para un programa."""
    return {
        str(e.leadNumber).strip()
        for e in db.query(ProyeccionExcluido).filter(
            ProyeccionExcluido.idPrograma == programa_id
        ).all()
        if e.leadNumber
    }


def _ffc_filtrado(db: Session, programa) -> tuple:
    """
    Devuelve (leads, count, monto) de Fijo Fuera de Counter para un programa,
    quitando los leadNumber que fueron excluidos manualmente.
    """
    leads = obtener_detalle_fijos_fuera_counter(programa.codigo)
    excluidos = _leadnumbers_excluidos(db, programa.id)
    leads = [l for l in leads if str(l.get("leadNumber") or "").strip() not in excluidos]
    count = len(leads)
    monto = sum(float(l.get("monto") or 0) for l in leads)
    return leads, count, monto

@router.patch("/anexar-comentario")
def anexar_comentario_programa(
    body: dict = Body(..., example={"idPrograma": 1, "comentario": "Este es un comentario sobre el programa"}),
    db: Session = Depends(get_db)
):
    """
    Anexa o actualiza el comentario de un programa específico.
    Siempre retorna status 200 si el programa existe.
    """
    id_programa = body.get("idPrograma")
    comentario = body.get("comentario", "")
    
    if not id_programa:
        raise HTTPException(status_code=400, detail="El campo 'idPrograma' es obligatorio")
    
    # Buscar el programa
    programa = db.query(Programa).filter(Programa.id == id_programa).first()
    
    if not programa:
        raise HTTPException(status_code=404, detail="Programa no encontrado")
    
    # Actualizar el comentario
    programa.comentario = comentario
    db.commit()
    db.refresh(programa)
    
    return {
        "msg": "Comentario anexado exitosamente",
        "idPrograma": id_programa,
        "comentario": comentario
    }


@router.post("/{programa_id}/sync-fijo-fuera-counter")
def sync_fijo_fuera_counter(programa_id: int, db: Session = Depends(get_db)):
    """
    Consulta Oracle Sales Cloud y:
    1. Actualiza FFC (Fijo fuera de counter)
    2. Detecta retrocesos de etapa y marca retrocedioEnCRM
    3. Persiste alumnos nuevos (Matrícula / Cerrada-Ganada) como oportunidades con agregadoUltimoMomento=True
    """
    programa = db.query(Programa).filter(Programa.id == programa_id).first()
    if not programa:
        raise HTTPException(status_code=404, detail="Programa no encontrado")
    if not programa.codigo:
        raise HTTPException(status_code=400, detail="El programa no tiene código CRM")

    # Sincronizar = recalcular todo desde cero. Se limpian las exclusiones manuales
    # previas para que los leads que se habían quitado vuelvan a aparecer.
    db.query(ProyeccionExcluido).filter(
        ProyeccionExcluido.idPrograma == programa_id
    ).delete(synchronize_session=False)

    # 1. Actualizar FFC (ya sin exclusiones, recalculado completo)
    _, ffc_count, ffc_monto = _ffc_filtrado(db, programa)
    programa.fijoFueraDeCounter = ffc_count
    programa.montoFijoFueraDeCounter = ffc_monto

    # 2. Detectar retrocesos — marcar flag, NO cambiar etapa
    _ETAPAS_RETROCESO = {"1 - Interés", "2 - Calificación", "5 - Cerrada/Perdida"}
    by_party, by_dni = obtener_etapas_actuales_convertidos(programa.codigo)
    oportunidades_db = db.query(Oportunidad).filter(
        Oportunidad.idPrograma == programa_id,
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
        if opp.agregadoUltimoMomento and (opp.monto or 0) < 1 and not opp.becado:
            opp.becado = True

    # 3. Persistir alumnos de último momento (Matrícula / Cerrada-Ganada) nuevos en CRM
    # Mapas clave→registro para poder promover registros existentes no conciliados
    existentes_por_party = {
        str(o.partyNumber).strip(): o
        for o in oportunidades_db if o.partyNumber
    }
    existentes_por_opty = {
        str(o.optyNumber).strip(): o
        for o in oportunidades_db if o.optyNumber
    }
    existentes_por_dni = {
        str(o.documentoIdentidad).strip(): o
        for o in oportunidades_db if o.documentoIdentidad
    }
    leads_ultimo_momento = obtener_alumnos_ultimo_momento(programa.codigo)
    nuevos_agregados = 0
    for lead in leads_ultimo_momento:
        party_crm = str(lead.get("partyNumber") or "").strip()
        opty_crm = str(lead.get("leadNumber") or "").strip()
        dni_crm = str(lead.get("dni") or "").strip()

        if not party_crm and not opty_crm and not dni_crm:
            continue

        # Buscar si ya existe un registro en BD por cualquiera de las tres claves
        existente = (
            (party_crm and existentes_por_party.get(party_crm))
            or (opty_crm and existentes_por_opty.get(opty_crm))
            or (dni_crm and existentes_por_dni.get(dni_crm))
        )

        if existente:
            # Ya conciliado o ya en proyecciones → sin cambios
            if existente.conciliado or existente.agregadoUltimoMomento:
                continue
            # En BD pero sin conciliar ni proyectar → promover a último momento
            # (ocurre cuando el alumno llegó vía Excel antes de ser conciliado en CRM)
            existente.agregadoUltimoMomento = True
            nuevos_agregados += 1
            continue

        descuento = lead.get("descuento")
        monto = float(lead.get("monto") or 0)
        becado = monto < 1
        nueva_opp = Oportunidad(
            nombre=lead.get("nombre"),
            documentoIdentidad=lead.get("dni"),
            partyNumber=int(party_crm) if party_crm.isdigit() else None,
            optyNumber=lead.get("leadNumber"),
            monto=monto,
            montoPropuesto=monto,
            descuento=float(descuento) if descuento is not None else 0.0,
            descuentoPropuesto=float(descuento) if descuento is not None else 0.0,
            moneda=lead.get("moneda"),
            etapaDeVentas=lead.get("etapa"),
            etapaVentaPropuesta=lead.get("etapa"),
            vendedora=lead.get("vendedor"),
            idPrograma=programa_id,
            idPropuesta=programa.idPropuesta,
            conciliado=False,
            becado=becado,
            posibleAtipico=False,
            eliminado=False,
            retrocedioEnCRM=False,
            agregadoUltimoMomento=True,
        )
        db.add(nueva_opp)
        if party_crm:
            existentes_por_party[party_crm] = nueva_opp
        if opty_crm:
            existentes_por_opty[opty_crm] = nueva_opp
        if dni_crm:
            existentes_por_dni[dni_crm] = nueva_opp
        nuevos_agregados += 1

    db.commit()
    db.refresh(programa)

    agregados_ultimo = db.query(Oportunidad).filter(
        Oportunidad.idPrograma == programa_id,
        Oportunidad.agregadoUltimoMomento == True,
        Oportunidad.eliminado == False,
        Oportunidad.retrocedioEnCRM == False,
        Oportunidad.becado == False,
    ).all()
    agregados_count = len(agregados_ultimo)
    agregados_monto = sum(o.monto or 0 for o in agregados_ultimo)

    return {
        "idPrograma": programa_id,
        "fijoFueraDeCounter": ffc_count + agregados_count,
        "montoFijoFueraDeCounter": ffc_monto + agregados_monto,
        "retrocesos_actualizados": retrocesos,
        "nuevos_ultimo_momento": nuevos_agregados,
    }


@router.get("/{programa_id}/fijo-fuera-counter-leads")
def get_fijo_fuera_counter_leads(programa_id: int, db: Session = Depends(get_db)):
    """
    Retorna la lista de leads 'Fijo fuera de counter' para un programa,
    con los datos necesarios para mostrar en el modal detalle.
    """
    programa = db.query(Programa).filter(Programa.id == programa_id).first()
    if not programa:
        raise HTTPException(status_code=404, detail="Programa no encontrado")
    if not programa.codigo:
        raise HTTPException(status_code=400, detail="El programa no tiene código CRM")

    # FFC del CRM (ya filtrados de los excluidos manualmente). Son eliminables vía
    # exclusión por leadNumber (no tienen id en BD).
    leads_ffc, _, _ = _ffc_filtrado(db, programa)
    leads = [{**l, "eliminable": True} for l in leads_ffc]
    agregados_ultimo = db.query(Oportunidad).filter(
        Oportunidad.idPrograma == programa_id,
        Oportunidad.agregadoUltimoMomento == True,
        Oportunidad.eliminado == False,
        Oportunidad.retrocedioEnCRM == False,
        Oportunidad.becado == False,
    ).all()
    agregados_leads = [
        {
            "id": o.id,  # id real de la oportunidad en BD (las de CRM no lo tienen)
            "eliminable": True,  # solo las agregadas en último momento se pueden borrar de BD
            "leadNumber": o.optyNumber or str(o.id),
            "nombre": o.nombre,
            "dni": o.documentoIdentidad,
            "monto": float(o.monto or 0),
            "moneda": o.moneda,
            "estado": "AGREGADO_ULTIMO_MOMENTO",
            "etapa": o.etapaVentaPropuesta or o.etapaDeVentas,
            "descuento": o.descuento,
            "vendedor": o.vendedora,
        }
        for o in agregados_ultimo
    ]

    leads_combinados = leads + agregados_leads
    return {"leads": leads_combinados, "total": len(leads_combinados)}


@router.post("/{programa_id}/excluir-ffc")
def excluir_ffc(
    programa_id: int,
    body: dict = Body(..., example={"leadNumber": "L-12345"}),
    db: Session = Depends(get_db),
):
    """
    Excluye manualmente un lead de proyección (FFC / Interés / Admisión) de un programa.
    El lead viene del CRM en vivo (no es fila de BD), así que se guarda su leadNumber
    para filtrarlo del modal y del conteo de Fijo Fuera de Counter. Tras excluirlo se
    recalcula y persiste el FFC del programa.
    """
    lead_number = str(body.get("leadNumber") or "").strip()
    if not lead_number:
        raise HTTPException(status_code=400, detail="El campo 'leadNumber' es requerido")

    programa = db.query(Programa).filter(Programa.id == programa_id).first()
    if not programa:
        raise HTTPException(status_code=404, detail="Programa no encontrado")

    # Evitar duplicados
    existe = db.query(ProyeccionExcluido).filter(
        ProyeccionExcluido.idPrograma == programa_id,
        ProyeccionExcluido.leadNumber == lead_number,
    ).first()
    if not existe:
        db.add(ProyeccionExcluido(idPrograma=programa_id, leadNumber=lead_number))
        db.commit()

    # Recalcular y persistir FFC del programa descontando los excluidos
    if programa.codigo:
        _, ffc_count, ffc_monto = _ffc_filtrado(db, programa)
        programa.fijoFueraDeCounter = ffc_count
        programa.montoFijoFueraDeCounter = ffc_monto
        db.commit()

    return {"excluido": lead_number, "idPrograma": programa_id}


@router.get("/{programa_id}/alumnos-ultimo-momento")
def get_alumnos_ultimo_momento(programa_id: int, db: Session = Depends(get_db)):
    """
    Retorna alumnos que pasaron a etapas '3 - Matrícula' o '4 - Cerrada/Ganada'
    en CRM pero NO están en la lista de alumnos conciliados del programa.
    """
    programa = db.query(Programa).filter(Programa.id == programa_id).first()
    if not programa:
        raise HTTPException(status_code=404, detail="Programa no encontrado")
    if not programa.codigo:
        return {"alumnos": []}

    # Party numbers ya conciliados en BD
    rows = db.query(
        Oportunidad.partyNumber,
        Oportunidad.optyNumber,
        Oportunidad.documentoIdentidad,
    ).filter(
        Oportunidad.idPrograma == programa_id,
    ).all()
    party_numbers_conciliados = {str(row[0]).strip() for row in rows if row[0]}
    opty_numbers_conciliados = {str(row[1]).strip() for row in rows if row[1]}
    dni_conciliados = {str(row[2]).strip() for row in rows if row[2]}

    # Leads en etapas cerradas del CRM
    leads = obtener_alumnos_ultimo_momento(programa.codigo)

    # Filtrar los que no están conciliados
    ultimo_momento = []
    for l in leads:
        party = str(l.get("partyNumber") or "").strip()
        opty = str(l.get("leadNumber") or "").strip()
        dni = str(l.get("dni") or "").strip()
        if party and party in party_numbers_conciliados:
            continue
        if opty and opty in opty_numbers_conciliados:
            continue
        if dni and dni in dni_conciliados:
            continue
        ultimo_momento.append(l)
    return {"alumnos": ultimo_momento}

