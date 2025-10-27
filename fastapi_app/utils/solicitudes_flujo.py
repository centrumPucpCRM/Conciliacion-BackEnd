from fastapi_app.models.solicitud import Solicitud as SolicitudModel, ValorSolicitud
from fastapi_app.models.log import Log
from datetime import datetime
from fastapi import HTTPException


def aceptar_rechazar_solicitud_subdirectores(body, db, solicitud):
	"""
	Maneja solicitudes de subdirectores (APROBACION_JP y APROBACION_COMERCIAL).
	- Si es RECHAZADO: cambia abierta a True (para que vuelva a aparecer)
	- Si es ACEPTADO: cambia valorSolicitud a ACEPTADO
	"""
	valor_solicitud_nombre = body.get("valorSolicitud")
	
	if not valor_solicitud_nombre:
		raise HTTPException(status_code=400, detail="Se requiere valorSolicitud (ACEPTADO o RECHAZADO)")
	
	if valor_solicitud_nombre == "RECHAZADO":
		# Si es rechazado, cambiar abierta a True para que vuelva a aparecer
		solicitud.abierta = True
		comentario = body.get("comentario", "")
		if comentario:
			solicitud.comentario = comentario
	elif valor_solicitud_nombre == "ACEPTADO":
		# Si es aceptado, cambiar el estado a ACEPTADO
		valor_aceptado = db.query(ValorSolicitud).filter_by(nombre="ACEPTADO").first()
		if not valor_aceptado:
			raise HTTPException(status_code=400, detail="ValorSolicitud 'ACEPTADO' no encontrado")
		solicitud.valorSolicitud_id = valor_aceptado.id
		comentario = body.get("comentario", "")
		if comentario:
			solicitud.comentario = comentario
	else:
		raise HTTPException(status_code=400, detail="valorSolicitud debe ser ACEPTADO o RECHAZADO")
	
	solicitud.creadoEn = datetime.now()
	
	# Crear log de auditoría
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
			'valorSolicitud': valor_solicitud_nombre,
			'tipo_solicitud': solicitud.tipoSolicitud.nombre if solicitud.tipoSolicitud else None,
			'valorSolicitud_id': solicitud.valorSolicitud_id,
		}
	}
	log = Log(**log_data)
	db.add(log)
	
	db.commit()
	return {
		"msg": "Solicitud de subdirector actualizada correctamente",
		"idSolicitud": solicitud.id,
		"valorSolicitud": valor_solicitud_nombre,
		"abierta": solicitud.abierta
	}
