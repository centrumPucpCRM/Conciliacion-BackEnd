from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.programa import Programa
from ..services.crm_service import obtener_fijos_fuera_counter, obtener_detalle_fijos_fuera_counter, obtener_alumnos_ultimo_momento, obtener_etapas_actuales_convertidos
from ..models.oportunidad import Oportunidad

router = APIRouter(prefix="/programa", tags=["Programa"])

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

    # 1. Actualizar FFC
    resultado = obtener_fijos_fuera_counter(programa.codigo)
    programa.fijoFueraDeCounter = resultado["count"]
    programa.montoFijoFueraDeCounter = resultado["monto"]

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

    # 3. Persistir alumnos de último momento (Matrícula / Cerrada-Ganada) nuevos en CRM
    party_numbers_existentes = {
        str(o.partyNumber).strip()
        for o in oportunidades_db
        if o.partyNumber
    }
    leads_ultimo_momento = obtener_alumnos_ultimo_momento(programa.codigo)
    nuevos_agregados = 0
    for lead in leads_ultimo_momento:
        party_crm = str(lead.get("partyNumber") or "").strip()
        if not party_crm or party_crm in party_numbers_existentes:
            continue
        descuento = lead.get("descuento")
        monto = float(lead.get("monto") or 0)
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
            becado=False,
            posibleAtipico=False,
            eliminado=False,
            retrocedioEnCRM=False,
            agregadoUltimoMomento=True,
        )
        db.add(nueva_opp)
        party_numbers_existentes.add(party_crm)
        nuevos_agregados += 1

    db.commit()
    db.refresh(programa)

    return {
        "idPrograma": programa_id,
        "fijoFueraDeCounter": resultado["count"],
        "montoFijoFueraDeCounter": resultado["monto"],
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

    leads = obtener_detalle_fijos_fuera_counter(programa.codigo)
    return {"leads": leads, "total": len(leads)}


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
    rows = db.query(Oportunidad.partyNumber).filter(
        Oportunidad.idPrograma == programa_id,
        Oportunidad.partyNumber.isnot(None),
    ).all()
    party_numbers_conciliados = {str(row[0]) for row in rows if row[0]}

    # Leads en etapas cerradas del CRM
    leads = obtener_alumnos_ultimo_momento(programa.codigo)

    # Filtrar los que no están conciliados
    ultimo_momento = [
        l for l in leads
        if l.get("partyNumber") not in party_numbers_conciliados
    ]
    return {"alumnos": ultimo_momento}

