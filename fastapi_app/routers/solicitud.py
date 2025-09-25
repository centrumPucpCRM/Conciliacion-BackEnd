from fastapi import Query

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from fastapi_app.database import get_db
from fastapi_app.models.solicitud import Solicitud as SolicitudModel

from fastapi_app.models.solicitud_x_oportunidad import SolicitudXOportunidad
from fastapi_app.models.solicitud_x_programa import SolicitudXPrograma
from fastapi_app.schemas.solicitud import SolicitudOut, SolicitudOportunidad, SolicitudPrograma

router = APIRouter(prefix="/solicitudes", tags=["Solicitud"])

from typing import List

@router.get("/listar", response_model=List[SolicitudOut])
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
		resultado.append(SolicitudOut(
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
from fastapi import Response
from fastapi_app.schemas.solicitud import SolicitudOut

@router.get("/listar/solicitudes-de-usuario")
def listar_solicitudes_filtrado(
	id_usuario: int = Query(..., description="ID del usuario (generador o receptor)"),
	id_propuesta: int = Query(..., description="ID de la propuesta"),
	db: Session = Depends(get_db)
):

	# Si el usuario es 1, cambiar a 2
	if id_usuario == 1:
		id_usuario = 2

	tipos_oportunidad = {"AGREGAR_ALUMNO", "EDICION_ALUMNO", "ELIMINACION_BECADO"}
	tipo_programa = "EXCLUSION_PROGRAMA"

	solicitudes = db.query(SolicitudModel).filter(
		((SolicitudModel.idUsuarioGenerador == id_usuario) | (SolicitudModel.idUsuarioReceptor == id_usuario)),
		SolicitudModel.idPropuesta == id_propuesta
	).all()

	solicitudesPropuestaOportunidad = []
	solicitudesPropuestaPrograma = []
	solicitudesGenerales = []

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
		solicitud_dict = SolicitudOut(
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
		).dict()
		tipo = solicitud_dict["tipoSolicitud"]
		if tipo in tipos_oportunidad:
			solicitudesPropuestaOportunidad.append(solicitud_dict)
		elif tipo == tipo_programa:
			solicitudesPropuestaPrograma.append(solicitud_dict)
		else:
			solicitudesGenerales.append(solicitud_dict)

	return {
		"solicitudesPropuestaOportunidad": solicitudesPropuestaOportunidad,
		"solicitudesPropuestaPrograma": solicitudesPropuestaPrograma,
		"solicitudesGenerales": solicitudesGenerales
	}