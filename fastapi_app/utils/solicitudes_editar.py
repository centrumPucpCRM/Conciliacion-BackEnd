
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

	# Crear log de auditoría detallado
	log_data = {
		'idSolicitud': solicitud.id,
		'tipoSolicitud_id': getattr(solicitud, 'tipoSolicitud_id', None),
		'creadoEn': solicitud.creadoEn,
		'auditoria': {
			'idUsuarioReceptor': solicitud.idUsuarioReceptor,
			'idUsuarioGenerador': solicitud.idUsuarioGenerador,
			'idPropuesta': solicitud.idPropuesta,
			'comentario': solicitud.comentario,
			'abierta': solicitud.abierta,
			'valorSolicitud_id': solicitud.idValorSolicitud,
			'valorSolicitud': valor_solicitud_nombre,
			'idPropuesta': solicitud.idPropuesta,
			'abierta': solicitud.abierta,
			'valorSolicitud_id': solicitud.valorSolicitud_id,
			'idPrograma': solicitud.programa.idPrograma,
			'tipo_solicitud': solicitud.tipoSolicitud.nombre,
			'idPropuesta': solicitud.idPropuesta,
			'abierta': solicitud.abierta,
			'valorSolicitud_id': solicitud.valorSolicitud_id,
			'idOportunidad': solicitud.oportunidad.idOportunidad,
			'montoPropuesto': None,
			'montoObjetado': None,
		}
	}
	log = Log(**log_data)
	db.add(log)

	db.commit()
	return {"msg": "Solicitud actualizada correctamente", "idSolicitud": solicitud.id, "valorSolicitud": valor_solicitud_nombre}

def aceptar_rechazar_edicion_alumno(body, db):

	return {"msg": "Función aceptar_rechazar_edicion_alumno no implementada"}