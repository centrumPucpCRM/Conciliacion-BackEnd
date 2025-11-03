
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
import pytz


def obtener_fecha_peru():
	"""Obtiene la fecha actual en zona horaria peruana"""
	peru_tz = pytz.timezone('America/Lima')
	return datetime.now(peru_tz).replace(tzinfo=None)


def crear_log_estandarizado(db, solicitud, valor_solicitud_nombre, datos_especificos=None):
	"""
	Crea un log estandarizado con campos base comunes y datos específicos según el tipo de solicitud.
	Todos los logs tendrán la misma estructura y zona horaria peruana.
	
	Args:
		db: Sesión de base de datos
		solicitud: Objeto solicitud
		valor_solicitud_nombre: Nombre del valor de solicitud (ACEPTADO/RECHAZADO/PENDIENTE)
		datos_especificos: Dict con datos específicos del tipo de solicitud
	"""
	# Obtener fecha peruana
	fecha_peru = obtener_fecha_peru()
	
	# Obtener nombres de usuarios
	usuario_generador = db.query(Usuario).filter_by(id=solicitud.idUsuarioGenerador).first()
	usuario_receptor = db.query(Usuario).filter_by(id=solicitud.idUsuarioReceptor).first()
	
	# ✅ EXCEPCIÓN: Si la solicitud es ACEPTADA, intercambiar roles para mostrar quién realizó la acción
	if valor_solicitud_nombre == "ACEPTADO":
		# El receptor es quien acepta, así que se convierte en el "generador" del log
		id_generador_log = solicitud.idUsuarioReceptor
		nombre_generador_log = usuario_receptor.nombre if usuario_receptor else 'Usuario no encontrado'
		id_receptor_log = solicitud.idUsuarioGenerador
		nombre_receptor_log = usuario_generador.nombre if usuario_generador else 'Usuario no encontrado'
	else:
		# Para PENDIENTE y RECHAZADO, mantener roles originales
		id_generador_log = solicitud.idUsuarioGenerador
		nombre_generador_log = usuario_generador.nombre if usuario_generador else 'Usuario no encontrado'
		id_receptor_log = solicitud.idUsuarioReceptor
		nombre_receptor_log = usuario_receptor.nombre if usuario_receptor else 'Usuario no encontrado'
	
	# Estructura base común para TODOS los logs
	auditoria_base = {
		# ✅ INFORMACIÓN DE USUARIOS (con roles intercambiados si es ACEPTADO)
		'idUsuarioGenerador': id_generador_log,
		'nombreUsuarioGenerador': nombre_generador_log,
		'idUsuarioReceptor': id_receptor_log,
		'nombreUsuarioReceptor': nombre_receptor_log,
		
		# ✅ INFORMACIÓN DE LA SOLICITUD (siempre incluida)
		'tipoSolicitud': solicitud.tipoSolicitud.nombre if solicitud.tipoSolicitud else 'Tipo no definido',
		'valorSolicitud': valor_solicitud_nombre,
		'comentario': solicitud.comentario or '',
		'invertido': getattr(solicitud, 'invertido', False),
		
		# ✅ INFORMACIÓN DE CONTEXTO (siempre incluida)
		'idPropuesta': solicitud.idPropuesta,
		'abierta': solicitud.abierta,
	}
	
	# Agregar datos específicos si existen
	if datos_especificos:
		auditoria_base.update(datos_especificos)
	
	# Crear el log con fecha peruana
	log_data = {
		'idSolicitud': solicitud.id,
		'tipoSolicitud_id': solicitud.tipoSolicitud_id,
		'creadoEn': fecha_peru,
		'auditoria': auditoria_base
	}
	
	log = Log(**log_data)
	db.add(log)
	return log


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
						oportunidad.etapaVentaPropuesta = oportunidad.etapaDeVentas
						body["comentario"] = body.get("comentario", "") + "\nAlumno NO agregado (se aceptó el rechazo previo)"
					db.add(oportunidad)
	
	# CASO: RECHAZADO - Solo invertir flag e intercambiar roles
	elif valor_solicitud_nombre == "RECHAZADO":
		# Invertir el flag para la próxima iteración
		solicitud.invertido = not solicitud.invertido
		
		# Obtener información del usuario que rechaza
		usuario_rechaza = db.query(Usuario).filter_by(id=solicitud.idUsuarioReceptor).first()
		
		# Construir mensaje de rechazo
		comentario_rechazo = f"\nEl usuario {usuario_rechaza.nombre if usuario_rechaza else 'Usuario'} rechazó la solicitud de tipo {tipo_solicitud}\n"
		
		# Intercambiar generador y receptor para ping-pong
		solicitud.idUsuarioGenerador, solicitud.idUsuarioReceptor = solicitud.idUsuarioReceptor, solicitud.idUsuarioGenerador
		
		# Agregar el comentario de rechazo
		comentario_base = body.get("comentario", "")
		body["comentario"] = comentario_base + comentario_rechazo
	
	# Actualizar comentario y timestamp
	comentario = body.get("comentario")
	if comentario:
		solicitud.comentario = comentario
	solicitud.creadoEn = obtener_fecha_peru()

	valor_solicitud_obj = db.query(ValorSolicitud).filter_by(nombre=valor_solicitud_nombre).first()
	solicitud.valorSolicitud = valor_solicitud_obj
	solicitud.valorSolicitud_id = valor_solicitud_obj.id

	# Datos específicos para solicitudes básicas (EXCLUSION_PROGRAMA, AGREGAR_ALUMNO)
	datos_especificos = {}
	
	if tipo_solicitud == "EXCLUSION_PROGRAMA":
		sxp = db.query(SolicitudXPrograma).filter_by(idSolicitud=solicitud.id).first()
		if sxp:
			programa = db.query(Programa).filter_by(id=sxp.idPrograma).first()
			datos_especificos = {
				'idPrograma': sxp.idPrograma,
				'nombrePrograma': programa.nombre if programa else None,
				'noAperturar': programa.noAperturar if programa else None,
				'noCalcular': programa.noCalcular if programa else None,
			}
	
	elif tipo_solicitud == "AGREGAR_ALUMNO":
		sxo = db.query(SolicitudXOportunidad).filter_by(idSolicitud=solicitud.id).first()
		if sxo:
			oportunidad = db.query(Oportunidad).filter_by(id=sxo.idOportunidad).first()
			datos_especificos = {
				'idOportunidad': sxo.idOportunidad,
				'etapaVentaPropuesta': oportunidad.etapaVentaPropuesta if oportunidad else None,
			}
	
	# Crear log estandarizado
	crear_log_estandarizado(db, solicitud, valor_solicitud_nombre, datos_especificos)

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
	
	# Calcular y actualizar descuentoPropuesto basado en el precio de lista del programa
	if oportunidad and oportunidad.idPrograma:
		programa = db.query(Programa).filter_by(id=oportunidad.idPrograma).first()
		if programa and programa.precioDeLista and programa.precioDeLista > 0:
			# Calcular el porcentaje de descuento: (precio_lista - monto_propuesto) / precio_lista
			nuevo_descuento = (programa.precioDeLista - oportunidad.montoPropuesto) / programa.precioDeLista
			# Asegurar que el descuento esté entre 0 y 1
			nuevo_descuento = max(0, min(1, nuevo_descuento))
			oportunidad.descuentoPropuesto = nuevo_descuento
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
	solicitud.creadoEn = obtener_fecha_peru()

	valor_solicitud_obj = db.query(ValorSolicitud).filter_by(nombre=valor_solicitud_nombre).first()
	solicitud.valorSolicitud = valor_solicitud_obj
	solicitud.valorSolicitud_id = valor_solicitud_obj.id


	# Datos específicos para edición de alumno
	datos_especificos = {
		'idOportunidad': sxop.idOportunidad,
		'montoPropuesto': sxop.montoPropuesto,
		'montoObjetado': sxop.montoObjetado,
		'descuentoPropuesto': oportunidad.descuentoPropuesto if oportunidad else None,
	}
	
	# Crear log estandarizado
	crear_log_estandarizado(db, solicitud, valor_solicitud_nombre, datos_especificos)

	db.commit()
	return {"msg": "Solicitud actualizada correctamente", "idSolicitud": solicitud.id, "valorSolicitud": valor_solicitud_nombre}

def aceptar_rechazar_fecha_cambiada(body, db, solicitud):
	valor_solicitud_nombre = body.get("valorSolicitud")
	sxp = db.query(SolicitudXPrograma).filter_by(idSolicitud=solicitud.id).first()
	
	if valor_solicitud_nombre == "RECHAZADO":
		solicitud.idUsuarioGenerador, solicitud.idUsuarioReceptor = solicitud.idUsuarioReceptor, solicitud.idUsuarioGenerador
		# Buscar la relación SolicitudXPrograma
		if sxp.fechaInaguracionObjetada:
			sxp.fechaInaguracionPropuesta = sxp.fechaInaguracionObjetada
			sxp.fechaInaguracionObjetada = body.get("fechaInaguracionPropuesta")
		else:
			sxp.fechaInaguracionObjetada = body.get("fechaInaguracionPropuesta")
	
	# Actualizar la fechaInaguracionPropuesta en Programa si corresponde
	programa = db.query(Programa).filter_by(id=sxp.idPrograma).first()
	if sxp.fechaInaguracionObjetada:
		programa.fechaInaguracionPropuesta = sxp.fechaInaguracionObjetada
	else:
		programa.fechaInaguracionPropuesta = sxp.fechaInaguracionPropuesta
	
	comentario = body.get("comentario")
	usuario_generador = db.query(Usuario).filter_by(id=solicitud.idUsuarioGenerador).first()
	usuario_receptor = db.query(Usuario).filter_by(id=solicitud.idUsuarioReceptor).first()
	nombre_generador = usuario_generador.nombre if usuario_generador else "-"
	nombre_receptor = usuario_receptor.nombre if usuario_receptor else "-"
	
	if comentario:
		solicitud.comentario = (
			comentario
			+ f" \n Fecha Propuesta por  {nombre_receptor} : " + str(sxp.fechaInaguracionPropuesta)
			+ f" \n Fecha Objetada por  {nombre_generador} : " + str(sxp.fechaInaguracionObjetada)
		)
	
	solicitud.creadoEn = obtener_fecha_peru()

	valor_solicitud_obj = db.query(ValorSolicitud).filter_by(nombre=valor_solicitud_nombre).first()
	solicitud.valorSolicitud = valor_solicitud_obj
	solicitud.valorSolicitud_id = valor_solicitud_obj.id

	# Datos específicos para cambio de fecha
	programa = db.query(Programa).filter_by(id=sxp.idPrograma).first()
	datos_especificos = {
		'idPrograma': sxp.idPrograma,
		'nombrePrograma': programa.nombre if programa else None,
		'fechaInaguracionPropuesta': str(sxp.fechaInaguracionPropuesta) if sxp.fechaInaguracionPropuesta else None,
		'fechaInaguracionObjetada': str(sxp.fechaInaguracionObjetada) if sxp.fechaInaguracionObjetada else None,
	}
	
	# Crear log estandarizado
	crear_log_estandarizado(db, solicitud, valor_solicitud_nombre, datos_especificos)

	db.commit()
	return {"msg": "Solicitud actualizada correctamente", "idSolicitud": solicitud.id, "valorSolicitud": valor_solicitud_nombre}

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
		
		comentario_rechazo = f"\nEl usuario {nombre_usuario} rechazó la solicitud\n"
		
		# Intercambiar generador y receptor para ping-pong
		solicitud.idUsuarioGenerador, solicitud.idUsuarioReceptor = solicitud.idUsuarioReceptor, solicitud.idUsuarioGenerador
		
		comentario_base = body.get("comentario", "")
		solicitud.comentario = comentario_base + comentario_rechazo
		accion_realizada = "Solicitud rechazada - flag invertido"
	else:
		raise HTTPException(status_code=400, detail="valorSolicitud debe ser ACEPTADO o RECHAZADO")
	
	solicitud.creadoEn = obtener_fecha_peru()
	
	# Actualizar valor de solicitud
	valor_solicitud_obj = db.query(ValorSolicitud).filter_by(nombre=valor_solicitud_nombre).first()
	if not valor_solicitud_obj:
		raise HTTPException(status_code=400, detail=f"ValorSolicitud '{valor_solicitud_nombre}' no encontrado")
	
	solicitud.valorSolicitud_id = valor_solicitud_obj.id
	
	# Datos específicos para eliminación de posible becado
	datos_especificos = {
		'idOportunidad': sxo.idOportunidad,
		'oportunidadEliminada': oportunidad.eliminado if valor_solicitud_nombre == "ACEPTADO" else None,
		'accionRealizada': accion_realizada,
	}
	
	# Crear log estandarizado
	crear_log_estandarizado(db, solicitud, valor_solicitud_nombre, datos_especificos)
	
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

def generar_mensaje_amigable_log(log):
	"""
	Genera un mensaje amigable y comprensible para mostrar en la interfaz de usuario.
	Explica claramente qué pasó en cada paso de la solicitud.
	
	Args:
		log: Objeto Log con auditoria JSON
		
	Returns:
		dict: Información estructurada para la interfaz
	"""
	auditoria = log.auditoria
	tipo_solicitud = auditoria.get('tipoSolicitud')
	valor_solicitud = auditoria.get('valorSolicitud')
	invertido = auditoria.get('invertido', False)
	usuario_generador = auditoria.get('nombreUsuarioGenerador', 'Usuario')
	usuario_receptor = auditoria.get('nombreUsuarioReceptor', 'Usuario')
	
	# Estructura base
	resultado = {
		'id': log.id,
		'fecha': log.creadoEn.strftime('%d/%m/%Y %H:%M') if log.creadoEn else None,
		'tipoSolicitud': tipo_solicitud,
		'valorSolicitud': valor_solicitud,
		'invertido': invertido,
		'usuarioGenerador': usuario_generador,
		'usuarioReceptor': usuario_receptor,
		'comentario': auditoria.get('comentario', ''),
		'icono': '',
		'color': '',
		'titulo': '',
		'descripcion': '',
		'detalles': []
	}
	
	# Generar mensajes específicos según tipo de solicitud
	if valor_solicitud == "PENDIENTE":
		# Caso especial: creación de solicitud
		resultado.update({
			'icono': '📝',
			'color': 'blue',
			'titulo': f'{usuario_generador} CREÓ la solicitud',
			'descripcion': f'Se creó una nueva solicitud de tipo {tipo_solicitud.replace("_", " ")}',
			'detalles': [
				f'Tipo: {tipo_solicitud.replace("_", " ")}',
				f'Creado por: {usuario_generador}',
				f'Dirigido a: {usuario_receptor}',
				'Estado: Pendiente de revisión'
			]
		})
	elif tipo_solicitud == "EXCLUSION_PROGRAMA":
		programa = auditoria.get('nombrePrograma', 'Programa')
		no_aperturar = auditoria.get('noAperturar')
		
		if valor_solicitud == "ACEPTADO":
			if not invertido:
				resultado.update({
					'icono': '🚫',
					'color': 'red',
					'titulo': f'{usuario_generador} EXCLUYÓ el programa',
					'descripcion': f'Se aceptó la solicitud de exclusión del programa "{programa}"',
					'detalles': [
						f'Programa: {programa}',
						'Estado: Excluido (no se aperturará)',
						f'Decisión tomada por: {usuario_generador}'
					]
				})
			else:
				resultado.update({
					'icono': '✅',
					'color': 'green',
					'titulo': f'{usuario_generador} INCLUYÓ el programa',
					'descripcion': f'Se aceptó el rechazo previo, el programa "{programa}" se aperturará',
					'detalles': [
						f'Programa: {programa}',
						'Estado: Incluido (se aperturará)',
						f'Decisión tomada por: {usuario_generador}',
						'Nota: Se aceptó un rechazo previo'
					]
				})
		else:  # RECHAZADO
			resultado.update({
				'icono': '↩️',
				'color': 'orange',
				'titulo': f'{usuario_generador} RECHAZÓ la exclusión',
				'descripcion': f'Se rechazó la solicitud y se devolvió a {usuario_generador}',
				'detalles': [
					f'Programa: {programa}',
					f'Rechazado por: {usuario_receptor}',
					f'Devuelto a: {usuario_generador}',
					'La solicitud continúa en proceso (ping-pong)'
				]
			})
	
	elif tipo_solicitud == "AGREGAR_ALUMNO":
		etapa_venta = auditoria.get('etapaVentaPropuesta')
		
		if valor_solicitud == "ACEPTADO":
			if not invertido:
				resultado.update({
					'icono': '👤➕',
					'color': 'green',
					'titulo': f'{usuario_generador} AGREGÓ al alumno',
					'descripcion': 'Se aceptó la solicitud de agregar alumno',
					'detalles': [
						f'Etapa de venta: {etapa_venta}',
						f'Agregado por: {usuario_receptor}',
						'Estado: Alumno agregado exitosamente'
					]
				})
			else:
				resultado.update({
					'icono': '👤❌',
					'color': 'red',
					'titulo': f'{usuario_generador} NO AGREGÓ al alumno',
					'descripcion': 'Se aceptó el rechazo previo, el alumno no será agregado',
					'detalles': [
						f'Etapa de venta: {etapa_venta}',
						f'Decisión tomada por: {usuario_receptor}',
						'Estado: Alumno NO agregado',
						'Nota: Se aceptó un rechazo previo'
					]
				})
		else:  # RECHAZADO
			resultado.update({
				'icono': '↩️',
				'color': 'orange',
				'titulo': f'{usuario_generador} RECHAZÓ agregar alumno',
				'descripcion': f'Se rechazó la solicitud y se devolvió a {usuario_generador}',
				'detalles': [
					f'Rechazado por: {usuario_receptor}',
					f'Devuelto a: {usuario_generador}',
					'La solicitud continúa en proceso (ping-pong)'
				]
			})
	
	elif tipo_solicitud == "EDICION_ALUMNO":
		monto_propuesto = auditoria.get('montoPropuesto')
		monto_objetado = auditoria.get('montoObjetado')
		descuento = auditoria.get('descuentoPropuesto')
		
		if valor_solicitud == "ACEPTADO":
			resultado.update({
				'icono': '💰✅',
				'color': 'green',
				'titulo': f'{usuario_generador} ACEPTÓ el monto propuesto',
				'descripcion': 'Se aprobó la propuesta de monto',
				'detalles': [
					f'Monto final: S/ {monto_propuesto:,.2f}' if monto_propuesto else 'Monto no especificado',
					f'Descuento aplicado: {descuento*100:.1f}%' if descuento else 'Sin descuento',
					f'Aprobado por: {usuario_receptor}'
				]
			})
		else:  # RECHAZADO
			resultado.update({
				'icono': '💰↩️',
				'color': 'orange',
				'titulo': f'{usuario_generador} OBJETÓ el monto',
				'descripcion': 'Se propuso un monto diferente',
				'detalles': [
					f'Monto original: S/ {monto_propuesto:,.2f}' if monto_propuesto else 'No especificado',
					f'Monto objetado: S/ {monto_objetado:,.2f}' if monto_objetado else 'No especificado',
					f'Objetado por: {usuario_receptor}',
					f'Devuelto a: {usuario_generador}'
				]
			})
	
	elif tipo_solicitud == "FECHA_CAMBIADA":
		programa = auditoria.get('nombrePrograma', 'Programa')
		fecha_propuesta = auditoria.get('fechaInaguracionPropuesta')
		fecha_objetada = auditoria.get('fechaInaguracionObjetada')
		
		if valor_solicitud == "ACEPTADO":
			resultado.update({
				'icono': '📅✅',
				'color': 'green',
				'titulo': f'{usuario_generador} ACEPTÓ el cambio de fecha',
				'descripcion': f'Se aprobó la nueva fecha para "{programa}"',
				'detalles': [
					f'Programa: {programa}',
					f'Fecha aprobada: {fecha_propuesta}' if fecha_propuesta else 'Fecha no especificada',
					f'Aprobado por: {usuario_receptor}'
				]
			})
		else:  # RECHAZADO
			resultado.update({
				'icono': '📅↩️',
				'color': 'orange',
				'titulo': f'{usuario_generador} OBJETÓ la fecha',
				'descripcion': 'Se propuso una fecha diferente',
				'detalles': [
					f'Programa: {programa}',
					f'Fecha original: {fecha_propuesta}' if fecha_propuesta else 'No especificada',
					f'Fecha objetada: {fecha_objetada}' if fecha_objetada else 'No especificada',
					f'Objetado por: {usuario_receptor}',
					f'Devuelto a: {usuario_generador}'
				]
			})
	
	elif tipo_solicitud == "ELIMINACION_POSIBLE_BECADO":
		oportunidad_eliminada = auditoria.get('oportunidadEliminada')
		accion_realizada = auditoria.get('accionRealizada', '')
		
		if valor_solicitud == "ACEPTADO":
			if not invertido:
				resultado.update({
					'icono': '🎓❌',
					'color': 'red',
					'titulo': f'{usuario_generador} ELIMINÓ la beca',
					'descripcion': 'Se aceptó la solicitud de eliminación de beca',
					'detalles': [
						'Estado: Beca eliminada',
						f'Eliminado por: {usuario_receptor}',
						f'Acción: {accion_realizada}'
					]
				})
			else:
				resultado.update({
					'icono': '🎓✅',
					'color': 'green',
					'titulo': f'{usuario_generador} CONSERVÓ la beca',
					'descripcion': 'Se aceptó el rechazo previo, la beca se mantiene',
					'detalles': [
						'Estado: Beca conservada',
						f'Decisión tomada por: {usuario_receptor}',
						f'Acción: {accion_realizada}',
						'Nota: Se aceptó un rechazo previo'
					]
				})
		else:  # RECHAZADO
			resultado.update({
				'icono': '↩️',
				'color': 'orange',
				'titulo': f'{usuario_generador} RECHAZÓ eliminar beca',
				'descripcion': f'Se rechazó la eliminación y se devolvió a {usuario_generador}',
				'detalles': [
					f'Rechazado por: {usuario_receptor}',
					f'Devuelto a: {usuario_generador}',
					'La beca permanece sin cambios por ahora',
					'La solicitud continúa en proceso (ping-pong)'
				]
			})
	
	# Casos para otros tipos de solicitud
	else:
		resultado.update({
			'icono': '📋',
			'color': 'gray',
			'titulo': f'Solicitud {valor_solicitud.lower()}',
			'descripcion': f'Solicitud de tipo {tipo_solicitud}',
			'detalles': [
				f'Tipo: {tipo_solicitud}',
				f'Estado: {valor_solicitud}',
				f'Usuario: {usuario_receptor}'
			]
		})
	
	return resultado

def obtener_resumen_log_por_tipo(log):
	"""
	Función de compatibilidad que usa la nueva función de mensajes amigables.
	"""
	return generar_mensaje_amigable_log(log)
