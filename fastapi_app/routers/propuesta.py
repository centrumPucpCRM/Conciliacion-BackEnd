from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models.propuesta import Propuesta as PropuestaModel
from ..schemas.propuesta import Propuesta, PropuestaCreate, CambioEstadoPropuestaResponse
from typing import List
from ..models.propuesta_programa import PropuestaPrograma
from ..models.programa import Programa

router = APIRouter(prefix="/propuesta", tags=["Propuesta"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=List[Propuesta])
def read_propuestas(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    propuestas = db.query(PropuestaModel).offset(skip).limit(limit).all()
    result = []
    for p in propuestas:
        # Buscar todos los programas asociados a la propuesta
        programas = (
            db.query(Programa)
            .join(PropuestaPrograma, Programa.id_programa == PropuestaPrograma.id_programa)
            .filter(PropuestaPrograma.id_propuesta == p.id_propuesta)
            .all()
        )
        # Extraer carteras únicas
        carteras = list({prog.cartera for prog in programas if prog.cartera})
        # Usar el esquema y agregar carteras
        data = Propuesta.from_orm(p)
        data.carteras = carteras
        result.append(data)
    return result

@router.post("/", response_model=Propuesta)
def create_propuesta(propuesta: PropuestaCreate, db: Session = Depends(get_db)):
    db_propuesta = PropuestaModel(**propuesta.dict())
    db.add(db_propuesta)
    db.commit()
    db.refresh(db_propuesta)
    return db_propuesta

@router.get("/{propuesta_id}", response_model=Propuesta)
def get_propuesta(propuesta_id: int, db: Session = Depends(get_db)):
    propuesta = db.query(PropuestaModel).filter(PropuestaModel.id_propuesta == propuesta_id).first()
    if not propuesta:
        raise HTTPException(status_code=404, detail="Propuesta not found")
    return Propuesta.from_orm(propuesta)

@router.put("/{propuesta_id}/preconciliado", response_model=CambioEstadoPropuestaResponse)
def pasar_a_preconciliado(propuesta_id: int, db: Session = Depends(get_db)):
    """
    Cambia el estado de una propuesta a PRECONCILIADA
    """
    propuesta = db.query(PropuestaModel).filter(PropuestaModel.id_propuesta == propuesta_id).first()
    if not propuesta:
        raise HTTPException(status_code=404, detail="Propuesta not found")
    
    propuesta.estado_propuesta = "PRECONCILIADA"
    db.commit()
    db.refresh(propuesta)
    return CambioEstadoPropuestaResponse(
        id_propuesta=propuesta.id_propuesta,
        estado_propuesta=propuesta.estado_propuesta,
        mensaje="La propuesta ha sido marcada como preconciliada"
    )

@router.put("/{propuesta_id}/aprobacion", response_model=CambioEstadoPropuestaResponse)
def pasar_a_aprobacion(propuesta_id: int, db: Session = Depends(get_db)):
    """
    Cambia el estado de una propuesta a APROBACION
    """
    propuesta = db.query(PropuestaModel).filter(PropuestaModel.id_propuesta == propuesta_id).first()
    if not propuesta:
        raise HTTPException(status_code=404, detail="Propuesta not found")
    
    propuesta.estado_propuesta = "APROBACION"
    db.commit()
    db.refresh(propuesta)
    return CambioEstadoPropuestaResponse(
        id_propuesta=propuesta.id_propuesta,
        estado_propuesta=propuesta.estado_propuesta,
        mensaje="La propuesta ha sido enviada a aprobación"
    )

@router.put("/{propuesta_id}/conciliado", response_model=CambioEstadoPropuestaResponse)
def pasar_a_conciliado(propuesta_id: int, db: Session = Depends(get_db)):
    """
    Cambia el estado de una propuesta a CONCILIADA
    """
    propuesta = db.query(PropuestaModel).filter(PropuestaModel.id_propuesta == propuesta_id).first()
    if not propuesta:
        raise HTTPException(status_code=404, detail="Propuesta not found")
    
    propuesta.estado_propuesta = "CONCILIADA"
    db.commit()
    db.refresh(propuesta)
    return CambioEstadoPropuestaResponse(
        id_propuesta=propuesta.id_propuesta,
        estado_propuesta=propuesta.estado_propuesta,
        mensaje="La propuesta ha sido marcada como conciliada"
    )
