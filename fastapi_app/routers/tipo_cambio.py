from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models.tipo_cambio import TipoCambio as TipoCambioModel
from ..schemas.tipo_cambio import TipoCambio, TipoCambioCreate
from typing import List

router = APIRouter(prefix="/tipo_cambio", tags=["TipoCambio"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=List[TipoCambio])
def read_tipo_cambios(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(TipoCambioModel).offset(skip).limit(limit).all()

@router.post("/", response_model=TipoCambio)
def create_tipo_cambio(tipo_cambio: TipoCambioCreate, db: Session = Depends(get_db)):
    db_tipo_cambio = TipoCambioModel(**tipo_cambio.dict())
    db.add(db_tipo_cambio)
    db.commit()
    db.refresh(db_tipo_cambio)
    return db_tipo_cambio

@router.get("/{tipo_cambio_id}", response_model=TipoCambio)
def get_tipo_cambio(tipo_cambio_id: int, db: Session = Depends(get_db)):
    tipo_cambio = db.query(TipoCambioModel).filter(TipoCambioModel.id_tipo_cambio == tipo_cambio_id).first()
    if not tipo_cambio:
        raise HTTPException(status_code=404, detail="TipoCambio not found")
    return tipo_cambio
