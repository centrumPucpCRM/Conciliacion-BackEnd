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
    Consulta Oracle Sales Cloud y actualiza el conteo de 'Fijo fuera de counter'
    (leads con Rank=HOT y StatusCode=QUALIFIED) para un programa específico.
    """
    programa = db.query(Programa).filter(Programa.id == programa_id).first()
    if not programa:
        raise HTTPException(status_code=404, detail="Programa no encontrado")
    if not programa.codigo:
        raise HTTPException(status_code=400, detail="El programa no tiene código CRM")

    resultado = obtener_fijos_fuera_counter(programa.codigo)
    programa.fijoFueraDeCounter = resultado["count"]
    programa.montoFijoFueraDeCounter = resultado["monto"]

    # Detectar alumnos que retrocedieron de etapa en CRM y actualizar DB
    _ETAPAS_RETROCESO = {"1 - Interés", "2 - Calificación", "5 - Cerrada/Perdida"}
    etapas_crm = obtener_etapas_actuales_convertidos(programa.codigo)
    oportunidades_db = db.query(Oportunidad).filter(
        Oportunidad.idPrograma == programa_id,
        Oportunidad.eliminado == False,
        Oportunidad.partyNumber.isnot(None),
    ).all()
    retrocesos = 0
    for opp in oportunidades_db:
        party = str(opp.partyNumber).strip() if opp.partyNumber else None
        if not party:
            continue
        etapa_crm = etapas_crm.get(party)
        if etapa_crm and etapa_crm in _ETAPAS_RETROCESO and opp.etapaVentaPropuesta != etapa_crm:
            opp.etapaVentaPropuesta = etapa_crm
            retrocesos += 1

    db.commit()
    db.refresh(programa)

    return {
        "idPrograma": programa_id,
        "fijoFueraDeCounter": resultado["count"],
        "montoFijoFueraDeCounter": resultado["monto"],
        "retrocesos_actualizados": retrocesos,
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

