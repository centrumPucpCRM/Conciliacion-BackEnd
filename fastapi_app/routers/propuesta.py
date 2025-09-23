
from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from fastapi_pagination import Page, paginate, Params
from fastapi_pagination.bases import AbstractPage
from fastapi_pagination.ext.sqlalchemy import paginate as sqlalchemy_paginate
from typing import Optional, List
from datetime import date
from ..database import get_db
from ..models.propuesta import Propuesta
from ..models.cartera import Cartera
from ..schemas.propuesta import Propuesta as PropuestaSchema

router = APIRouter(prefix="/propuesta", tags=["Propuesta"])


@router.post("/listar", response_model=Page[PropuestaSchema])
def listar_propuestas(
	body: dict = Body(..., example={
		"pagina": 1,
		"elementosPorPagina": 10,
		"fechaMinima": None,
		"fechaMaxima": None,
		"carteras": []
	}),
	db: Session = Depends(get_db)
):
	pagina = body.get("pagina", 1) - 1
	elementos_por_pagina = body.get("elementosPorPagina", 10)
	fecha_minima = body.get("fechaMinima")
	fecha_maxima = body.get("fechaMaxima")
	carteras = body.get("carteras") or []

	query = db.query(Propuesta)

	if fecha_minima:
		query = query.filter(Propuesta.creadoEn >= fecha_minima)
	if fecha_maxima:
		query = query.filter(Propuesta.creadoEn <= fecha_maxima)
	if carteras:
		query = query.join(Propuesta.carteras).filter(Cartera.nombre.in_(carteras))
	query = query.order_by(Propuesta.creadoEn.desc())

	# paginación manual (offset/limit)
	total = query.count()
	items = query.offset((pagina) * elementos_por_pagina).limit(elementos_por_pagina).all()
	return Page.create(items, total=total, params=Params(page=pagina, size=elementos_por_pagina))
    