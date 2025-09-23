# import pandas as pd
# import datetime
# from typing import Dict, List, Any, Optional
# from sqlalchemy.orm import Session
# from fastapi import HTTPException

# from ..models.usuario import Usuario
# from ..models.cartera import Cartera
# from ..models.programa import Programa
# from ..models.oportunidad import Oportunidad
# from ..models.propuesta import Propuesta
# from ..models.tipo_cambio import TipoCambio
# from ..models.propuesta_oportunidad import PropuestaOportunidad
# from ..models.propuesta_programa import PropuestaPrograma
# from ..models.solicitud import Solicitud

# async def process_csv_data(db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
#     """
#     Procesa datos CSV de conciliación ya convertidos a formato JSON y crea los registros
#     correspondientes en la base de datos."""

#     try:
#         # ...existing code...
#         print(data)
#         detalle = data.get("detalle") if isinstance(data, dict) else None
#         df = None
#         if detalle:
#             df = pd.DataFrame(detalle)
#         else:
#             csv_url = data.get("csv_url") if isinstance(data, dict) else None
#             if not csv_url:
#                 raise HTTPException(status_code=400, detail="No se proporcion� ni 'detalle' ni 'csv_url' para procesar el archivo de conciliaci�n")
#             try:
#                 df = pd.read_csv(csv_url)
#             except Exception as csv_error:
#                 raise HTTPException(status_code=400, detail=f"No se pudo leer el CSV desde la URL proporcionada: {csv_error}")

#         if df is None or df.empty:
#             raise HTTPException(status_code=400, detail="El archivo CSV no contiene registros para procesar")

#         df = df.copy()
#         # ...existing code...
#         df.columns = df.columns.str.strip()
#         # ...existing code...
#         propuesta_info = data.get("propuesta") if isinstance(data, dict) else {}
#         selected_carteras = []
#         if isinstance(propuesta_info, dict):
#             raw_carteras = propuesta_info.get("carteras")
#             if isinstance(raw_carteras, list) and raw_carteras:
#                 selected_carteras = [str(cartera).strip() for cartera in raw_carteras if cartera is not None]

#         if selected_carteras and 'cartera.nombre' in df.columns:
#             df['cartera.nombre'] = df['cartera.nombre'].apply(lambda value: str(value).strip() if pd.notna(value) else value)
#             df = df[df['cartera.nombre'].isin(selected_carteras)]
#             if df.empty:
#                 raise HTTPException(status_code=400, detail="No se encontraron registros para las carteras seleccionadas en el CSV")
#         # ...existing code...
#         columns_mapping = {
#             'usuario.nombre': 'usuario.nombre',
#             'cartera.nombre': 'cartera.nombre',
#             'programa.codigo': 'programa.codigo',
#             'programa.nombre': 'programa.nombre',
#             'programa.fecha_de_inicio': 'programa.fecha_de_inicio',
#             'programa.fecha_de_inauguracion': 'programa.fecha_de_inauguracion',
#             'programa.fecha_ultima_postulante': 'programa.fecha_ultima_postulante',
#             'programa.moneda': 'programa.moneda',
#             'programa.precio_lista': 'programa.precio_lista',
#             'programa.meta_alumnos': 'programa.meta_alumnos',
#             'programa.meta_venta': 'programa.meta_venta',
#             'programa.punto_minimo_apertura': 'programa.punto_minimo_apertura',
#             'programa.subdireccion':'programa.subdireccion',
#             'oportunidad.nombre': 'oportunidad.nombre',
#             'oportunidad.documento_identidad': 'oportunidad.documento_identidad',
#             'oportunidad.correo': 'oportunidad.correo',
#             'oportunidad.telefono': 'oportunidad.telefono',
#             'oportunidad.etapa_venta': 'oportunidad.etapa_venta',
#             'oportunidad.descuento': 'oportunidad.descuento',
#             'oportunidad.moneda': 'oportunidad.moneda',
#             'oportunidad.monto': 'oportunidad.monto',
#             'oportunidad.party_number': 'oportunidad.party_number',
#             'oportunidad.conciliado': 'oportunidad.conciliado',
#         }
#         df = df.rename(columns={col: columns_mapping.get(col, col) for col in df.columns})
#         date_columns = [
#             'programa.fecha_de_inicio',
#             'programa.fecha_de_inauguracion',
#             'programa.fecha_ultima_postulante'
#         ]
#         import re
#         for col in date_columns:
#             if col in df.columns:
#                 df[col] = df[col].astype(str).str.strip().replace({r'[./]': '-', r'\s+': ' '}, regex=True)
#                 df[col] = df[col].replace({'nan': '', 'NaT': '', 'None': '', '': None})
#                 def robust_parse(val):
#                     if not val or val.lower() in ['nan', 'nat', 'none', '']:
#                         return pd.NaT
#                     try:
#                         return pd.to_datetime(val, errors='coerce', yearfirst=True, dayfirst=False)
#                     except Exception:
#                         pass
#                     try:
#                         from dateutil import parser
#                         return parser.parse(val, yearfirst=True, dayfirst=False)
#                     except Exception:
#                         return pd.NaT
#                 df[col] = df[col].apply(robust_parse)
#         # ...existing code...
#         now = datetime.datetime.now()
#         propuesta_info = data.get("propuesta") if isinstance(data, dict) else {}
#         # Cambia aquí: usa el nombre que viene del frontend si existe
#         propuesta_nombre = propuesta_info.get("nombre") or f"Propuesta_{now.strftime('%Y%m%d_%H%M%S')}"
#         propuesta_unica = Propuesta(
#             nombre=propuesta_nombre,
#             descripcion="Propuesta generada automáticamente desde archivo CSV",
#             tipo_propuesta="CREACION",  
#             estado_propuesta="GENERADA",
#             creado_en=now
#         )
#         db.add(propuesta_unica)
#         db.flush()
#         # ...existing code...
#         # Ya no se elimina ningún usuario ni usuario_cartera. Solo actualizar si existe, crear si no.
#         carteras_dict = {}
#         if 'cartera.nombre' in df.columns:
#             for cartera_nombre in df['cartera.nombre'].dropna().unique():
#                 cartera_nombre = cartera_nombre.strip()
#                 cartera = db.query(Cartera).filter(Cartera.nombre == cartera_nombre).first()
#                 if not cartera:
#                     cartera = Cartera(nombre=cartera_nombre)
#                     db.add(cartera)
#                     db.flush()
#                 carteras_dict[cartera_nombre] = cartera
#         from ..models.rol_permiso import Rol
#         rol = db.query(Rol).filter(Rol.id_rol == 1).first()
#         if not rol:
#             rol = db.query(Rol).filter(Rol.nombre == "Administrador").first()
#         if not rol:
#             raise HTTPException(status_code=404, detail="No se encontró un rol adecuado para los usuarios")
#         usuarios_dict = {}
#         usuario_carteras_map = {}
#         for _, row in df.iterrows():
#             if pd.notna(row.get('usuario.nombre')) and pd.notna(row.get('cartera.nombre')):
#                 usuario_nombre = row['usuario.nombre'].strip()
#                 cartera_nombre = row['cartera.nombre'].strip()
#                 if usuario_nombre not in usuario_carteras_map:
#                     usuario_carteras_map[usuario_nombre] = set()
#                 usuario_carteras_map[usuario_nombre].add(cartera_nombre)
#         for usuario_nombre, cartera_nombres in usuario_carteras_map.items():
#             usuario = db.query(Usuario).filter(Usuario.nombres == usuario_nombre).first()
#             if not usuario:
#                 usuario = Usuario(
#                     nombres=usuario_nombre,
#                     dni=f"USR{len(usuarios_dict) + 1}",
#                     correo=f"{usuario_nombre.lower().replace(' ', '.')}@ejemplo.com",
#                     celular="999999999",
#                     id_rol=rol.id_rol
#                 )
#                 db.add(usuario)
#                 db.flush()
#             usuarios_dict[usuario_nombre] = usuario
#             for cartera_nombre in cartera_nombres:
#                 cartera = carteras_dict.get(cartera_nombre)
#                 if cartera and cartera not in usuario.carteras:
#                     usuario.carteras.append(cartera)
#         # ...existing code...
#         programas_dict = {}
#         if 'programa.codigo' in df.columns:
#             def parse_float(val):
#                 if pd.isna(val):
#                     return 0.0
#                 if isinstance(val, float) or isinstance(val, int):
#                     return float(val)
#                 if isinstance(val, str):
#                     return float(val.replace(',', '.'))
#                 return 0.0
#             for _, row in df.iterrows():
#                 if pd.notna(row.get('programa.codigo')):
#                     programa_codigo = str(row['programa.codigo']).strip()
#                     if programa_codigo not in programas_dict:
#                         usuario_nombre = str(row.get('usuario.nombre', '')).strip() if pd.notna(row.get('usuario.nombre')) else ''
#                         usuario_jp = usuarios_dict.get(usuario_nombre)
#                         id_jefe_producto = usuario_jp.id_usuario if usuario_jp else 1
#                         programa_data = {
#                             'codigo': programa_codigo,
#                             'nombre': str(row.get('programa.nombre', 'Programa')).strip() if pd.notna(row.get('programa.nombre')) else f"Programa {programa_codigo}",
#                             'moneda': str(row.get('programa.moneda', 'PEN')).strip() if pd.notna(row.get('programa.moneda')) else 'PEN',
#                             'precio_lista': parse_float(row.get('programa.precio_lista', 0)) if pd.notna(row.get('programa.precio_lista')) else 0,
#                             'id_propuesta': propuesta_unica.id_propuesta,
#                             'id_jefe_producto': id_jefe_producto
#                         }
#                         programa_data['cartera'] = str(row.get('cartera.nombre')).strip()
#                         programa_data['fecha_de_inicio'] = row.get('programa.fecha_de_inicio').date() if pd.notna(row.get('programa.fecha_de_inicio')) else None
#                         programa_data['fecha_de_inauguracion'] = row.get('programa.fecha_de_inauguracion').date() if pd.notna(row.get('programa.fecha_de_inauguracion')) else None
#                         programa_data['fecha_ultima_postulante'] = row.get('programa.fecha_ultima_postulante').date() if pd.notna(row.get('programa.fecha_ultima_postulante')) else None
#                         programa_data['meta_venta'] = parse_float(row.get('programa.meta_venta', 0)) if pd.notna(row.get('programa.meta_venta')) else None
#                         programa_data['meta_alumnos'] = row.get('programa.meta_alumnos') if pd.notna(row.get('programa.meta_alumnos')) else None
#                         programa_data['punto_minimo_apertura'] = int(row.get('programa.punto_minimo_apertura')) if pd.notna(row.get('programa.punto_minimo_apertura')) else None
#                         programa_data['subdireccion'] = str(row.get('programa.subdireccion')).strip() if pd.notna(row.get('programa.subdireccion')) else None
#                         programa = Programa(**programa_data)
#                         db.add(programa)
#                         db.flush()
#                         programas_dict[programa_codigo] = programa
#         # ...existing code...
#         today = datetime.date.today()
#         tipo_cambios = {}
#         tipo_cambio_pen = db.query(TipoCambio).filter(
#             TipoCambio.moneda_origen == 'PEN',
#             TipoCambio.moneda_target == 'PEN',
#             TipoCambio.fecha_tipo_cambio == today
#         ).first()
#         if not tipo_cambio_pen:
#             tipo_cambio_pen = TipoCambio(
#                 moneda_origen='PEN',
#                 moneda_target='PEN',
#                 equivalencia=1.0,
#                 fecha_tipo_cambio=today,
#                 creado_en=datetime.datetime.now()
#             )
#             db.add(tipo_cambio_pen)
#             db.flush()
#         tipo_cambios['PEN'] = tipo_cambio_pen
#         tipo_cambio_usd = db.query(TipoCambio).filter(
#             TipoCambio.moneda_origen == 'USD',
#             TipoCambio.moneda_target == 'PEN',
#             TipoCambio.fecha_tipo_cambio == today
#         ).first()
#         if not tipo_cambio_usd:
#             tipo_cambio_usd = TipoCambio(
#                 moneda_origen='USD',
#                 moneda_target='PEN',
#                 equivalencia=3.75,
#                 fecha_tipo_cambio=today,
#                 creado_en=datetime.datetime.now()
#             )
#             db.add(tipo_cambio_usd)
#             db.flush()
#         tipo_cambios['USD'] = tipo_cambio_usd
#         tipo_cambio_eur = db.query(TipoCambio).filter(
#             TipoCambio.moneda_origen == 'EUR',
#             TipoCambio.moneda_target == 'PEN',
#             TipoCambio.fecha_tipo_cambio == today
#         ).first()
#         if not tipo_cambio_eur:
#             tipo_cambio_eur = TipoCambio(
#                 moneda_origen='EUR',
#                 moneda_target='PEN',
#                 equivalencia=4.10,
#                 fecha_tipo_cambio=today,
#                 creado_en=datetime.datetime.now()
#             )
#             db.add(tipo_cambio_eur)
#             db.flush()
#         tipo_cambios['EUR'] = tipo_cambio_eur
#         for programa_codigo, programa in programas_dict.items():
#             propuesta_programa_existente = db.query(PropuestaPrograma).filter(
#                 PropuestaPrograma.id_propuesta == propuesta_unica.id_propuesta,
#                 PropuestaPrograma.id_programa == programa.id_programa
#             ).first()
#             if not propuesta_programa_existente:
#                 propuesta_programa = PropuestaPrograma(
#                     id_propuesta=propuesta_unica.id_propuesta,
#                     id_programa=programa.id_programa
#                 )
#                 db.add(propuesta_programa)
#         db.flush()
#         # Procesamiento por lotes en paralelo por programa.codigo
#         import concurrent.futures
#         from sqlalchemy.orm import sessionmaker
#         from sqlalchemy import create_engine
#         # Asume que tienes acceso a la cadena de conexión de la base de datos
#         # Si usas FastAPI y tienes el engine global, reemplaza esto por tu engine
#         engine = db.get_bind()
#         SessionLocal = sessionmaker(bind=engine)

#         def es_atipico(desc, monto=None, precio_lista=None):
#             if not isinstance(desc, float):
#                 return False
#             if desc < 0 or desc > 1:
#                 return True
#             decimales = str(desc).split('.')
#             if len(decimales) == 2:
#                 dec = decimales[1].ljust(4, '0')
#                 if dec[2] != '0' or dec[3] != '0':
#                     return True
#             if monto is not None and precio_lista is not None and precio_lista != 0:
#                 ratio = monto / precio_lista
#                 ratio_decimales = str(ratio).split('.')
#                 if len(ratio_decimales) == 2:
#                     ratio_dec = ratio_decimales[1].ljust(4, '0')
#                     if ratio_dec[2] != '0' or ratio_dec[3] != '0':
#                         return True
#             return False

#         import time
#         def procesar_lote(lote_df):
#             inicio = time.time()
#             programa_codigo = str(lote_df.iloc[0]['programa.codigo']) if 'programa.codigo' in lote_df.columns else 'N/A'
#             print(f"[Lote {programa_codigo}] INICIO procesamiento: {datetime.datetime.now().strftime('%H:%M:%S')}")
#             session = SessionLocal()
#             oportunidades_bulk = []
#             propuestas_bulk = []
#             oportunidades_temp = []
#             for _, row in lote_df.iterrows():
#                 if pd.notna(row.get('oportunidad.nombre')) and pd.notna(row.get('programa.codigo')):
#                     oportunidad_nombre = str(row['oportunidad.nombre']).strip()
#                     programa_codigo = str(row['programa.codigo']).strip()
#                     programa = session.query(Programa).filter(Programa.codigo == programa_codigo).first()
#                     if not programa:
#                         continue
#                     descuento = parse_float(row.get('oportunidad.descuento', 0)) if pd.notna(row.get('oportunidad.descuento')) else 0.0
#                     oportunidad_data = {
#                         'nombre': oportunidad_nombre,
#                         'documento_identidad': str(row.get('oportunidad.documento_identidad', '')).strip() if pd.notna(row.get('oportunidad.documento_identidad')) else '',
#                         'correo': str(row.get('oportunidad.correo', '')).strip() if pd.notna(row.get('oportunidad.correo')) else '',
#                         'telefono': str(row.get('oportunidad.telefono', '')).strip() if pd.notna(row.get('oportunidad.telefono')) else '',
#                         'etapa_venta': str(row.get('oportunidad.etapa_venta', 'NUEVA')).strip() if pd.notna(row.get('oportunidad.etapa_venta')) else 'NUEVA',
#                         'descuento': descuento,
#                         'moneda': str(row.get('oportunidad.moneda', 'PEN')).strip() if pd.notna(row.get('oportunidad.moneda')) else 'PEN',
#                         'monto': parse_float(row.get('oportunidad.monto', 0)) if pd.notna(row.get('oportunidad.monto')) else 0.0,
#                         'becado': bool(row.get('oportunidad.becado', False)) if pd.notna(row.get('oportunidad.becado')) else False,
#                         'conciliado': bool(row.get('oportunidad.conciliado', False)) if pd.notna(row.get('oportunidad.conciliado')) else False,
#                         'posible_atipico': es_atipico(
#                             descuento, 
#                             parse_float(row.get('oportunidad.monto', 0)) if pd.notna(row.get('oportunidad.monto')) else 0.0,
#                             programa.precio_lista if programa and programa.precio_lista else 0
#                         ),
#                         'id_programa': programa.id_programa,
#                         'party_number': str(row.get('oportunidad.party_number', '')).strip() if pd.notna(row.get('oportunidad.party_number')) else '',
#                         'conciliado': bool(row.get('oportunidad.conciliado', False)) if pd.notna(row.get('oportunidad.conciliado')) else False  
#                     }
#                     oportunidad = Oportunidad(**oportunidad_data)
#                     oportunidades_bulk.append(oportunidad)
#                     oportunidades_temp.append((oportunidad, programa_codigo, oportunidad_data))
#             session.bulk_save_objects(oportunidades_bulk)
#             session.flush()
#             for oportunidad, programa_codigo, oportunidad_data in oportunidades_temp:
#                 programa = session.query(Programa).filter(Programa.codigo == programa_codigo).first()
#                 propuesta_programa = session.query(PropuestaPrograma).filter(
#                     PropuestaPrograma.id_propuesta == propuesta_unica.id_propuesta,
#                     PropuestaPrograma.id_programa == programa.id_programa
#                 ).first()
#                 id_propuesta_programa = propuesta_programa.id_propuesta_programa if propuesta_programa else None
#                 tipo_cambio = session.query(TipoCambio).filter(TipoCambio.moneda_origen == oportunidad_data['moneda'], TipoCambio.moneda_target == 'PEN').first()
#                 id_tipo_cambio = tipo_cambio.id_tipo_cambio if tipo_cambio else None
#                 monto_propuesto = oportunidad.monto
#                 propuesta_oportunidad = PropuestaOportunidad(
#                     id_propuesta=propuesta_unica.id_propuesta,
#                     id_oportunidad=oportunidad.id_oportunidad,
#                     id_propuesta_programa=id_propuesta_programa,
#                     id_tipo_cambio=id_tipo_cambio,
#                     monto_propuesto=monto_propuesto,
#                     etapa_venta_propuesto=oportunidad.etapa_venta
#                 )
#                 propuestas_bulk.append(propuesta_oportunidad)
#             session.bulk_save_objects(propuestas_bulk)
#             session.commit()
#             session.close()
#             fin = time.time()
#             duracion = fin - inicio
#             print(f"[Lote {programa_codigo}] FIN procesamiento: {datetime.datetime.now().strftime('%H:%M:%S')} | Duración: {duracion:.2f} segundos")
#             return True

#         # Agrupa el DataFrame por cartera.nombre y procesa cada grupo en paralelo
#         grupos = [group for _, group in df.groupby('cartera.nombre')]
#         with concurrent.futures.ThreadPoolExecutor() as executor:
#             futures = [executor.submit(procesar_lote, grupo) for grupo in grupos]
#             concurrent.futures.wait(futures)
#         # Crear solicitudes de aprobacion comercial para los subdirectores comerciales
#         subdirector_role = db.query(Rol).filter(Rol.nombre == "Comercial - Subdirector").first()
#         daf_subdirector_role = db.query(Rol).filter(Rol.nombre == "DAF - Subdirector").first()
#         subdirectores_comerciales = []
#         if subdirector_role:
#             subdirectores_comerciales = db.query(Usuario).filter(Usuario.id_rol == subdirector_role.id_rol).all()
#         if subdirectores_comerciales:
#             if not daf_subdirector_role:
#                 raise HTTPException(status_code=404, detail="No se encontro el rol 'DAF - Subdirector'")
#             daf_subdirector = db.query(Usuario).filter(Usuario.id_rol == daf_subdirector_role.id_rol).first()
#             if not daf_subdirector:
#                 raise HTTPException(status_code=404, detail="No se encontro un usuario con rol 'DAF - Subdirector'")
#             for subdirector in subdirectores_comerciales:
#                 solicitud_existente = db.query(Solicitud).filter(
#                     Solicitud.id_propuesta == propuesta_unica.id_propuesta,
#                     Solicitud.id_usuario_generador == subdirector.id_usuario,
#                     Solicitud.tipo_solicitud == "APROBACION_COMERCIAL"
#                 ).first()
#                 if solicitud_existente:
#                     continue
#                 comentario = (
#                     f"{subdirector.nombres} confirma, en calidad de Subdirector Comercial, "
#                     "que su cartera ha sido conciliada con los Jefes de Producto."
#                 )
#                 nueva_solicitud = Solicitud(
#                     id_propuesta=propuesta_unica.id_propuesta,
#                     id_usuario_generador=subdirector.id_usuario,
#                     id_usuario_receptor=daf_subdirector.id_usuario,
#                     aceptado_por_responsable=False,
#                     tipo_solicitud="APROBACION_COMERCIAL",
#                     valor_solicitud="PENDIENTE",
#                     comentario=comentario,
#                     creado_en=datetime.datetime.now(),
#                     abierta=True
#                 )
#                 db.add(nueva_solicitud)
#         db.commit()
#         return {
#             "status": "success",
#             "message": "CSV procesado con éxito",
#             "propuesta_id": propuesta_unica.id_propuesta,
#             "propuesta_nombre": propuesta_unica.nombre
#         }
#     except HTTPException:
#         raise
#     except Exception as e:
#         import traceback
#         print("ERROR GENERAL EN process_csv_data:")
#         print(str(e))
#         traceback.print_exc()
#         raise HTTPException(status_code=500, detail=f"Error general en process_csv_data: {str(e)}")




