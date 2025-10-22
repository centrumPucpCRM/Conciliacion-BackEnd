
import pandas as pd
import datetime
import math

from typing import Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException
# Procesamiento por lotes en paralelo, cada lote con su propia sesión
from concurrent.futures import ThreadPoolExecutor
from fastapi_app.database import SessionLocal

from ..models.solicitud_x_programa import SolicitudXPrograma
from ..models.usuario import Usuario
from ..models.cartera import Cartera
from ..models.programa import Programa
from ..models.oportunidad import Oportunidad
from ..models.propuesta import Propuesta, TipoDePropuesta, EstadoPropuesta
from ..models.tipo_cambio import TipoCambio
from ..models.solicitud import Solicitud, TipoSolicitud, ValorSolicitud
from ..models.rol_permiso import Rol


def cargar_carteras(db, df):
    carteras_dict = {}
    if 'cartera.nombre' in df.columns:
        nombres_unicos = [nombre.strip() for nombre in df['cartera.nombre'].dropna().unique()]
        existentes = db.query(Cartera).filter(Cartera.nombre.in_(nombres_unicos)).all()
        existentes_dict = {c.nombre: c for c in existentes}
        nuevas = []
        for cartera_nombre in nombres_unicos:
            if cartera_nombre not in existentes_dict:
                cartera = Cartera(nombre=cartera_nombre)
                nuevas.append(cartera)
                carteras_dict[cartera_nombre] = cartera
            else:
                carteras_dict[cartera_nombre] = existentes_dict[cartera_nombre]
        if nuevas:
            db.bulk_save_objects(nuevas)
            db.flush()
    return carteras_dict

def cargar_jps(db, df, carteras_dict, usuarios_dict):
    """
    Carga Jefes de Producto desde el CSV.
    Crea usuarios con rol 'Comercial - Jefe de producto' y les asigna carteras.
    """
    usuario_carteras_map = {}
    
    # Construir mapa usuario JP -> set(carteras)
    for _, row in df.iterrows():
        u = row.get('usuario.nombre')
        c = row.get('cartera.nombre')
        if pd.notna(u) and pd.notna(c):
            usuario_carteras_map.setdefault(str(u), set()).add(str(c))
    
    if not usuario_carteras_map:
        return
    
    # Obtener rol JP
    rol_jp = db.query(Rol).filter(Rol.nombre == "Comercial - Jefe de producto").first()
    
    # Traer existentes exactamente por nombre
    nombres_jp = list(usuario_carteras_map.keys())
    existentes_jp = db.query(Usuario).filter(Usuario.nombre.in_(nombres_jp)).all()
    existentes_jp_dict = {str(u.nombre): u for u in existentes_jp}
    
    # Crear faltantes y/o usar existentes
    for un in nombres_jp:
        u = existentes_jp_dict.get(un)
        if not u:
            u = Usuario(
                nombre=un,
                clave=str(un).replace(' ', '.'),
                correo=f"{str(un).replace(' ', '.')}@ejemplo.com",
                activo=True
            )
            db.add(u)
        if rol_jp and rol_jp not in u.roles:
            u.roles.append(rol_jp)
        usuarios_dict[un] = u
    
    # Asegurar IDs antes de relaciones
    db.flush()
    
    # Asignar carteras evitando duplicados
    for un, carteras in usuario_carteras_map.items():
        usuario = usuarios_dict[un]
        actuales = {c.nombre for c in usuario.carteras}
        for cn in carteras:
            cartera = carteras_dict.get(cn)
            if cartera and cartera.nombre not in actuales:
                usuario.carteras.append(cartera)
                actuales.add(cartera.nombre)

def cargar_subdirectores(db, df, carteras_dict, usuarios_dict):
    """
    Carga Subdirectores desde el CSV.
    Crea usuarios con rol 'Comercial - Subdirector' y les asigna carteras.
    """
    subdirector_carteras_map = {}
    
    # Construir mapa subdirector -> set(carteras)
    for _, row in df.iterrows():
        s = row.get('usuario.nombreSubdirector')
        c = row.get('cartera.nombre')
        if pd.notna(s) and pd.notna(c):
            subdirector_carteras_map.setdefault(str(s), set()).add(str(c))
    
    if not subdirector_carteras_map:
        return
    
    # Obtener rol Subdirector
    rol_subdirector = db.query(Rol).filter(Rol.nombre == "Comercial - Subdirector").first()
    
    # Traer existentes exactamente por nombre
    nombres_subdirectores = list(subdirector_carteras_map.keys())
    existentes_subdirectores = db.query(Usuario).filter(Usuario.nombre.in_(nombres_subdirectores)).all()
    existentes_subdirectores_dict = {str(u.nombre): u for u in existentes_subdirectores}
    
    # Crear faltantes y/o usar existentes
    for sn in nombres_subdirectores:
        u = existentes_subdirectores_dict.get(sn)
        if not u:
            u = Usuario(
                nombre=sn,
                clave=str(sn).replace(' ', '.'),
                correo=f"{str(sn).replace(' ', '.')}@ejemplo.com",
                activo=True
            )
            db.add(u)
        if rol_subdirector and rol_subdirector not in u.roles:
            u.roles.append(rol_subdirector)
        usuarios_dict[sn] = u
    
    # Asegurar IDs antes de relaciones
    db.flush()
    
    # Asignar carteras evitando duplicados
    for sn, carteras in subdirector_carteras_map.items():
        subdirector = usuarios_dict[sn]
        actuales = {c.nombre for c in subdirector.carteras}
        for cn in carteras:
            cartera = carteras_dict.get(cn)
            if cartera and cartera.nombre not in actuales:
                subdirector.carteras.append(cartera)
                actuales.add(cartera.nombre)

def cargar_usuarios(db, df, carteras_dict):
    """
    Carga todos los usuarios (JPs y Subdirectores) desde el CSV.
    Orquesta la carga de ambos tipos de usuarios.
    """
    usuarios_dict = {}
    
    # Cargar Jefes de Producto
    cargar_jps(db, df, carteras_dict, usuarios_dict)
    
    # Cargar Subdirectores
    cargar_subdirectores(db, df, carteras_dict, usuarios_dict)
    
    return usuarios_dict



def cargar_propuesta(db, data):
    now = datetime.datetime.now()
    propuesta_info = data.get("propuesta") if isinstance(data, dict) else {}
    propuesta_nombre = propuesta_info.get("nombre") or f"Propuesta_{now.strftime('%Y%m%d_%H%M%S')}"

    # Get or create TipoDePropuesta instance
    tipo_obj = db.query(TipoDePropuesta).filter_by(nombre="CREACION").first()
    if not tipo_obj:
        tipo_obj = TipoDePropuesta(nombre="CREACION")
        db.add(tipo_obj)
        db.flush()

    # Get or create EstadoPropuesta instance
    estado_obj = db.query(EstadoPropuesta).filter_by(nombre="GENERADA").first()
    if not estado_obj:
        estado_obj = EstadoPropuesta(nombre="GENERADA")
        db.add(estado_obj)
        db.flush()

    propuesta_unica = Propuesta(
        nombre=propuesta_nombre,
        descripcion="Propuesta generada automáticamente desde archivo CSV",
        tipoDePropuesta=tipo_obj,
        estadoPropuesta=estado_obj,
        creadoEn=now,
        fechaPropuesta=data.get("fechaDatos"),
        horaPropuesta=data.get("horaDatos")
    )
    # Assign carteras as model instances
    cartera_names = propuesta_info.get("carteras", [])
    cartera_objs = []
    for name in cartera_names:
        cartera = db.query(Cartera).filter(Cartera.nombre == name.strip()).first()
        if not cartera:
            cartera = Cartera(nombre=name.strip())
            db.add(cartera)
            db.flush()
        cartera_objs.append(cartera)
    # Ensure only unique carteras are linked
    propuesta_unica.carteras = list({c.id: c for c in cartera_objs}.values())
    db.add(propuesta_unica)
    db.flush()
    return propuesta_unica


def cargar_programas(db, df, propuesta_unica, usuarios_dict):
    def sanitize_value(val):
        """Convierte NaN, None, y strings vacíos a None, y tipos NumPy a Python nativos"""
        if val is None:
            return None
        if isinstance(val, float):
            if math.isnan(val):
                return None
            return val
        if isinstance(val, str):
            stripped = val.strip()
            if stripped == '' or stripped.lower() in {'nan', 'none'}:
                return None
            return stripped
        # Convertir tipos NumPy a Python nativos
        if hasattr(val, 'item'):  # numpy types have .item() method
            return val.item()
        return val
    
    programas_dict = {}
    fecha_propuesta = propuesta_unica.creadoEn.date() if hasattr(propuesta_unica.creadoEn, 'date') else propuesta_unica.creadoEn
    tipos_cambio = db.query(TipoCambio).filter(TipoCambio.fecha_tipo_cambio == fecha_propuesta).all()
    tipos_cambio_dict = {tc.moneda_origen: tc for tc in tipos_cambio}
    # Agrupa por programa.codigo y toma la primera fila de cada grupo
    df_programas = df.dropna(subset=['programa.codigo'])
    grouped = df_programas.groupby(df_programas['programa.codigo'].astype(str).str.strip())
    programas_bulk = []
    for programa_codigo, group in grouped:
        row = group.iloc[0]
        
        # Sanitizar todos los valores antes de usarlos
        programa_nombre = sanitize_value(row.get('programa.nombre', f"Programa {programa_codigo}"))
        if programa_nombre is None:
            programa_nombre = f"Programa {programa_codigo}"
        
        moneda = sanitize_value(row.get('programa.moneda', 'PEN'))
        if moneda is None:
            moneda = 'PEN'
        
        subdireccion = sanitize_value(row.get('programa.subdireccion'))
        usuario_nombre = sanitize_value(row.get('usuario.nombre', ''))
        usuario_nombreSubdirector = sanitize_value(row.get('usuario.nombreSubdirector', ''))
        
        fecha_inauguracion = sanitize_value(row.get('programa.fecha_de_inauguracion'))
        
        # Calcular mes de forma segura
        if fecha_inauguracion and pd.notna(fecha_inauguracion):
            try:
                mes = pd.to_datetime(fecha_inauguracion).strftime('%m')
            except:
                mes = None
        else:
            mes = None
        
        precio_lista = sanitize_value(row.get('programa.precio_lista', 0))
        meta_venta = sanitize_value(row.get('programa.meta_venta', 0))
        punto_minimo = sanitize_value(row.get('programa.punto_minimo_apertura', 0))
        meta_alumnos = sanitize_value(row.get('programa.meta_alumnos', 0))
        cartera_nombre = sanitize_value(row.get('cartera.nombre'))
        
        # Convertir a tipos correctos después de sanitizar
        precio_lista = float(precio_lista) if precio_lista is not None else 0.0
        meta_venta = float(meta_venta) if meta_venta is not None else 0.0
        punto_minimo = int(punto_minimo) if punto_minimo is not None else 0
        meta_alumnos = int(meta_alumnos) if meta_alumnos is not None else 0
        
        programa = Programa(
            codigo=programa_codigo,
            nombre=programa_nombre,
            fechaDeInaguracion=fecha_inauguracion,
            moneda=moneda,
            precioDeLista=precio_lista,
            metaDeVenta=meta_venta,
            puntoMinimoApertura=punto_minimo,
            subdireccion=subdireccion,
            idPropuesta=propuesta_unica.id,
            idJefeProducto=usuarios_dict.get(usuario_nombre).id if usuario_nombre and usuario_nombre in usuarios_dict else None,
            idSubdirector=usuarios_dict.get(usuario_nombreSubdirector).id if usuario_nombreSubdirector and usuario_nombreSubdirector in usuarios_dict else None,
            fechaInaguracionPropuesta=fecha_inauguracion,
            idTipoCambio=tipos_cambio_dict.get(moneda).id if moneda in tipos_cambio_dict else None,
            cartera=cartera_nombre,
            mes=mes,
            mesPropuesto=mes,
            metaDeAlumnos=meta_alumnos
        )
        programas_bulk.append(programa)
        programas_dict[programa_codigo] = programa
    if programas_bulk:
        db.bulk_save_objects(programas_bulk)
        db.flush()
        db.commit()
    programas = db.query(Programa).filter(Programa.idPropuesta == propuesta_unica.id).all()
    for programa in programas:
        programas_dict[programa.codigo] = programa
    return programas_dict

def cargar_oportunidades(db, df, propuesta_unica, programas_dict):
    # Cargar solo los tipos de cambio cuya fecha_tipo_cambio coincide con la fecha de creación de la propuesta
    fecha_propuesta = propuesta_unica.creadoEn.date() if hasattr(propuesta_unica.creadoEn, 'date') else propuesta_unica.creadoEn
    tipos_cambio = db.query(TipoCambio).filter(TipoCambio.fecha_tipo_cambio == fecha_propuesta).all()
    tipos_cambio_dict = {tc.moneda_origen: tc for tc in tipos_cambio}
    
    def sanitize_str(val):
        sval = str(val).strip()
        return '' if sval.lower() == 'nan' or sval == 'None' else sval
    def sanitize_int(val):
        try:
            sval = str(val).strip()
            if val is None or (isinstance(val, float) and math.isnan(val)) or sval.lower() == 'nan' or sval == '':
                return None
            return int(val)
        except:
            return None
    def sanitize_float(val):
        try:
            if val is None or (isinstance(val, float) and math.isnan(val)) or str(val).lower() == 'nan':
                return 0.0
            return float(val)
        except:
            return 0.0
    def sanitize_bool(val):
        if str(val).lower() == 'nan' or val is None:
            return False
        return bool(val)
    
    # Helper para sanitizar moneda específicamente
    def sanitize_moneda(val):
        """Sanitiza moneda, devuelve 'PEN' por defecto si es None o inválido"""
        if val is None:
            return 'PEN'
        if isinstance(val, float) and math.isnan(val):
            return 'PEN'
        sval = str(val).strip()
        if sval.lower() in {'nan', 'none', ''}:
            return 'PEN'
        return sval

    # Calcular si es atípico fila por fila (simple, no vectorizado)
    atipicos = []
    for idx, row in df.iterrows():
        descuento = float(row.get('oportunidad.descuento', 0) or 0)
        monto = float(row.get('oportunidad.monto', 0) or 0)
        precio_lista = float(row.get('oportunidad.precio_lista', 0) or 0)
        cond1 = descuento < 0 or descuento > 1
        # decimales de descuento
        decimales_desc = str(round(descuento, 4)).split('.')
        cond2 = len(decimales_desc) == 2 and len(decimales_desc[1]) > 2 and decimales_desc[1][2:] != '00'
        # decimales de monto/precio_lista
        ratio = monto / precio_lista if precio_lista else 0
        decimales_ratio = str(round(ratio, 4)).split('.')
        cond3 = len(decimales_ratio) == 2 and len(decimales_ratio[1]) > 2 and decimales_ratio[1][2:] != '00'
        atipicos.append(cond1 or cond2 or cond3)
    df['oportunidad.posibleAtipico'] = atipicos
    oportunidades_bulk = []
    oportunidades_dict = {}
    propuesta_id = propuesta_unica.id
    for idx, row in df.iterrows():
        try:
            if pd.notna(row.get('oportunidad.nombre')):
                oportunidad_nombre = sanitize_str(row['oportunidad.nombre'])
                documentoIdentidad = sanitize_str(row.get('oportunidad.documento_identidad', ''))
                correo = sanitize_str(row.get('oportunidad.correo', ''))
                telefono = sanitize_str(row.get('oportunidad.telefono', ''))
                etapaDeVentas = sanitize_str(row.get('oportunidad.etapa_venta', 'NUEVA'))
                moneda = sanitize_moneda(row.get('oportunidad.moneda'))  # ✅ Usa sanitize_moneda
                programa_codigo = sanitize_str(row.get('programa.codigo', ''))
                
                # Obtener id_tipo_cambio de forma segura
                tipo_cambio_obj = tipos_cambio_dict.get(moneda)
                id_tipo_cambio = tipo_cambio_obj.id if tipo_cambio_obj else None
                
                descuento = sanitize_float(row.get('oportunidad.descuento', 0))
                monto = sanitize_float(row.get('oportunidad.monto', 0))
                becado = sanitize_bool(row.get('oportunidad.becado', False))
                partyNumber = sanitize_int(row.get('oportunidad.party_number', 0))
                conciliado = sanitize_bool(row.get('oportunidad.conciliado', False))
                posibleAtipico = bool(row.get('oportunidad.posibleAtipico', False))
                idPrograma = programas_dict.get(programa_codigo).id if programa_codigo in programas_dict else None
                oportunidad = Oportunidad(
                    nombre=oportunidad_nombre,
                    documentoIdentidad=documentoIdentidad,
                    correo=correo,
                    telefono=telefono,
                    etapaDeVentas=etapaDeVentas,
                    descuento=descuento,
                    monto=monto,
                    moneda=moneda,
                    fechaMatricula=row.get('oportunidad.fecha_matricula'),
                    becado=becado,
                    partyNumber=partyNumber,
                    conciliado=conciliado,
                    idPropuesta=propuesta_id,
                    idPrograma=idPrograma,
                    idTipoCambio=id_tipo_cambio,
                    montoPropuesto=monto,
                    etapaVentaPropuesta=etapaDeVentas,
                    fechaMatriculaPropuesta=row.get('oportunidad.fecha_matricula'),
                    posibleAtipico=posibleAtipico,
                )
                oportunidades_bulk.append(oportunidad)
                oportunidades_dict[oportunidad_nombre] = oportunidad
        except Exception as e:
            print(f"[ERROR] Oportunidad fila {idx}: {e}\nDatos: {row.to_dict()}")
            db.rollback()
    if oportunidades_bulk:
        try:
            db.bulk_save_objects(oportunidades_bulk)
            db.commit()
        except Exception as e:
            print(f"[ERROR] Bulk insert final: {e}")
            db.rollback()
    return oportunidades_dict

def cargar_tipo_cambio(db):
    today = datetime.date.today()
    for moneda in ['PEN', 'USD', 'EUR']:
        tipo_cambio = db.query(TipoCambio).filter(
            TipoCambio.moneda_origen == moneda,
            TipoCambio.moneda_target == 'PEN',
            TipoCambio.fecha_tipo_cambio == today
        ).first()
        if not tipo_cambio:
            equivalencias = {'PEN': 1.0, 'USD': 3.75, 'EUR': 4.10}
            tipo_cambio = TipoCambio(
                moneda_origen=moneda,
                moneda_target='PEN',
                equivalencia=equivalencias[moneda],
                fecha_tipo_cambio=today
            )
            db.add(tipo_cambio)
            db.flush()

def crear_solicitudes_subdirectores(db, propuesta_unica):
    from fastapi_app.models.log import Log
    tipo_aprobacion = db.query(TipoSolicitud).filter_by(nombre="APROBACION_COMERCIAL").first()
    valor_pendiente = db.query(ValorSolicitud).filter_by(nombre="PENDIENTE").first()
    
    # Obtener dinámicamente todos los usuarios con rol "Comercial - Subdirector"
    rol_subdirector = db.query(Rol).filter(Rol.nombre == "Comercial - Subdirector").first()
    if not rol_subdirector:
        print(f"[WARNING] Rol 'Comercial - Subdirector' no encontrado. Saltando creación de solicitudes de subdirectores.")
        return
    
    subdirectores = db.query(Usuario).join(Usuario.roles).filter(Rol.id == rol_subdirector.id).all()
    
    if not subdirectores:
        print(f"[WARNING] No se encontraron usuarios con rol 'Comercial - Subdirector'. Saltando creación de solicitudes.")
        return
    
    solicitudes_bulk = []
    logs_bulk = []
    
    # Obtener el receptor (DAF Subdirector)
    receptor_usuario = db.query(Usuario).filter(Usuario.nombre == 'daf.subdirector').first()
    
    # Validar que el receptor existe
    if not receptor_usuario:
        print(f"[WARNING] Usuario 'daf.subdirector' no encontrado. Saltando creación de solicitudes de subdirectores.")
        return
    
    for subdirector in subdirectores:
        comentario = f"Solicitud de {subdirector.nombre} para revision"
        nueva_solicitud = Solicitud(
            idUsuarioGenerador=subdirector.id,
            idUsuarioReceptor=receptor_usuario.id,
            tipoSolicitud_id=tipo_aprobacion.id,
            valorSolicitud_id=valor_pendiente.id,
            idPropuesta=propuesta_unica.id,
            comentario=comentario,
            creadoEn=datetime.datetime.now(),
            abierta=True
        )
        solicitudes_bulk.append(nueva_solicitud)
    if solicitudes_bulk:
        db.bulk_save_objects(solicitudes_bulk)
        db.flush()
        # Refrescar solicitudes_bulk con los ids asignados
        solicitudes_db = db.query(Solicitud).filter(Solicitud.idPropuesta == propuesta_unica.id, Solicitud.tipoSolicitud_id == tipo_aprobacion.id).all()
        for s in solicitudes_db:
            log_data = {
                'idSolicitud': s.id,
                'tipoSolicitud_id': s.tipoSolicitud_id,
                'creadoEn': datetime.datetime.now(),
                'auditoria': {
                    'idUsuarioReceptor': s.idUsuarioReceptor,
                    'idUsuarioGenerador': s.idUsuarioGenerador,
                    'idPropuesta': s.idPropuesta,
                    'comentario': s.comentario,
                    'abierta': s.abierta,
                    'valorSolicitud_id': s.valorSolicitud_id
                }
            }
            log = Log(**log_data)
            logs_bulk.append(log)
        db.bulk_save_objects(logs_bulk)
        db.flush()


def crear_solicitudes_Jp(db, propuesta_unica):
    from fastapi_app.models.log import Log
    
    tipo_aprobacion = db.query(TipoSolicitud).filter_by(nombre="APROBACION_JP").first()
    valor_pendiente = db.query(ValorSolicitud).filter_by(nombre="PENDIENTE").first()
    
    # Obtener todos los programas de esta propuesta con JP y Subdirector asignados
    programas = db.query(Programa).filter(
        Programa.idPropuesta == propuesta_unica.id,
        Programa.idJefeProducto.isnot(None),
        Programa.idSubdirector.isnot(None)
    ).all()
    
    if not programas:
        print(f"[WARNING] No se encontraron programas con JP y Subdirector asignados. Saltando creación de solicitudes JP.")
        return
    
    # Crear conjunto de combinaciones únicas (idJefeProducto, idSubdirector)
    combinaciones_unicas = set()
    for programa in programas:
        combinaciones_unicas.add((programa.idJefeProducto, programa.idSubdirector))
    
    if not combinaciones_unicas:
        print(f"[WARNING] No se encontraron combinaciones JP-Subdirector. Saltando creación de solicitudes JP.")
        return
    
    # Obtener todos los usuarios necesarios de una vez
    usuarios_ids = set()
    for jp_id, sub_id in combinaciones_unicas:
        usuarios_ids.add(jp_id)
        usuarios_ids.add(sub_id)
    
    usuarios = db.query(Usuario).filter(Usuario.id.in_(usuarios_ids)).all()
    usuarios_dict = {u.id: u for u in usuarios}
    
    solicitudes_bulk = []
    logs_bulk = []
    
    # Crear UNA solicitud por cada combinación única JP → Subdirector
    for jp_id, subdirector_id in combinaciones_unicas:
        jp_usuario = usuarios_dict.get(jp_id)
        subdirector_usuario = usuarios_dict.get(subdirector_id)
        
        if not jp_usuario or not subdirector_usuario:
            print(f"[WARNING] Usuario no encontrado (JP: {jp_id}, Subdirector: {subdirector_id}). Saltando solicitud.")
            continue
        
        comentario = f"Solicitud de {jp_usuario.nombre} para revisión de {subdirector_usuario.nombre}"
        
        nueva_solicitud = Solicitud(
            idUsuarioGenerador=jp_usuario.id,
            idUsuarioReceptor=subdirector_usuario.id,
            tipoSolicitud_id=tipo_aprobacion.id,
            valorSolicitud_id=valor_pendiente.id,
            idPropuesta=propuesta_unica.id,
            comentario=comentario,
            creadoEn=datetime.datetime.now(),
            abierta=True
        )
        solicitudes_bulk.append(nueva_solicitud)
    if solicitudes_bulk:
        db.bulk_save_objects(solicitudes_bulk)
        db.flush()
        # Refrescar solicitudes_bulk con los ids asignados
        solicitudes_db = db.query(Solicitud).filter(Solicitud.idPropuesta == propuesta_unica.id, Solicitud.tipoSolicitud_id == tipo_aprobacion.id).all()
        for s in solicitudes_db:
            log_data = {
                'idSolicitud': s.id,
                'tipoSolicitud_id': s.tipoSolicitud_id,
                'creadoEn': datetime.datetime.now(),
                'auditoria': {
                    'idUsuarioReceptor': s.idUsuarioReceptor,
                    'idUsuarioGenerador': s.idUsuarioGenerador,
                    'idPropuesta': s.idPropuesta,
                    'comentario': s.comentario,
                    'abierta': s.abierta,
                    'valorSolicitud_id': s.valorSolicitud_id
                }
            }
            log = Log(**log_data)
            logs_bulk.append(log)
        db.bulk_save_objects(logs_bulk)
        db.flush()


# Agrupa la carga de CSV, carteras, usuarios y propuesta
def cargar_datos_base(db, data):
    df = cargar_csv(data)
    db.commit()
    carteras_dict = cargar_carteras(db, df)
    db.commit()
    usuarios_dict = cargar_usuarios(db, df, carteras_dict)
    db.commit()
    propuesta_unica = cargar_propuesta(db, data)
    return df, usuarios_dict, propuesta_unica

import pandas as pd
def cargar_csv(data):
    fecha = data.get("fechaDatos")
    hora = data.get("horaDatos")
    csv_url = "https://centrum-conciliacion-service.s3.us-east-1.amazonaws.com/CONCILIACION_" + fecha + "+" + hora + ".xlsx"
    DATE_COLS = [
        'programa.fecha_de_inicio',
        'programa.fecha_de_inauguracion',
        'programa.fecha_ultima_postulante',
        'oportunidad.fecha_matricula',
    ]
    df = pd.read_excel(
        csv_url,
        sheet_name="Conciliacion",
        parse_dates=DATE_COLS,
        engine="openpyxl",
        keep_default_na=True,
        na_filter=True,
    )

    for c in DATE_COLS:
        if c in df.columns:
            # strftime -> 'YYYY-MM-DD'; NaT permanece como NaT y luego lo pasamos a None
            s = df[c].dt.strftime('%Y-%m-%d')
            df[c] = s.where(df[c].notna(), None)

    df = df.copy()
    df.columns = df.columns.str.strip()
    return df

def crearRelacionCarteraSubdirectoresYDAF(db: Session, df: pd.DataFrame, propuesta: Propuesta) -> None:
    # Nombres de usuarios clave
    nombres_usuarios = ["daf.supervisor","daf.subdirector",
        "admin","Jefe grado","Jefe ee","Jefe CentrumX"]

    # Buscar usuarios por nombre (ignorando mayúsculas/minúsculas y espacios)
    usuarios = db.query(Usuario).filter(
        Usuario.nombre.in_([n.strip() for n in nombres_usuarios])
    ).all()
    usuarios_dict = {u.nombre.strip().lower(): u for u in usuarios}

    carteras_col = 'cartera.nombre'

    nombres_carteras = [str(n).strip() for n in df[carteras_col].dropna().unique()]
    carteras = db.query(Cartera).filter(Cartera.nombre.in_(nombres_carteras)).all()
    carteras_dict = {c.nombre.strip(): c for c in carteras}

    # Asignar todas las carteras a cada usuario clave
    for usuario in usuarios_dict.values():
        for cartera in carteras_dict.values():
            if cartera not in usuario.carteras:
                usuario.carteras.append(cartera)
    db.flush()
    
def process_csv_data(db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
# Alias para compatibilidad con el endpoint
    import time
    timings = {}
    try:
        total_start = time.time()

        # 1. Cargar datos base
        start = time.time()
        df, usuarios_dict, propuesta_unica = cargar_datos_base(db, data)
        timings['cargar_datos_base'] = time.time() - start
        print(f"Tiempo cargar_datos_base: {timings['cargar_datos_base']:.4f} segundos")

        # 2. Cargar tipo de cambio y hacer commit SOLO aquí
        start = time.time()
        cargar_tipo_cambio(db)
        db.commit()  # Commit solo para guardar tipo de cambio
        timings['cargar_tipo_cambio'] = time.time() - start
        print(f"Tiempo cargar_tipo_cambio: {timings['cargar_tipo_cambio']:.4f} segundos")

        # 3. Cargar programas
        start = time.time()
        programas_dict = cargar_programas(db, df, propuesta_unica, usuarios_dict)
        timings['cargar_programas'] = time.time() - start
        print(f"Tiempo cargar_programas: {timings['cargar_programas']:.4f} segundos")
        db.commit()  # Commit solo para guardar programas

        # 4. Cargar oportunidades
        start = time.time()
        cargar_oportunidades(db, df, propuesta_unica, programas_dict)
        timings['cargar_oportunidades'] = time.time() - start
        print(f"Tiempo cargar_oportunidades: {timings['cargar_oportunidades']:.4f} segundos")

        # 5. Crear solicitudes de aprobación por cartera y subdirección
        start = time.time()
        crear_solicitudes_subdirectores(db, propuesta_unica)
        timings['generar_solicitudes_aprobacion'] = time.time() - start
        print(f"Tiempo generar_solicitudes_aprobacion: {timings['generar_solicitudes_aprobacion']:.4f} segundos")

        # 6. Crear solicitudes de aprobación JP
        start = time.time()
        crear_solicitudes_Jp(db, propuesta_unica)
        timings['crear_solicitudes_Jp'] = time.time() - start
        print(f"Tiempo crear_solicitudes_Jp: {timings['crear_solicitudes_Jp']:.4f} segundos")

        # 7 aca se tiene que crear una relacion entre la cartera que se esta ingresando y  
        start = time.time()
        crearRelacionCarteraSubdirectoresYDAF(db, df, propuesta_unica)
        timings['crearRelacionCarteraSubdirectoresYDAF'] = time.time() - start
        print(f"Tiempo crearRelacionCarteraSubdirectoresYDAF: {timings['crearRelacionCarteraSubdirectoresYDAF']:.4f} segundos")

        
        # 7. Commit final para guardar todo lo demás
        db.commit()
        total_time = time.time() - total_start
        print(f"\n=== TIEMPO TOTAL: {total_time:.4f} segundos ===\n")        
        
        return {
            "status": "success",
            "message": "CSV procesado con éxito",
            "propuesta_id": "asdas",
            "propuesta_nombre": "sadsad",
            "timings": timings,
            "total_time": total_time
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error general en process_csv_data_v2: {str(e)}")
