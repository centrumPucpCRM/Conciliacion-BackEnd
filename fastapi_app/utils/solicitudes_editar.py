
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
	id_usuario_receptor = solicitud.idUsuarioReceptor
	# Lógica especial cuando se acepta una solicitud previamente rechazada
	if valor_solicitud_nombre == "ACEPTADO" and solicitud.valorSolicitud.nombre == "RECHAZADO":
		# Caso 1: EXCLUSION_PROGRAMA - DAF supervisor aprueba apertura del programa
		if solicitud.tipoSolicitud.nombre == "EXCLUSION_PROGRAMA" and id_usuario_receptor in [1, 2]:
			# Buscar la relación solicitud_x_programa
			sxp = db.query(SolicitudXPrograma).filter_by(idSolicitud=solicitud.id).first()
			if sxp:
				# Buscar el programa y cambiar noAperturar a False (se permite aperturar)
				programa = db.query(Programa).filter_by(id=sxp.idPrograma).first()
				if programa:
					programa.noAperturar = False
					programa.noCalcular = False
					db.add(programa)
					# Actualizar el comentario
					body["comentario"] = "\nEl programa se va a aperturar ya que DAF lo aprobó"
					
		# Caso 2: AGREGAR_ALUMNO - JP acepta el rechazo (marca como "No agregado")
		if solicitud.tipoSolicitud.nombre == "AGREGAR_ALUMNO" and id_usuario_receptor not in [1, 2]:
			# Buscar la relación solicitud_x_oportunidad
			sxo = db.query(SolicitudXOportunidad).filter_by(idSolicitud=solicitud.id).first()
			if sxo:
				# Buscar la oportunidad y cambiar etapaVentaPropuesta a "No agregado"
				oportunidad = db.query(Oportunidad).filter_by(id=sxo.idOportunidad).first()
				if oportunidad:
					oportunidad.etapaVentaPropuesta = "No agregado"
					db.add(oportunidad)
					body["comentario"] = "\nEl Alumno no fue agregado ya que DAF no lo autorizó y se aceptó esto"

	
	if valor_solicitud_nombre == "RECHAZADO":
		# Obtener información del usuario que rechaza
		usuario_rechaza = db.query(Usuario).filter_by(id=solicitud.idUsuarioReceptor).first()
		tipo_solicitud = solicitud.tipoSolicitud.nombre
		# Construir mensaje de rechazo
		comentario_rechazo = f"\nEl usuario {usuario_rechaza.nombre} rechazó la solicitud de tipo {tipo_solicitud}\n"
		# Intercambiar generador y receptor
		solicitud.idUsuarioGenerador, solicitud.idUsuarioReceptor = solicitud.idUsuarioReceptor, solicitud.idUsuarioGenerador
		
		# Agregar el comentario de rechazo
		comentario_base = body.get("comentario", "")
		body["comentario"] = comentario_base + comentario_rechazo
	#
	comentario = body.get("comentario")
	if comentario:
		solicitud.comentario = comentario
	solicitud.creadoEn = datetime.now()

	valor_solicitud_obj = db.query(ValorSolicitud).filter_by(nombre=valor_solicitud_nombre).first()
	solicitud.valorSolicitud = valor_solicitud_obj
	solicitud.valorSolicitud_id = valor_solicitud_obj.id

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
			'valorSolicitud': valor_solicitud_nombre,
			'idPropuesta': solicitud.idPropuesta,
			'abierta': solicitud.abierta,
			'tipo_solicitud': solicitud.tipoSolicitud.nombre,
			'idPropuesta': solicitud.idPropuesta,
			'abierta': solicitud.abierta,
			'valorSolicitud_id': solicitud.valorSolicitud_id,
			'montoPropuesto': None,
			'montoObjetado': None,
		}
	}
	log = Log(**log_data)
	db.add(log)

	db.commit()
	return {"msg": "Solicitud actualizada correctamente", "idSolicitud": solicitud.id, "valorSolicitud": valor_solicitud_nombre}

def aceptar_rechazar_edicion_alumno(body, db, solicitud):
	valor_solicitud_nombre = body.get("valorSolicitud")
	sxop = db.query(SolicitudXOportunidad).filter_by(idSolicitud=solicitud.id).first()
	if valor_solicitud_nombre == "RECHAZADO":
		solicitud.idUsuarioGenerador, solicitud.idUsuarioReceptor = solicitud.idUsuarioReceptor, solicitud.idUsuarioGenerador
		# Buscar la relación SolicitudXOportunidad
		if sxop.montoObjetado:
			sxop.montoPropuesto = sxop.montoObjetado
			sxop.montoObjetado = body.get("montoPropuesto")
		else:
			sxop.montoObjetado = body.get("montoPropuesto")
		# Actualizar el montoPropuesto en Oportunidad si corresponde
	oportunidad = db.query(Oportunidad).filter_by(id=sxop.idOportunidad).first()
	if sxop.montoObjetado:
		oportunidad.montoPropuesto = sxop.montoObjetado
	else:
		oportunidad.montoPropuesto = sxop.montoPropuesto
	comentario = body.get("comentario")
	usuario_generador = db.query(Usuario).filter_by(id=solicitud.idUsuarioGenerador).first()
	usuario_receptor = db.query(Usuario).filter_by(id=solicitud.idUsuarioReceptor).first()
	nombre_generador = usuario_generador.nombre if usuario_generador else "-"
	nombre_receptor = usuario_receptor.nombre if usuario_receptor else "-"
	if comentario:
		solicitud.comentario = (
			comentario
			+ f" \n Monto Propuesto por  {nombre_receptor} : " + str(sxop.montoPropuesto)
			+ f" \n Monto Objetado por  {nombre_generador} : " + str(sxop.montoObjetado)
		)
	solicitud.creadoEn = datetime.now()

	valor_solicitud_obj = db.query(ValorSolicitud).filter_by(nombre=valor_solicitud_nombre).first()
	solicitud.valorSolicitud = valor_solicitud_obj
	solicitud.valorSolicitud_id = valor_solicitud_obj.id


	# Obtener nombres de usuario generador y receptor
	usuario_generador = db.query(Usuario).filter_by(id=solicitud.idUsuarioGenerador).first()
	usuario_receptor = db.query(Usuario).filter_by(id=solicitud.idUsuarioReceptor).first()
	nombre_generador = usuario_generador.nombre if usuario_generador else None
	nombre_receptor = usuario_receptor.nombre if usuario_receptor else None

	log_data = {
		'idSolicitud': solicitud.id,
		'tipoSolicitud_id': getattr(solicitud, 'tipoSolicitud_id', None),
		'creadoEn': solicitud.creadoEn,
		'auditoria': {
			'idUsuarioReceptor': solicitud.idUsuarioReceptor,
			'nombreUsuarioReceptor': nombre_receptor,
			'idUsuarioGenerador': solicitud.idUsuarioGenerador,
			'nombreUsuarioGenerador': nombre_generador,
			'idPropuesta': solicitud.idPropuesta,
			'comentario': solicitud.comentario,
			'abierta': solicitud.abierta,
			'valorSolicitud': valor_solicitud_nombre,
			'idPropuesta': solicitud.idPropuesta,
			'abierta': solicitud.abierta,
			'valorSolicitud_id': solicitud.valorSolicitud_id,
			'tipo_solicitud': solicitud.tipoSolicitud.nombre,
			'idPropuesta': solicitud.idPropuesta,
			'abierta': solicitud.abierta,
			'montoPropuesto': sxop.montoPropuesto,
			'montoObjetado': sxop.montoObjetado,
		}
	}
	log = Log(**log_data)
	db.add(log)

	db.commit()
	return {"msg": "Solicitud actualizada correctamente", "idSolicitud": solicitud.id, "valorSolicitud": valor_solicitud_nombre}