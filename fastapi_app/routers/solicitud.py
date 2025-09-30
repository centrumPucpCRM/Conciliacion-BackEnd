from fastapi import Query

from fastapi import APIRouter, Depends

from fastapi_app.database import get_db
from fastapi_app.models.solicitud import Solicitud as SolicitudModel

from fastapi_app.models.solicitud_x_oportunidad import SolicitudXOportunidad
from fastapi_app.models.solicitud_x_programa import SolicitudXPrograma
from fastapi_app.schemas.solicitud import Solicitud, SolicitudOportunidad, SolicitudPrograma

from fastapi import Body, HTTPException

from sqlalchemy.orm import Session
from typing import List

router = APIRouter(prefix="/solicitudes", tags=["Solicitud"])
# Endpoint generico para crear solicitudes de alumno o programa
@router.post("/crear")
def crear_solicitud_generica(
	body: dict = Body(...),
	db: Session = Depends(get_db)
):
	tipo_solicitud = body.get("tipo_solicitud") #OBLIGATORIO
	if tipo_solicitud in ["AGREGAR_ALUMNO", "EDICION_ALUMNO", "ELIMINACION_BECADO"]:
		if tipo_solicitud == "AGREGAR_ALUMNO":
			#  idPropuesta (obtener del programa a que propuesta esta asociado)
			# "idPrograma", (OBLIGATORIO)
			# "idOportunidad", (OBLIGATORIO)
			# "idUsuarioGenerador" (OBLIGATORIO)
			# "tipoSolicitud_id", " (obtener el id de este "tipo_solicitud	")",
			# "valorSolicitud_id" (obtener el id de  "ABIERTA")
			# "idUsuarioReceptor (obtener del idPrograma)"
			# comentario (OBLIGATORIO)
			# abierta = True
			pass
		elif tipo_solicitud == "EDICION_ALUMNO":
			#  idPropuesta (obtener del programa a que propuesta esta asociado)
			# "idPrograma", (OBLIGATORIO)
			# "idOportunidad", (OBLIGATORIO)
			# "idUsuarioGenerador" (OBLIGATORIO)
			# "montoPropuesto", (OBLIGATORIO)
			# "montoObjetado", (OBLIGATORIO)
			# "tipoSolicitud_id", " (obtener el id de este "tipo_solicitud")",
			# "valorSolicitud_id" (obtener el id de  "ABIERTA")
			# "idUsuarioReceptor (obtener del idPrograma)"
			# comentario "El monto  propuesto fue editado por el usuario (obtener el nombre del usuario generador) de oporutnidad.monto, oportunidad..monto_propuesto"
			# abierta = True
			pass
		elif tipo_solicitud == "ELIMINACION_BECADO":
			#Por ahora esto no genera una solicitud
			pass
	elif tipo_solicitud in ["EXCLUSION_PROGRAMA", "FECHA_CAMBIADA"]:
		if tipo_solicitud == "EXCLUSION_PROGRAMA":
			pass
		elif tipo_solicitud == "FECHA_CAMBIADA":
	return {"message": "Funcionalidad no implementada aún"}



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

