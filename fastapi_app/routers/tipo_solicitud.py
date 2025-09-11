from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models.tipo_solicitud import TipoSolicitud as TipoSolicitudModel
from ..schemas.tipo_solicitud import TipoSolicitud, TipoSolicitudCreate
from typing import List

router = APIRouter(prefix="/tipo_solicitud", tags=["TipoSolicitud"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=List[TipoSolicitud])
def read_tipo_solicitudes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(TipoSolicitudModel).offset(skip).limit(limit).all()

@router.post("/", response_model=TipoSolicitud)
def create_tipo_solicitud(tipo_solicitud: TipoSolicitudCreate, db: Session = Depends(get_db)):
    db_tipo_solicitud = TipoSolicitudModel(**tipo_solicitud.dict())
    db.add(db_tipo_solicitud)
    db.commit()
    db.refresh(db_tipo_solicitud)
    return db_tipo_solicitud

@router.get("/{tipo_solicitud_id}", response_model=TipoSolicitud)
def get_tipo_solicitud(tipo_solicitud_id: int, db: Session = Depends(get_db)):
    tipo_solicitud = db.query(TipoSolicitudModel).filter(TipoSolicitudModel.id_tipo_solicitud == tipo_solicitud_id).first()
    if not tipo_solicitud:
        raise HTTPException(status_code=404, detail="TipoSolicitud not found")
    return tipo_solicitud
