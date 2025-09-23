import pandas as pd
import datetime
from typing import Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException
# Procesamiento por lotes en paralelo, cada lote con su propia sesión
from concurrent.futures import ThreadPoolExecutor
from fastapi_app.database import SessionLocal

from ..models.usuario import Usuario
from ..models.cartera import Cartera
from ..models.programa import Programa
from ..models.oportunidad import Oportunidad
from ..models.propuesta import Propuesta, TipoDePropuesta, EstadoPropuesta
from ..models.tipo_cambio import TipoCambio
from ..models.solicitud import Solicitud, TipoSolicitud
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

def cargar_usuarios(db, df, carteras_dict):
    usuarios_dict = {}
    usuario_carteras_map = {}
    for _, row in df.iterrows():
        if pd.notna(row.get('usuario.nombre')) and pd.notna(row.get('cartera.nombre')):
            usuario_nombre = row['usuario.nombre'].strip()
            cartera_nombre = row['cartera.nombre'].strip()
            if usuario_nombre not in usuario_carteras_map:
                usuario_carteras_map[usuario_nombre] = set()
            usuario_carteras_map[usuario_nombre].add(cartera_nombre)
    rol = db.query(Rol).filter(Rol.nombre == "Administrador").first()
    nombres_unicos = list(usuario_carteras_map.keys())
    existentes = db.query(Usuario).filter(Usuario.nombre.in_(nombres_unicos)).all()
    existentes_dict = {u.nombre: u for u in existentes}
    nuevos = []
    for usuario_nombre in nombres_unicos:
        if usuario_nombre not in existentes_dict:
            usuario = Usuario(
                nombre=usuario_nombre,
                correo=f"{usuario_nombre.lower().replace(' ', '.')}@ejemplo.com",
                activo=True
            )
            if rol:
                usuario.roles.append(rol)
            nuevos.append(usuario)
            usuarios_dict[usuario_nombre] = usuario
        else:
            usuarios_dict[usuario_nombre] = existentes_dict[usuario_nombre]
    if nuevos:
        db.bulk_save_objects(nuevos)
        db.flush()
    # Asignar carteras a usuarios
    for usuario_nombre, cartera_nombres in usuario_carteras_map.items():
        usuario = usuarios_dict[usuario_nombre]
        for cartera_nombre in cartera_nombres:
            cartera = carteras_dict.get(cartera_nombre)
            if cartera and cartera not in usuario.carteras:
                usuario.carteras.append(cartera)
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
        creadoEn=now
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
    programas_dict = {}
    fecha_propuesta = propuesta_unica.creadoEn.date() if hasattr(propuesta_unica.creadoEn, 'date') else propuesta_unica.creadoEn
    tipos_cambio = db.query(TipoCambio).filter(TipoCambio.fecha_tipo_cambio == fecha_propuesta).all()
    tipos_cambio_dict = {tc.moneda_origen: tc for tc in tipos_cambio}
    print(f"[INFO] Tipos de cambio encontrados para fecha {fecha_propuesta}: {list(tipos_cambio_dict.keys())}")

    # Agrupa por programa.codigo y toma la primera fila de cada grupo
    df_programas = df.dropna(subset=['programa.codigo'])
    grouped = df_programas.groupby(df_programas['programa.codigo'].astype(str).str.strip())
    programas_bulk = []
    for programa_codigo, group in grouped:
        row = group.iloc[0]
        programa_nombre = str(row.get('programa.nombre', f"Programa {programa_codigo}")).strip()
        moneda = str(row.get('programa.moneda', 'PEN')).strip()
        subdireccion = str(row.get('programa.subdireccion', '')) if row.get('programa.subdireccion', None) is not None else None
        usuario_nombre = str(row.get('usuario.nombre', '')).strip()

        programa = Programa(
            codigo=programa_codigo,
            nombre=programa_nombre,
            fechaDeInaguracion=row.get('programa.fecha_de_inauguracion'),
            moneda=moneda,
            precioDeLista=float(row.get('programa.precio_lista', 0)),
            metaDeVenta=float(row.get('programa.meta_venta', 0)),
            puntoMinimoApertura=int(row.get('programa.punto_minimo_apertura', 0)),
            subdireccion=subdireccion,
            idPropuesta=propuesta_unica.id,
            idJefeProducto=usuarios_dict.get(usuario_nombre).id if usuario_nombre in usuarios_dict else None,
            fechaInaguracionPropuesta=row.get('programa.fecha_de_inauguracion'),
            idTipoCambio=tipos_cambio_dict.get(moneda).id,
        )
        programas_bulk.append(programa)
        programas_dict[programa_codigo] = programa
    if programas_bulk:
        db.bulk_save_objects(programas_bulk)
        db.flush()
    return programas_dict

def cargar_oportunidades(db, df, propuesta_unica, programas_dict):
    import math
    # Cargar solo los tipos de cambio cuya fecha_tipo_cambio coincide con la fecha de creación de la propuesta
    fecha_propuesta = propuesta_unica.creadoEn.date() if hasattr(propuesta_unica.creadoEn, 'date') else propuesta_unica.creadoEn
    tipos_cambio = db.query(TipoCambio).filter(TipoCambio.fecha_tipo_cambio == fecha_propuesta).all()
    tipos_cambio_dict = {tc.moneda_origen: tc for tc in tipos_cambio}
    print(f"[INFO] Tipos de cambio encontrados para fecha {fecha_propuesta}: {list(tipos_cambio_dict.keys())}")
    
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

    # Vectorized es_atipico calculation for the DataFrame
    def es_atipico_vectorizado(descuento, monto, precio_lista):
        try:
            descuento_float = descuento.astype(float)
        except Exception:
            descuento_float = pd.Series([0.0]*len(descuento))
        cond1 = (descuento_float < 0) | (descuento_float > 1)
        decimales = descuento_float.round(4).astype(str).str.split('.')
        cond2 = decimales.apply(lambda x: len(x) == 2 and x[1][2:] != '00')
        ratio = monto / precio_lista.replace(0, 1)
        ratio_decimales = ratio.round(4).astype(str).str.split('.')
        cond3 = ratio_decimales.apply(lambda x: len(x) == 2 and x[1][2:] != '00')
        return cond1 | cond2 | cond3

    # Prepare precio_lista series for each oportunidad
    df['programa.codigo'] = df['programa.codigo'].astype(str).str.strip()
    precio_lista_map = {k: v.precioDeLista for k, v in programas_dict.items()}
    df['precio_lista_prog'] = df['programa.codigo'].map(precio_lista_map).fillna(0)
    df['oportunidad.posibleAtipico'] = es_atipico_vectorizado(
        df['oportunidad.descuento'].fillna(0),
        df['oportunidad.monto'].fillna(0),
        df['precio_lista_prog'].fillna(0)
    )

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
                moneda = sanitize_str(row.get('oportunidad.moneda', 'PEN'))
                programa_codigo = sanitize_str(row.get('programa.codigo', ''))
                id_tipo_cambio = tipos_cambio_dict.get(moneda).id  
                descuento = sanitize_float(row.get('oportunidad.descuento', 0))
                monto = sanitize_float(row.get('oportunidad.monto', 0))
                becado = sanitize_bool(row.get('oportunidad.becado', False))
                partyNumber = sanitize_int(row.get('oportunidad.party_number', 0))
                conciliado = sanitize_bool(row.get('oportunidad.conciliado', False))
                posibleAtipico = bool(row.get('oportunidad.posibleAtipico', False))
                oportunidad = Oportunidad(
                    nombre=oportunidad_nombre,
                    documentoIdentidad=documentoIdentidad,
                    correo=correo,
                    telefono=telefono,
                    etapaDeVentas=etapaDeVentas,
                    descuento=descuento,
                    monto=monto,
                    becado=becado,
                    partyNumber=partyNumber,
                    conciliado=conciliado,
                    idPropuesta=propuesta_id,
                    idPrograma=programas_dict.get(programa_codigo).id if programa_codigo in programas_dict else None,
                    idTipoCambio=id_tipo_cambio,
                    montoPropuesto=monto,
                    etapaVentaPropuesta=etapaDeVentas,
                    posibleAtipico=posibleAtipico
                )
                oportunidades_bulk.append(oportunidad)
                oportunidades_dict[oportunidad_nombre] = oportunidad
            # Print cada 1000 filas para monitorear avance
        except Exception as e:
            return
            print(f"[ERROR] Oportunidad fila {idx}: {e}\nDatos: {row.to_dict()}")
            db.rollback()
    if oportunidades_bulk:
        try:
            db.bulk_save_objects(oportunidades_bulk)
            db.commit()
        except Exception as e:
            return
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

def crear_solicitudes_aprobacion(db, propuesta_unica):
    subdirector_role = db.query(Rol).filter(Rol.nombre == "Comercial - Subdirector").first()
    daf_subdirector_role = db.query(Rol).filter(Rol.nombre == "DAF - Subdirector").first()
    subdirectores_comerciales = []
    if subdirector_role:
        subdirectores_comerciales = db.query(Usuario).filter(Usuario.roles.any(Rol.id == subdirector_role.id)).all()
    if subdirectores_comerciales:
        if not daf_subdirector_role:
            raise HTTPException(status_code=404, detail="No se encontró el rol 'DAF - Subdirector'")
        daf_subdirector = db.query(Usuario).filter(Usuario.roles.any(Rol.id == daf_subdirector_role.id)).first()
        if not daf_subdirector:
            raise HTTPException(status_code=404, detail="No se encontró un usuario con rol 'DAF - Subdirector'")
        # Get TipoSolicitud instance for "APROBACION_COMERCIAL"
        tipo_aprobacion = db.query(TipoSolicitud).filter_by(nombre="APROBACION_COMERCIAL").first()
        if not tipo_aprobacion:
            raise HTTPException(status_code=404, detail="No se encontró el tipo de solicitud 'APROBACION_COMERCIAL'")
        from fastapi_app.models.solicitud_x_programa import SolicitudXPrograma
        programas = db.query(Programa).filter(Programa.idPropuesta == propuesta_unica.id).all()
        solicitudes_bulk = []
        solicitudes_x_programa_bulk = []
        for subdirector in subdirectores_comerciales:
            solicitud_existente = db.query(Solicitud).filter(
                Solicitud.idUsuarioGenerador == subdirector.id,
                Solicitud.tipoSolicitud_id == tipo_aprobacion.id
            ).first()
            if solicitud_existente:
                continue
            comentario = (
                f"{subdirector.nombre} confirma, en calidad de Subdirector Comercial, "
                "que su cartera ha sido conciliada con los Jefes de Producto."
            )
            nueva_solicitud = Solicitud(
                idUsuarioGenerador=subdirector.id,
                idUsuarioReceptor=daf_subdirector.id,
                tipoSolicitud_id=tipo_aprobacion.id,
                valorSolicitud_id=None,  # Set correct valorSolicitud_id if needed
                comentario=comentario,
                creadoEn=datetime.datetime.now(),
                abierta=True
            )
            solicitudes_bulk.append(nueva_solicitud)
        if solicitudes_bulk:
            db.bulk_save_objects(solicitudes_bulk)
            db.flush()
            # Ahora que tienen id, crear SolicitudXPrograma en bulk
            for nueva_solicitud in solicitudes_bulk:
                for programa in programas:
                    solicitud_programa = SolicitudXPrograma(
                        idPrograma=programa.id,
                        idSolicitud=nueva_solicitud.id
                    )
                    solicitudes_x_programa_bulk.append(solicitud_programa)
            if solicitudes_x_programa_bulk:
                db.bulk_save_objects(solicitudes_x_programa_bulk)
                db.flush()

# Agrupa la carga de CSV, carteras, usuarios y propuesta
def cargar_datos_base(db, data):
    df = cargar_csv(data)
    carteras_dict = cargar_carteras(db, df)
    usuarios_dict = cargar_usuarios(db, df, carteras_dict)
    propuesta_unica = cargar_propuesta(db, data)
    return df, usuarios_dict, propuesta_unica
# Helper function for CSV loading
def cargar_csv(data):
    csv_url = data.get("csv_url") if isinstance(data, dict) else None
    if not csv_url:
        raise HTTPException(status_code=400, detail="No se proporcionó 'csv_url' para procesar el archivo de conciliación")
    try:
        df = pd.read_csv(csv_url, decimal=',')
    except Exception as csv_error:
        raise HTTPException(status_code=400, detail=f"No se pudo leer el CSV desde la URL proporcionada: {csv_error}")
    if df is None or df.empty:
        raise HTTPException(status_code=400, detail="El archivo CSV no contiene registros para procesar")
    df = df.copy()
    df.columns = df.columns.str.strip()
    return df



def process_csv_data_v2(db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
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

        # 4. Cargar oportunidades
        start = time.time()
        cargar_oportunidades(db, df, propuesta_unica, programas_dict)
        timings['cargar_oportunidades'] = time.time() - start
        print(f"Tiempo cargar_oportunidades: {timings['cargar_oportunidades']:.4f} segundos")

        # 5. Crear solicitudes de aprobación
        start = time.time()
        crear_solicitudes_aprobacion(db, propuesta_unica)
        timings['crear_solicitudes_aprobacion'] = time.time() - start
        print(f"Tiempo crear_solicitudes_aprobacion: {timings['crear_solicitudes_aprobacion']:.4f} segundos")

        # 6. Commit final para guardar todo lo demás
        db.commit()
        total_time = time.time() - total_start
        print(f"Tiempo total de ejecución: {total_time:.4f} segundos")
        return {
            "status": "success",
            "message": "CSV procesado con éxito",
            "propuesta_id": propuesta_unica.id,
            "propuesta_nombre": propuesta_unica.nombre,
            "timings": timings,
            "total_time": total_time
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error general en process_csv_data_v2: {str(e)}")
