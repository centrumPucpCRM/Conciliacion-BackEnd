
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

from fastapi_app.schemas import programa

def crear_solicitud_alumno(body, db):
	# Determinar tipo de solicitud antes de validar campos
	tipo_solicitud = body.get("tipo_solicitud")
	if not tipo_solicitud:
		raise HTTPException(status_code=400, detail="Falta campo obligatorio: tipo_solicitud")

	if tipo_solicitud == "EDICION_ALUMNO":
		required_fields = ["idOportunidad", "tipo_solicitud", "montoPropuesto"]
	elif tipo_solicitud == "AGREGAR_ALUMNO":
		required_fields = ["idOportunidad", "comentario", "tipo_solicitud"]

	for field in required_fields:
		if body.get(field) is None:
			raise HTTPException(status_code=400, detail=f"Falta campo obligatorio: {field}")

	id_oportunidad = body["idOportunidad"]
	comentario = body.get("comentario", "")

	# Buscar la oportunidad para obtener datos actuales
	oportunidad = db.query(Oportunidad).filter_by(id=id_oportunidad).first()
	if not oportunidad:
		raise HTTPException(status_code=400, detail="Oportunidad no encontrada")
	
	id_programa = oportunidad.idPrograma
	monto = oportunidad.monto

	# Obtener programa para idPropuesta y idUsuarioReceptor
	programa = db.query(Programa).filter_by(id=id_programa).first()
	if not programa:
		raise HTTPException(status_code=400, detail="Programa no encontrado")
	
	id_propuesta = programa.idPropuesta
	
	if (body.get("idUsuario") and tipo_solicitud == "EDICION_ALUMNO"):
		if str(body.get("idUsuario"))=="2" or str(body.get("idUsuario"))=="1":
			id_usuario_generador = "1"
			id_usuario_receptor = programa.idJefeProducto
		else :
			id_usuario_generador = body.get("idUsuario")
			id_usuario_receptor = "1"
	else:
		id_usuario_generador = programa.idJefeProducto
		id_usuario_receptor = "1" #El id del daf.supervisor
	
	# Si es EDICION_ALUMNO, armar comentario especial
	if tipo_solicitud == "EDICION_ALUMNO":
		# Buscar el nombre del usuario generador usando el id_usuario_generador
		usuario = db.query(Usuario).filter_by(id=id_usuario_generador).first()
		nombre_usuario = usuario.nombre if usuario and hasattr(usuario, "nombre") else str(id_usuario_generador)
		monto_propuesto = body.get("montoPropuesto")
		comentario = f"Por solicitud de {nombre_usuario} se cambia el monto {monto} a un monto propuesto de {monto_propuesto}"

	# Obtener tipoSolicitud_id
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
		idUsuarioReceptor=id_usuario_receptor,
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

	# Si es EDICION_ALUMNO, actualizar el montoPropuesto de la oportunidad
	if tipo_solicitud == "EDICION_ALUMNO":
		monto_propuesto = body.get("montoPropuesto")
		if monto_propuesto is not None:
			oportunidad.montoPropuesto = monto_propuesto
			db.commit()
	elif tipo_solicitud == "AGREGAR_ALUMNO":
		# Cambiar el estado en etapaVentaPropuesta a "3 Matriculado"
		oportunidad.etapaVentaPropuesta = "3 Matriculado"
		oportunidad.fechaMatriculaPropuesta = datetime.now().date()
		db.commit()

	# Crear log de auditoría
	log_data = {
		'idSolicitud': solicitud.id,
		'tipoSolicitud_id': solicitud.tipoSolicitud_id,
		'creadoEn': solicitud.creadoEn,
		'auditoria': {
			'idUsuarioReceptor': solicitud.idUsuarioReceptor,
			'idUsuarioGenerador': solicitud.idUsuarioGenerador,
			'idPropuesta': solicitud.idPropuesta,
			'comentario': solicitud.comentario,
			'abierta': solicitud.abierta,
			'valorSolicitud_id': solicitud.valorSolicitud_id,
			'idOportunidad': id_oportunidad,
			'montoPropuesto': sxos.montoPropuesto,
			'montoObjetado': sxos.montoObjetado,
			'tipo_solicitud': tipo_solicitud,
		}
	}
	log = Log(**log_data)
	db.add(log)
	db.commit()
	return {"msg": f"Solicitud {tipo_solicitud} creada", "id": solicitud.id}

def crear_solicitud_programa(body, db):
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
		idUsuarioReceptor=id_usuario_generador,  # El id del daf.supervisor
		idUsuarioGenerador="1",
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
	
	if tipo_solicitud == "EXCLUSION_PROGRAMA":
		programa.noAperturar = True
		programa.noCalcular = True
		db.commit()
	elif tipo_solicitud == "FECHA_CAMBIADA":
		pass	

	# Crear log de auditoría
	log_data = {
		'idSolicitud': solicitud.id,
		'tipoSolicitud_id': solicitud.tipoSolicitud_id,
		'creadoEn': solicitud.creadoEn,
		'auditoria': {
			'idUsuarioReceptor': solicitud.idUsuarioReceptor,
			'idUsuarioGenerador': solicitud.idUsuarioGenerador,
			'idPropuesta': solicitud.idPropuesta,
			'comentario': solicitud.comentario,
			'abierta': solicitud.abierta,
			'valorSolicitud_id': solicitud.valorSolicitud_id,
			'idPrograma': id_programa,
			'noAperturar': getattr(programa, 'noAperturar', None),
			'tipo_solicitud': tipo_solicitud,
		}
	}
	log = Log(**log_data)
	db.add(log)
	db.commit()
	return {"msg": f"Solicitud {tipo_solicitud} creada", "id": solicitud.id}

def crear_solicitud_fecha(body, db):
	"""
	Crea una solicitud de cambio de fecha para un programa.
	Similar a EDICION_ALUMNO pero trabaja con fechas en lugar de montos.
	"""
	# Validar campos obligatorios
	required_fields = ["idPrograma", "tipo_solicitud", "fechaInaguracionPropuesta"]
	for field in required_fields:
		if body.get(field) is None:
			raise HTTPException(status_code=400, detail=f"Falta campo obligatorio: {field}")

	id_programa = body["idPrograma"]
	fecha_propuesta = body.get("fechaInaguracionPropuesta")
	comentario_frontend = body.get("comentario", "")  # Comentario opcional del frontend

	# Obtener programa para idPropuesta y obtener fecha actual
	programa = db.query(Programa).filter_by(id=id_programa).first()
	if not programa:
		raise HTTPException(status_code=400, detail="Programa no encontrado")
	
	id_propuesta = programa.idPropuesta
	fecha_actual = programa.fechaDeInaguracion

	id_usuario_generador = programa.idJefeProducto
	id_usuario_receptor = "1"
	
	# Armar comentario automático
	usuario = db.query(Usuario).filter_by(id=id_usuario_generador).first()
	nombre_usuario = usuario.nombre if usuario and hasattr(usuario, "nombre") else str(id_usuario_generador)
	comentario_auto = f"Por solicitud de {nombre_usuario} se cambia la fecha de inauguración de {fecha_actual} a {fecha_propuesta}"
	
	# Si hay comentario del frontend, agregarlo al inicio separado por \n
	if comentario_frontend:
		comentario = f"{comentario_frontend}\n{comentario_auto}"
	else:
		comentario = comentario_auto

	# Obtener tipoSolicitud_id
	tipo_solicitud_obj = db.query(TipoSolicitud).filter_by(nombre="FECHA_CAMBIADA").first()
	if not tipo_solicitud_obj:
		raise HTTPException(status_code=400, detail="TipoSolicitud 'FECHA_CAMBIADA' no encontrado")
	tipo_solicitud_id = tipo_solicitud_obj.id

	# Obtener valorSolicitud_id para "PENDIENTE"
	valor_solicitud_obj = db.query(ValorSolicitud).filter_by(nombre="PENDIENTE").first()
	if not valor_solicitud_obj:
		raise HTTPException(status_code=400, detail="ValorSolicitud 'PENDIENTE' no encontrado")
	valor_solicitud_id = valor_solicitud_obj.id

	# Crear la solicitud
	solicitud = SolicitudModel(
		idUsuarioReceptor=id_usuario_receptor,
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

	# Crear la relación en solicitud_x_programa con la fecha propuesta
	sxps = SolicitudXPrograma(
		idSolicitud=solicitud.id,
		idPrograma=id_programa,
		fechaInaguracionPropuesta=fecha_propuesta,
		fechaInaguracionObjetada=None
	)
	db.add(sxps)
	db.commit()

	# Crear log de auditoría
	log_data = {
		'idSolicitud': solicitud.id,
		'tipoSolicitud_id': solicitud.tipoSolicitud_id,
		'creadoEn': solicitud.creadoEn,
		'auditoria': {
			'idUsuarioReceptor': solicitud.idUsuarioReceptor,
			'idUsuarioGenerador': solicitud.idUsuarioGenerador,
			'idPropuesta': solicitud.idPropuesta,
			'comentario': solicitud.comentario,
			'abierta': solicitud.abierta,
			'valorSolicitud_id': solicitud.valorSolicitud_id,
			'idPrograma': id_programa,
			'fechaInaguracionPropuesta': str(fecha_propuesta),
			'fechaInaguracionObjetada': None,
			'tipo_solicitud': "FECHA_CAMBIADA",
		}
	}
	log = Log(**log_data)
	db.add(log)
	db.commit()
	return {"msg": "Solicitud FECHA_CAMBIADA creada", "id": solicitud.id}
