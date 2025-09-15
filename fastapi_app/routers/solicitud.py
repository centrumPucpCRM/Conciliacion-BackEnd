

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..database import SessionLocal, get_db
from ..models.solicitud import Solicitud as SolicitudModel, VALOR_SOLICITUD_VALORES
from ..schemas.solicitud import (
    Solicitud, SolicitudCreate, SolicitudClienteCreate, SolicitudClienteResponse
)
from ..models.solicitud_propuesta_oportunidad import SolicitudPropuestaOportunidad as SolicitudPOModel
from typing import List, Optional
from pydantic import BaseModel
import datetime
from .solicitudes_daf import programa_router as daf_programa_router

router = APIRouter(prefix="/solicitud", tags=["Solicitud"])

@router.get("/", response_model=List[Solicitud])
def read_solicitudes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(SolicitudModel).offset(skip).limit(limit).all()

@router.post("/", response_model=Solicitud)
def create_solicitud(solicitud: SolicitudCreate, db: Session = Depends(get_db)):
    db_solicitud = SolicitudModel(**solicitud.dict())
    db.add(db_solicitud)
    db.commit()
    db.refresh(db_solicitud)
    return db_solicitud

@router.get("/{solicitud_id}", response_model=Solicitud)
def get_solicitud(solicitud_id: int, db: Session = Depends(get_db)):
    solicitud = db.query(SolicitudModel).filter(SolicitudModel.id_solicitud == solicitud_id).first()
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud not found")
    return solicitud



@router.get("/aprobacion_jp/usuario/{id_usuario_generador}", response_model=List[Solicitud])
def get_aprobacion_jp_by_usuario_generador(id_usuario_generador: int, db: Session = Depends(get_db)):
    """
    Listar todas las solicitudes de tipo APROBACION_JP donde el usuario es el generador.
    """
    solicitudes = db.query(SolicitudModel).filter(
        SolicitudModel.tipo_solicitud == "APROBACION_JP",
        SolicitudModel.id_usuario_generador == id_usuario_generador
    ).all()
    return solicitudes
@router.patch("/aprobacion_jp/usuario/{id_usuario_generador}/cerrar", response_model=List[Solicitud])
def cerrar_aprobacion_jp_by_usuario_generador(id_usuario_generador: int, db: Session = Depends(get_db)):
    """
    Cierra (abierta=0) todas las solicitudes de tipo APROBACION_JP donde el usuario es el generador.
    """
    solicitudes = db.query(SolicitudModel).filter(
        SolicitudModel.tipo_solicitud == "APROBACION_JP",
        SolicitudModel.id_usuario_generador == id_usuario_generador
    ).all()
    for solicitud in solicitudes:
        solicitud.abierta = False
    db.commit()
    return solicitudes