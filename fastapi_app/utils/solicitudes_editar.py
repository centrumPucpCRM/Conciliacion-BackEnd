
from fastapi_app.models.solicitud import Solicitud as SolicitudModel
from fastapi_app.models.programa import Programa
from fastapi_app.models.oportunidad import Oportunidad
from fastapi_app.models.usuario import Usuario
from fastapi_app.models.log import Log
from fastapi_app.models.solicitud_x_oportunidad import SolicitudXOportunidad
from fastapi_app.models.solicitud_x_programa import SolicitudXPrograma
from fastapi_app.models.solicitud import TipoSolicitud, ValorSolicitud
from datetime import datetime
from fastapi import  HTTPException


def aceptar_rechazar_solicitud_basico(body, db, solicitud):
	valor_solicitud_nombre = body.get("valorSolicitud")
	comentario = body.get("comentario")
	if valor_solicitud_nombre == "RECHAZADO":
		solicitud.idUsuarioGenerador, solicitud.idUsuarioReceptor = solicitud.idUsuarioReceptor, solicitud.idUsuarioGenerador
	valor_solicitud_obj = db.query(ValorSolicitud).filter_by(nombre=valor_solicitud_nombre).first()
	solicitud.idValorSolicitud = valor_solicitud_obj.id
	if comentario:
		solicitud.comentario = comentario
	solicitud.creadoEn = datetime.now()
	db.commit()
	return {"msg": "Solicitud actualizada correctamente", "idSolicitud": solicitud.id, "valorSolicitud": valor_solicitud_nombre}

def aceptar_rechazar_edicion_alumno(body, db):

	return {"msg": "Función aceptar_rechazar_edicion_alumno no implementada"}