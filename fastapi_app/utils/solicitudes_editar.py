
# from fastapi_app.models.solicitud import Solicitud as SolicitudModel
# from fastapi_app.models.programa import Programa
# from fastapi_app.models.oportunidad import Oportunidad

# from fastapi_app.models.solicitud_x_oportunidad import SolicitudXOportunidad
# from fastapi_app.models.solicitud_x_programa import SolicitudXPrograma
# from fastapi_app.models.solicitud import TipoSolicitud, ValorSolicitud

# from fastapi import  HTTPException

# def crear_solicitud_agregar_alumno(body, db):
# 	from datetime import datetime
# 	# Validar campos obligatorios
# 	required_fields = ["idOportunidad", "comentario","tipo_solicitud"]
# 	for field in required_fields:
# 		if body.get(field) is None:
# 			raise HTTPException(status_code=400, detail=f"Falta campo obligatorio: {field}")

# 	id_oportunidad = body["idOportunidad"]
# 	comentario = body["comentario"]

# 	# Buscar la oportunidad para obtener idPrograma
# 	oportunidad = db.query(Oportunidad).filter_by(id=id_oportunidad).first()
# 	if not oportunidad:
# 		raise HTTPException(status_code=400, detail="Oportunidad no encontrada")
# 	id_programa = oportunidad.idPrograma

# 	# Obtener programa para idPropuesta y idUsuarioReceptor
# 	programa = db.query(Programa).filter_by(id=id_programa).first()
# 	if not programa:
# 		raise HTTPException(status_code=400, detail="Programa no encontrado")
# 	id_propuesta = programa.idPropuesta
# 	id_usuario_generador = programa.idJefeProducto

# 	# Obtener tipoSolicitud_id
# 	tipo_solicitud = body.get("tipo_solicitud")
# 	tipo_solicitud_obj = db.query(TipoSolicitud).filter_by(nombre=tipo_solicitud).first()
# 	if not tipo_solicitud_obj:
# 		raise HTTPException(status_code=400, detail="TipoSolicitud no encontrado")
# 	tipo_solicitud_id = tipo_solicitud_obj.id

# 	# Obtener valorSolicitud_id para "PENDIENTE"
# 	valor_solicitud_obj = db.query(ValorSolicitud).filter_by(nombre="PENDIENTE").first()
# 	if not valor_solicitud_obj:
# 		raise HTTPException(status_code=400, detail="ValorSolicitud 'PENDIENTE' no encontrado")
# 	valor_solicitud_id = valor_solicitud_obj.id

# 	# Crear la solicitud
# 	solicitud = SolicitudModel(
# 		idUsuarioReceptor="2",#El id del daf.supervisor
# 		idUsuarioGenerador=id_usuario_generador,
# 		abierta=True,
# 		tipoSolicitud_id=tipo_solicitud_id,
# 		valorSolicitud_id=valor_solicitud_id,
# 		idPropuesta=id_propuesta,
# 		comentario=comentario,
# 		creadoEn=datetime.now()
# 	)
# 	db.add(solicitud)
# 	db.commit()
# 	db.refresh(solicitud)

# 	# Crear la relación en solicitud_x_oportunidad
# 	sxos = SolicitudXOportunidad(
# 		idSolicitud=solicitud.id,
# 		idOportunidad=id_oportunidad,
# 		montoPropuesto=body["montoPropuesto"] if "montoPropuesto" in body else None,
# 		montoObjetado=None
# 	)
# 	db.add(sxos)
# 	db.commit()
# 	return {"msg": f"Solicitud {tipo_solicitud} creada", "id": solicitud.id}

# def crear_solicitud_exclusion_programa(body, db):
# 	from datetime import datetime
# 	# Validar campos obligatorios
# 	required_fields = ["idPrograma", "comentario","tipo_solicitud"]
# 	for field in required_fields:
# 		if body.get(field) is None:
# 			raise HTTPException(status_code=400, detail=f"Falta campo obligatorio: {field}")

# 	id_programa = body["idPrograma"]
# 	comentario = body["comentario"]

# 	# Obtener programa para idPropuesta y idUsuarioGenerador
# 	programa = db.query(Programa).filter_by(id=id_programa).first()
# 	if not programa:
# 		raise HTTPException(status_code=400, detail="Programa no encontrado")
# 	id_propuesta = programa.idPropuesta
# 	id_usuario_generador = programa.idJefeProducto

# 	# Obtener tipoSolicitud_id
# 	tipo_solicitud = body.get("tipo_solicitud")
# 	tipo_solicitud_obj = db.query(TipoSolicitud).filter_by(nombre=tipo_solicitud).first()
# 	if not tipo_solicitud_obj:
# 		raise HTTPException(status_code=400, detail="TipoSolicitud no encontrado")
# 	tipo_solicitud_id = tipo_solicitud_obj.id

# 	# Obtener valorSolicitud_id para "PENDIENTE"
# 	valor_solicitud_obj = db.query(ValorSolicitud).filter_by(nombre="PENDIENTE").first()
# 	if not valor_solicitud_obj:
# 		raise HTTPException(status_code=400, detail="ValorSolicitud 'PENDIENTE' no encontrado")
# 	valor_solicitud_id = valor_solicitud_obj.id

# 	# Crear la solicitud
# 	solicitud = SolicitudModel(
# 		idUsuarioReceptor="2",  # El id del daf.supervisor
# 		idUsuarioGenerador=id_usuario_generador,
# 		abierta=True,
# 		tipoSolicitud_id=tipo_solicitud_id,
# 		valorSolicitud_id=valor_solicitud_id,
# 		idPropuesta=id_propuesta,
# 		comentario=comentario,
# 		creadoEn=datetime.now()
# 	)
# 	db.add(solicitud)
# 	db.commit()
# 	db.refresh(solicitud)

# 	# Crear la relación en solicitud_x_programa
# 	sxps = SolicitudXPrograma(
# 		idSolicitud=solicitud.id,
# 		idPrograma=id_programa
# 	)
# 	db.add(sxps)
# 	db.commit()
# 	return {"msg": f"Solicitud {tipo_solicitud} creada", "id": solicitud.id}
