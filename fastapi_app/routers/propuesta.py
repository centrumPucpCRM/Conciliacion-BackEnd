from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from sqlalchemy.orm import load_only
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate as sqlalchemy_paginate
from typing import Optional, List
from datetime import date
from ..database import get_db
from ..models.propuesta import Propuesta
from ..models.cartera import Cartera
from ..schemas.propuesta import Propuesta as PropuestaSchema

router = APIRouter(prefix="/propuesta", tags=["Propuesta"])


@router.get("/listar", response_model=Page[PropuestaSchema])
def listar_propuestas(
    db: Session = Depends(get_db),
):
    # Listado directo desde la tabla propuesta, excluyendo la relación "carteras"
    query = db.query(Propuesta).options(
        load_only(Propuesta.id, Propuesta.nombre)
    )

    # Paginación automática provista por fastapi-pagination
    return sqlalchemy_paginate(db, query)
