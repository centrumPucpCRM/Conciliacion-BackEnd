
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
	"""
	Maneja aceptación/rechazo de solicitudes básicas con lógica de ping-pong invertida.
	
	Aplica a:
	- EXCLUSION_PROGRAMA: Control de apertura de programas
	- AGREGAR_ALUMNO: Control de agregación de alumnos
	
	Lógica ping-pong:
	- ACEPTADO con invertido=False: Comportamiento normal (excluir/no agregar)
	- ACEPTADO con invertido=True: Comportamiento invertido (incluir/agregar)
	- RECHAZADO: Invierte flag e intercambia roles (permite ping-pong)
	"""
	valor_solicitud_nombre = body.get("valorSolicitud")
	id_usuario_receptor = solicitud.idUsuarioReceptor
	tipo_solicitud = solicitud.tipoSolicitud.nombre
	
	# CASO: ACEPTADO - Aplicar lógica según flag invertido
	if valor_solicitud_nombre == "ACEPTADO":
		# Caso 1: EXCLUSION_PROGRAMA
		if tipo_solicitud == "EXCLUSION_PROGRAMA":
			sxp = db.query(SolicitudXPrograma).filter_by(idSolicitud=solicitud.id).first()
			if sxp:
				programa = db.query(Programa).filter_by(id=sxp.idPrograma).first()
				if programa:
					if not solicitud.invertido:
						# Comportamiento normal: ACEPTAR exclusión = NO aperturar
						programa.noAperturar = True
						programa.noCalcular = True
						body["comentario"] = body.get("comentario", "") + "\nPrograma excluido - no se aperturará"
					else:
						# Comportamiento invertido: ACEPTAR = SÍ aperturar (acepta rechazo de exclusión)
						programa.noAperturar = False
						programa.noCalcular = False
						body["comentario"] = body.get("comentario", "") + "\nPrograma incluido - se aperturará (se aceptó el rechazo de exclusión)"
					db.add(programa)
		
		# Caso 2: AGREGAR_ALUMNO
		elif tipo_solicitud == "AGREGAR_ALUMNO":
			sxo = db.query(SolicitudXOportunidad).filter_by(idSolicitud=solicitud.id).first()
			if sxo:
				oportunidad = db.query(Oportunidad).filter_by(id=sxo.idOportunidad).first()
				if oportunidad:
					if not solicitud.invertido:
						# Comportamiento normal: ACEPTAR = Agregar alumno
						oportunidad.etapaVentaPropuesta = "Agregado"
						body["comentario"] = body.get("comentario", "") + "\nAlumno agregado exitosamente"
					else:
						# Comportamiento invertido: ACEPTAR = NO agregar (acepta rechazo previo)
						oportunidad.etapaVentaPropuesta = "No agregado"
						body["comentario"] = body.get("comentario", "") + "\nAlumno NO agregado (se aceptó el rechazo previo)"
					db.add(oportunidad)
	
	# CASO: RECHAZADO - Solo invertir flag e intercambiar roles
	elif valor_solicitud_nombre == "RECHAZADO":
		# Invertir el flag para la próxima iteración
		solicitud.invertido = not solicitud.invertido
		
		# Obtener información del usuario que rechaza
		usuario_rechaza = db.query(Usuario).filter_by(id=solicitud.idUsuarioReceptor).first()
		
		# Construir mensaje de rechazo
		comentario_rechazo = f"\nEl usuario {usuario_rechaza.nombre if usuario_rechaza else 'Usuario'} rechazó la solicitud de tipo {tipo_solicitud} (lógica invertida: {solicitud.invertido})\n"
		
		# Intercambiar generador y receptor para ping-pong
		solicitud.idUsuarioGenerador, solicitud.idUsuarioReceptor = solicitud.idUsuarioReceptor, solicitud.idUsuarioGenerador
		
		# Agregar el comentario de rechazo
		comentario_base = body.get("comentario", "")
		body["comentario"] = comentario_base + comentario_rechazo
	
	# Actualizar comentario y timestamp
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
			'tipo_solicitud': solicitud.tipoSolicitud.nombre,
			'valorSolicitud_id': solicitud.valorSolicitud_id,
			'invertido': solicitud.invertido,
			'montoPropuesto': None,
			'montoObjetado': None,
		}
	}
	log = Log(**log_data)
	db.add(log)

	db.commit()
	return {
		"msg": "Solicitud actualizada correctamente",
		"idSolicitud": solicitud.id,
		"valorSolicitud": valor_solicitud_nombre,
		"invertido": solicitud.invertido
	}

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

def aceptar_rechazar_fecha_cambiada(body, db, solicitud):
	"""
	Acepta o rechaza una solicitud de tipo FECHA_CAMBIADA.
	
	Lógica:
	- ACEPTAR: Se acepta la fecha propuesta (fechaInaguracionPropuesta o fechaInaguracionObjetada si existe)
	  y se actualiza el programa con esa fecha.
	- RECHAZAR: Se intercambian roles, se propone una nueva fecha que pasa a ser fechaInaguracionObjetada
	  (o se intercambian las fechas si ya existe una objetada).
	"""
	valor_solicitud_nombre = body.get("valorSolicitud")
	
	# Buscar la relación SolicitudXPrograma
	sxp = db.query(SolicitudXPrograma).filter_by(idSolicitud=solicitud.id).first()
	if not sxp:
		raise HTTPException(status_code=400, detail="No se encontró la relación solicitud-programa")
	
	# Obtener el programa
	programa = db.query(Programa).filter_by(id=sxp.idPrograma).first()
	if not programa:
		raise HTTPException(status_code=400, detail="Programa no encontrado")
	
	# Si se RECHAZA, intercambiar generador y receptor y manejar fechas
	if valor_solicitud_nombre == "RECHAZADO":
		# Intercambiar roles
		solicitud.idUsuarioGenerador, solicitud.idUsuarioReceptor = solicitud.idUsuarioReceptor, solicitud.idUsuarioGenerador
		
		# Obtener la nueva fecha propuesta del body (obligatoria al rechazar)
		nueva_fecha_objetada = body.get("fechaInaguracionPropuesta")
		if not nueva_fecha_objetada:
			raise HTTPException(status_code=400, detail="Debe proporcionar una fecha al rechazar (fechaInaguracionPropuesta)")
		
		# Manejar intercambio de fechas
		if sxp.fechaInaguracionObjetada:
			# Ya había una fecha objetada, intercambiar
			sxp.fechaInaguracionPropuesta = sxp.fechaInaguracionObjetada
			sxp.fechaInaguracionObjetada = nueva_fecha_objetada
		else:
			# Primera vez que se rechaza, la fecha propuesta pasa a objetada
			sxp.fechaInaguracionObjetada = nueva_fecha_objetada
	
	# Si se ACEPTA, aplicar la fecha al programa
	elif valor_solicitud_nombre == "ACEPTADO":
		# Si hay fecha objetada, aceptamos esa (es la última propuesta)
		# Si no, aceptamos la fecha propuesta original
		fecha_a_aplicar = sxp.fechaInaguracionObjetada if sxp.fechaInaguracionObjetada else sxp.fechaInaguracionPropuesta
		
		if fecha_a_aplicar:
			programa.fechaInaguracionPropuesta = fecha_a_aplicar
	
	# Construir comentario
	comentario = body.get("comentario", "")
	usuario_generador = db.query(Usuario).filter_by(id=solicitud.idUsuarioGenerador).first()
	usuario_receptor = db.query(Usuario).filter_by(id=solicitud.idUsuarioReceptor).first()
	nombre_generador = usuario_generador.nombre if usuario_generador else "-"
	nombre_receptor = usuario_receptor.nombre if usuario_receptor else "-"
	
	if comentario:
		solicitud.comentario = (
			comentario
			+ f"\nFecha Propuesta por {nombre_receptor}: {sxp.fechaInaguracionPropuesta}"
		)
		if sxp.fechaInaguracionObjetada:
			solicitud.comentario += f"\nFecha Objetada por {nombre_generador}: {sxp.fechaInaguracionObjetada}"
	
	solicitud.creadoEn = datetime.now()
	
	# Actualizar valor de solicitud
	valor_solicitud_obj = db.query(ValorSolicitud).filter_by(nombre=valor_solicitud_nombre).first()
	if not valor_solicitud_obj:
		raise HTTPException(status_code=400, detail=f"ValorSolicitud '{valor_solicitud_nombre}' no encontrado")
	
	solicitud.valorSolicitud = valor_solicitud_obj
	solicitud.valorSolicitud_id = valor_solicitud_obj.id
	
	# Crear log de auditoría
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
			'valorSolicitud_id': solicitud.valorSolicitud_id,
			'tipo_solicitud': solicitud.tipoSolicitud.nombre,
			'idPrograma': sxp.idPrograma,
			'fechaInaguracionPropuesta': str(sxp.fechaInaguracionPropuesta) if sxp.fechaInaguracionPropuesta else None,
			'fechaInaguracionObjetada': str(sxp.fechaInaguracionObjetada) if sxp.fechaInaguracionObjetada else None,
			'fechaAplicadaAlPrograma': str(programa.fechaInaguracionPropuesta) if valor_solicitud_nombre == "ACEPTADO" else None,
		}
	}
	log = Log(**log_data)
	db.add(log)
	
	db.commit()
	return {
		"msg": "Solicitud de cambio de fecha actualizada correctamente",
		"idSolicitud": solicitud.id,
		"valorSolicitud": valor_solicitud_nombre,
		"idPrograma": programa.id,
		"fechaInaguracionPropuesta": str(sxp.fechaInaguracionPropuesta) if sxp.fechaInaguracionPropuesta else None,
		"fechaInaguracionObjetada": str(sxp.fechaInaguracionObjetada) if sxp.fechaInaguracionObjetada else None,
		"fechaAplicadaAlPrograma": str(programa.fechaInaguracionPropuesta) if valor_solicitud_nombre == "ACEPTADO" else None
	}

def aceptar_rechazar_ELIMINACION_POSIBLE_BECADO(body, db, solicitud):
	"""
	Maneja la aceptación/rechazo de solicitudes de tipo ELIMINACION_POSIBLE_BECADO con lógica invertida.
	
	Lógica:
	- ACEPTADO con invertido=False: Elimina al alumno (comportamiento normal)
	- ACEPTADO con invertido=True: NO elimina al alumno (comportamiento invertido - acepta el rechazo previo)
	- RECHAZADO: Solo invierte el flag e intercambia roles (NO toca al alumno, permite ping-pong)
	"""
	valor_solicitud_nombre = body.get("valorSolicitud")
	
	if not valor_solicitud_nombre:
		raise HTTPException(status_code=400, detail="Se requiere valorSolicitud (ACEPTADO o RECHAZADO)")
	
	# Buscar la relación solicitud_x_oportunidad
	sxo = db.query(SolicitudXOportunidad).filter_by(idSolicitud=solicitud.id).first()
	if not sxo:
		raise HTTPException(status_code=400, detail="No se encontró la relación con oportunidad")
	
	# Buscar la oportunidad
	oportunidad = db.query(Oportunidad).filter_by(id=sxo.idOportunidad).first()
	if not oportunidad:
		raise HTTPException(status_code=400, detail="Oportunidad no encontrada")
	
	# Obtener usuario que realiza la acción
	usuario_actual = db.query(Usuario).filter_by(id=solicitud.idUsuarioReceptor).first()
	nombre_usuario = usuario_actual.nombre if usuario_actual else "Usuario"
	
	accion_realizada = ""
	
	if valor_solicitud_nombre == "ACEPTADO":
		# Solo aquí se toma la decisión de eliminar o no según el flag invertido
		if not solicitud.invertido:
			# Comportamiento normal: ACEPTAR = ELIMINAR
			oportunidad.eliminado = True
			accion_realizada = f"Beca eliminada por {nombre_usuario}"
		else:
			# Comportamiento invertido: ACEPTAR = NO ELIMINAR (acepta el rechazo previo)
			oportunidad.eliminado = False
			accion_realizada = f"Beca NO eliminada - {nombre_usuario} aceptó el rechazo previo"
		
		comentario_aceptado = body.get("comentario", "")
		solicitud.comentario = f"{comentario_aceptado}\n{accion_realizada}"
			
	elif valor_solicitud_nombre == "RECHAZADO":
		# Solo invertir el flag e intercambiar roles, NO tocar al alumno
		solicitud.invertido = not solicitud.invertido
		
		comentario_rechazo = f"\nEl usuario {nombre_usuario} rechazó la solicitud (lógica invertida: {solicitud.invertido})\n"
		
		# Intercambiar generador y receptor para ping-pong
		solicitud.idUsuarioGenerador, solicitud.idUsuarioReceptor = solicitud.idUsuarioReceptor, solicitud.idUsuarioGenerador
		
		comentario_base = body.get("comentario", "")
		solicitud.comentario = comentario_base + comentario_rechazo
		accion_realizada = "Solicitud rechazada - flag invertido"
	else:
		raise HTTPException(status_code=400, detail="valorSolicitud debe ser ACEPTADO o RECHAZADO")
	
	solicitud.creadoEn = datetime.now()
	
	# Actualizar valor de solicitud
	valor_solicitud_obj = db.query(ValorSolicitud).filter_by(nombre=valor_solicitud_nombre).first()
	if not valor_solicitud_obj:
		raise HTTPException(status_code=400, detail=f"ValorSolicitud '{valor_solicitud_nombre}' no encontrado")
	
	solicitud.valorSolicitud_id = valor_solicitud_obj.id
	
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
			'valorSolicitud': valor_solicitud_nombre,
			'tipo_solicitud': 'ELIMINACION_POSIBLE_BECADO',
			'valorSolicitud_id': solicitud.valorSolicitud_id,
			'idOportunidad': sxo.idOportunidad,
			'invertido': solicitud.invertido,
			'oportunidad_eliminada': oportunidad.eliminado if valor_solicitud_nombre == "ACEPTADO" else None,
			'accion_realizada': accion_realizada,
		}
	}
	log = Log(**log_data)
	db.add(log)
	
	db.commit()
	return {
		"msg": f"Solicitud ELIMINACION_POSIBLE_BECADO {valor_solicitud_nombre.lower()}",
		"idSolicitud": solicitud.id,
		"valorSolicitud": valor_solicitud_nombre,
		"idOportunidad": sxo.idOportunidad,
		"invertido": solicitud.invertido,
		"oportunidadEliminada": oportunidad.eliminado if valor_solicitud_nombre == "ACEPTADO" else None,
		"accionRealizada": accion_realizada
	}
