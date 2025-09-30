

from fastapi import APIRouter, Depends

from fastapi_app.database import get_db
from fastapi_app.models.solicitud import Solicitud as SolicitudModel
from fastapi_app.models.oportunidad import Oportunidad

from fastapi_app.models.solicitud_x_oportunidad import SolicitudXOportunidad
from fastapi_app.models.solicitud_x_programa import SolicitudXPrograma
from fastapi_app.schemas.solicitud import Solicitud, SolicitudOportunidad, SolicitudPrograma

from fastapi import Body

from sqlalchemy.orm import Session
from typing import List

from ..utils.solicitudes_crear import crear_solicitud_alumno, crear_solicitud_programa
#from ..utils.solicitudes_editar import editar_solicitud_alumno,editar_solicitud_programa

router = APIRouter(prefix="/solicitudes", tags=["Solicitud"])
# Endpoint generico para crear solicitudes de alumno o programa
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
	tipo_solicitud = body.get("tipo_solicitud")
	if tipo_solicitud in ["AGREGAR_ALUMNO", "EDICION_ALUMNO", "ELIMINACION_BECADO","ELIMINACION_BECADO_REVERTIR"]:
		id_oportunidad = body.get("idOportunidad")
		oportunidad = db.query(Oportunidad).filter_by(id=id_oportunidad).first()
		if tipo_solicitud == "AGREGAR_ALUMNO":
			return crear_solicitud_alumno(body, db)
		elif tipo_solicitud == "EDICION_ALUMNO":
			return crear_solicitud_alumno(body, db)
		elif tipo_solicitud == "ELIMINACION_BECADO":
			oportunidad.eliminado = True
			db.commit()
			return {"msg": "Oportunidad marcada como eliminada", "idOportunidad": id_oportunidad}
		elif tipo_solicitud == "ELIMINACION_BECADO_REVERTIR":
			oportunidad.eliminado = False
			db.commit()
			return {"msg": "Oportunidad revertida a no eliminada", "idOportunidad": id_oportunidad}
		
	elif tipo_solicitud in ["EXCLUSION_PROGRAMA", "FECHA_CAMBIADA"]:
		if tipo_solicitud == "EXCLUSION_PROGRAMA":
			return crear_solicitud_programa(body, db)
		elif tipo_solicitud == "FECHA_CAMBIADA":
			#To do: Implementar cambio de fecha en programa
			pass
	return

@router.post("/editar")
def editar_solicitud_generica(
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
				"montoObjetado": 500,
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
	tipo_solicitud = body.get("tipo_solicitud")
	if tipo_solicitud in ["AGREGAR_ALUMNO", "EDICION_ALUMNO", "ELIMINACION_BECADO","ELIMINACION_BECADO_REVERTIR"]:
		id_oportunidad = body.get("idOportunidad")
		oportunidad = db.query(Oportunidad).filter_by(id=id_oportunidad).first()
		if tipo_solicitud == "AGREGAR_ALUMNO":
			return crear_solicitud_alumno(body, db)
		elif tipo_solicitud == "EDICION_ALUMNO":
			return crear_solicitud_alumno(body, db)
		elif tipo_solicitud == "ELIMINACION_BECADO":
			oportunidad.eliminado = True
			db.commit()
			return {"msg": "Oportunidad marcada como eliminada", "idOportunidad": id_oportunidad}
		elif tipo_solicitud == "ELIMINACION_BECADO_REVERTIR":
			oportunidad.eliminado = False
			db.commit()
			return {"msg": "Oportunidad revertida a no eliminada", "idOportunidad": id_oportunidad}
		
	elif tipo_solicitud in ["EXCLUSION_PROGRAMA", "FECHA_CAMBIADA"]:
		if tipo_solicitud == "EXCLUSION_PROGRAMA":
			return crear_solicitud_programa(body, db)
		elif tipo_solicitud == "FECHA_CAMBIADA":
			#To do: Implementar cambio de fecha en programa
			pass
	return
