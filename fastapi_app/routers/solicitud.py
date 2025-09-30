
from datetime import datetime
from fastapi import Query

from fastapi import APIRouter, Depends

from fastapi_app.database import get_db
from fastapi_app.models.solicitud import Solicitud as SolicitudModel
from fastapi_app.models.programa import Programa
from fastapi_app.models.oportunidad import Oportunidad

from fastapi_app.models.solicitud_x_oportunidad import SolicitudXOportunidad
from fastapi_app.models.solicitud_x_programa import SolicitudXPrograma
from fastapi_app.schemas.solicitud import Solicitud, SolicitudOportunidad, SolicitudPrograma
from fastapi_app.models.solicitud import TipoSolicitud, ValorSolicitud

from fastapi import Body, HTTPException

from sqlalchemy.orm import Session
from typing import List

router = APIRouter(prefix="/solicitudes", tags=["Solicitud"])
# Endpoint generico para crear solicitudes de alumno o programa
@router.post("/crear")
def crear_solicitud_generica(
	body: dict = Body(
		...,
		example={
			"AGREGAR_ALUMNO":{
				"tipo_solicitud": "AGREGAR_ALUMNO",
				"idOportunidad": 10,
				"comentario": "Agregar de alumno por solicitud del usuario."
			},
			"EDICION_ALUMNO":{
				"tipo_solicitud": "EDICION_ALUMNO",
				"idOportunidad": 10,
				"montoPropuesto": 1000,
				"comentario": "Edición de alumno por solicitud del usuario."
			},
			"EXCLUSION_PROGRAMA":{
				"tipo_solicitud": "EXCLUSION_PROGRAMA",
				"idPrograma": 218,
				"comentario": "DAF solicita la exclusión del programa."
			}
		}
	),
	db: Session = Depends(get_db)
):
	tipo_solicitud = body.get("tipo_solicitud") #OBLIGATORIO
	if tipo_solicitud in ["AGREGAR_ALUMNO", "EDICION_ALUMNO", "ELIMINACION_BECADO"]:
		if tipo_solicitud == "AGREGAR_ALUMNO":
			return crear_solicitud_agregar_alumno(body, db)
		elif tipo_solicitud == "EDICION_ALUMNO":
			return crear_solicitud_agregar_alumno(body, db)
		elif tipo_solicitud == "ELIMINACION_BECADO":
			#Por ahora esto no genera una solicitud
			pass
	elif tipo_solicitud in ["EXCLUSION_PROGRAMA", "FECHA_CAMBIADA"]:
		if tipo_solicitud == "EXCLUSION_PROGRAMA":
			return crear_solicitud_exclusion_programa(body, db)
		elif tipo_solicitud == "FECHA_CAMBIADA":
			pass
	return



@router.get("/listar", response_model=List[Solicitud])
def listar_solicitudes(db: Session = Depends(get_db)):
	solicitudes = db.query(SolicitudModel).all()
	resultado = []
	for s in solicitudes:
		sxos = db.query(SolicitudXOportunidad).filter_by(idSolicitud=s.id).first()
		sxps = db.query(SolicitudXPrograma).filter_by(idSolicitud=s.id).first()
		oportunidad = None
		programa = None
		if sxos:
			oportunidad = SolicitudOportunidad(
				idOportunidad=sxos.idOportunidad,
				montoPropuesto=sxos.montoPropuesto,
				montoObjetado=sxos.montoObjetado
			)
		if sxps:
			programa = SolicitudPrograma(
				idPrograma=sxps.idPrograma,
				fechaInaguracionPropuesta=sxps.fechaInaguracionPropuesta,
				fechaInaguracionObjetada=sxps.fechaInaguracionObjetada
			)
		resultado.append(Solicitud(
			id=s.id,
			idUsuarioReceptor=s.idUsuarioReceptor,
			idUsuarioGenerador=s.idUsuarioGenerador,
			abierta=s.abierta,
			tipoSolicitud=s.tipoSolicitud.nombre if s.tipoSolicitud else None,
			valorSolicitud=s.valorSolicitud.nombre if s.valorSolicitud else None,
			idPropuesta=s.idPropuesta,
			comentario=s.comentario,
			creadoEn=s.creadoEn,
			oportunidad=oportunidad,
			programa=programa
		))
	return resultado


def crear_solicitud_agregar_alumno(body, db):
	from datetime import datetime
	# Validar campos obligatorios
	required_fields = ["idOportunidad", "comentario","tipo_solicitud"]
	for field in required_fields:
		if body.get(field) is None:
			raise HTTPException(status_code=400, detail=f"Falta campo obligatorio: {field}")

	id_oportunidad = body["idOportunidad"]
	comentario = body["comentario"]

	# Buscar la oportunidad para obtener idPrograma
	oportunidad = db.query(Oportunidad).filter_by(id=id_oportunidad).first()
	if not oportunidad:
		raise HTTPException(status_code=400, detail="Oportunidad no encontrada")
	id_programa = oportunidad.idPrograma

	# Obtener programa para idPropuesta y idUsuarioReceptor
	programa = db.query(Programa).filter_by(id=id_programa).first()
	if not programa:
		raise HTTPException(status_code=400, detail="Programa no encontrado")
	id_propuesta = programa.idPropuesta
	id_usuario_generador = programa.idJefeProducto

	# Obtener tipoSolicitud_id
	tipo_solicitud = body.get("tipo_solicitud")
	tipo_solicitud_obj = db.query(TipoSolicitud).filter_by(nombre=tipo_solicitud).first()
	if not tipo_solicitud_obj:
		raise HTTPException(status_code=400, detail="TipoSolicitud no encontrado")
	tipo_solicitud_id = tipo_solicitud_obj.id

	# Obtener valorSolicitud_id para "PENDIENTE"
	valor_solicitud_obj = db.query(ValorSolicitud).filter_by(nombre="PENDIENTE").first()
	if not valor_solicitud_obj:
		raise HTTPException(status_code=400, detail="ValorSolicitud 'PENDIENTE' no encontrado")
	valor_solicitud_id = valor_solicitud_obj.id

	# Crear la solicitud
	solicitud = SolicitudModel(
		idUsuarioReceptor="2",#El id del daf.supervisor
		idUsuarioGenerador=id_usuario_generador,
		abierta=True,
		tipoSolicitud_id=tipo_solicitud_id,
		valorSolicitud_id=valor_solicitud_id,
		idPropuesta=id_propuesta,
		comentario=comentario,
		creadoEn=datetime.now()
	)
	db.add(solicitud)
	db.commit()
	db.refresh(solicitud)

	# Crear la relación en solicitud_x_oportunidad
	sxos = SolicitudXOportunidad(
		idSolicitud=solicitud.id,
		idOportunidad=id_oportunidad,
		montoPropuesto=body["montoPropuesto"] if "montoPropuesto" in body else None,
		montoObjetado=None
	)
	db.add(sxos)
	db.commit()
	return {"msg": "Solicitud AGREGAR_ALUMNO creada", "id": solicitud.id}

def crear_solicitud_exclusion_programa(body, db):
	from datetime import datetime
	# Validar campos obligatorios
	required_fields = ["idPrograma", "comentario","tipo_solicitud"]
	for field in required_fields:
		if body.get(field) is None:
			raise HTTPException(status_code=400, detail=f"Falta campo obligatorio: {field}")

	id_programa = body["idPrograma"]
	comentario = body["comentario"]

	# Obtener programa para idPropuesta y idUsuarioGenerador
	programa = db.query(Programa).filter_by(id=id_programa).first()
	if not programa:
		raise HTTPException(status_code=400, detail="Programa no encontrado")
	id_propuesta = programa.idPropuesta
	id_usuario_generador = programa.idJefeProducto

	# Obtener tipoSolicitud_id
	tipo_solicitud = body.get("tipo_solicitud")
	tipo_solicitud_obj = db.query(TipoSolicitud).filter_by(nombre=tipo_solicitud).first()
	if not tipo_solicitud_obj:
		raise HTTPException(status_code=400, detail="TipoSolicitud no encontrado")
	tipo_solicitud_id = tipo_solicitud_obj.id

	# Obtener valorSolicitud_id para "PENDIENTE"
	valor_solicitud_obj = db.query(ValorSolicitud).filter_by(nombre="PENDIENTE").first()
	if not valor_solicitud_obj:
		raise HTTPException(status_code=400, detail="ValorSolicitud 'PENDIENTE' no encontrado")
	valor_solicitud_id = valor_solicitud_obj.id

	# Crear la solicitud
	solicitud = SolicitudModel(
		idUsuarioReceptor="2",  # El id del daf.supervisor
		idUsuarioGenerador=id_usuario_generador,
		abierta=True,
		tipoSolicitud_id=tipo_solicitud_id,
		valorSolicitud_id=valor_solicitud_id,
		idPropuesta=id_propuesta,
		comentario=comentario,
		creadoEn=datetime.now()
	)
	db.add(solicitud)
	db.commit()
	db.refresh(solicitud)

	# Crear la relación en solicitud_x_programa
	sxps = SolicitudXPrograma(
		idSolicitud=solicitud.id,
		idPrograma=id_programa
	)
	db.add(sxps)
	db.commit()
	return {"msg": "Solicitud EXCLUSION_PROGRAMA creada", "id": solicitud.id}
