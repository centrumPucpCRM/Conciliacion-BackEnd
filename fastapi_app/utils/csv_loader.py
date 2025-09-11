import csv
import io
import pandas as pd
import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from ..models.usuario import Usuario
from ..models.cartera import Cartera
from ..models.programa import Programa
from ..models.oportunidad import Oportunidad
from ..models.propuesta import Propuesta
from ..models.tipo_cambio import TipoCambio
from ..models.propuesta_oportunidad import PropuestaOportunidad
from ..models.propuesta_programa import PropuestaPrograma

async def process_csv_data(db: Session, data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Procesa datos CSV de conciliación ya convertidos a formato JSON y crea los registros
    correspondientes en la base de datos.
    """
    try:
        df = pd.DataFrame(data)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Error al procesar los datos: {str(e)}")
    
    # Eliminar espacios en blanco de los nombres de columnas
    df.columns = df.columns.str.strip()
    
    # Reemplazar nombres de columnas para manejar posibles inconsistencias
    columns_mapping = {
        'usuario.nombre': 'usuario.nombre',
        'cartera.nombre': 'cartera.nombre',
        'programa.codigo': 'programa.codigo',
        'programa.nombre': 'programa.nombre',
        'progrma.fecha_de_inicio': 'programa.fecha_de_inicio',  # Corregir typo en el CSV
        'programa.fecha_de_inicio': 'programa.fecha_de_inicio',
        'programa.fecha_de_inauguracion': 'programa.fecha_de_inauguracion',
        'programa.fecha_ultima_postulante': 'programa.fecha_ultima_postulante',
        'programa.moneda': 'programa.moneda',
        'programa.precio_lista': 'programa.precio_lista',
        'oportunidad.nombre': 'oportunidad.nombre',
        'oportunidad.documento_identidad': 'oportunidad.documento_identidad',
        'oportunidad.correo': 'oportunidad.correo',
        'oportunidad.telefono': 'oportunidad.telefono',
        'oportunidad.etapa_venta': 'oportunidad.etapa_venta',
        'oportunidad.descuento': 'oportunidad.descuento',
        'oportunidad.moneda': 'oportunidad.moneda',
        'oportunidad.monto': 'oportunidad.monto'
    }
    df = df.rename(columns={col: columns_mapping.get(col, col) for col in df.columns})
    date_columns = [
        'programa.fecha_de_inicio',
        'programa.fecha_de_inauguracion',
        'programa.fecha_ultima_postulante'
    ]
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce', format='%d/%m/%Y')

    # 1. Crear propuesta única
    now = datetime.datetime.now()
    propuesta_nombre = f"Propuesta_{now.strftime('%Y%m%d_%H%M%S')}"
    propuesta_unica = Propuesta(
        nombre=propuesta_nombre,
        descripcion="Propuesta generada automáticamente desde archivo CSV",
        tipo_propuesta="CREACION",
        estado_propuesta="GENERADA",
        creado_en=now
    )
    db.add(propuesta_unica)
    db.flush()

    # 2. Eliminar usuarios con rol 1
    usuarios_rol1 = db.query(Usuario).filter(Usuario.id_rol == 1).all()
    for usuario in usuarios_rol1:
        db.delete(usuario)
    db.flush()

    # 3. Crear carteras únicas
    carteras_dict = {}
    if 'cartera.nombre' in df.columns:
        for cartera_nombre in df['cartera.nombre'].dropna().unique():
            cartera_nombre = cartera_nombre.strip()
            cartera = db.query(Cartera).filter(Cartera.nombre == cartera_nombre).first()
            if not cartera:
                cartera = Cartera(nombre=cartera_nombre)
                db.add(cartera)
                db.flush()
            carteras_dict[cartera_nombre] = cartera

    # 4. Crear usuarios únicos con id_rol=1 y mapeo a carteras
    from ..models.rol_permiso import Rol
    rol = db.query(Rol).filter(Rol.id_rol == 1).first()
    if not rol:
        rol = db.query(Rol).filter(Rol.nombre == "Administrador").first()
    if not rol:
        raise HTTPException(status_code=404, detail="No se encontró un rol adecuado para los usuarios")
    usuarios_dict = {}
    usuario_carteras_map = {}
    for _, row in df.iterrows():
        if pd.notna(row.get('usuario.nombre')) and pd.notna(row.get('cartera.nombre')):
            usuario_nombre = row['usuario.nombre'].strip()
            cartera_nombre = row['cartera.nombre'].strip()
            if usuario_nombre not in usuario_carteras_map:
                usuario_carteras_map[usuario_nombre] = set()
            usuario_carteras_map[usuario_nombre].add(cartera_nombre)
    for usuario_nombre, cartera_nombres in usuario_carteras_map.items():
        usuario = db.query(Usuario).filter(Usuario.nombres == usuario_nombre).first()
        if not usuario:
            usuario = Usuario(
                nombres=usuario_nombre,
                dni=f"USR{len(usuarios_dict) + 1}",
                correo=f"{usuario_nombre.lower().replace(' ', '.')}@ejemplo.com",
                celular="999999999",
                id_rol=rol.id_rol
            )
            db.add(usuario)
            db.flush()
        usuarios_dict[usuario_nombre] = usuario
        for cartera_nombre in cartera_nombres:
            cartera = carteras_dict.get(cartera_nombre)
            if cartera and cartera not in usuario.carteras:
                usuario.carteras.append(cartera)

    # 5. Crear programas únicos
    programas_dict = {}
    if 'programa.codigo' in df.columns:
        # Función para convertir string con coma o punto a float (debe estar disponible antes de uso)
        def parse_float(val):
            if pd.isna(val):
                return 0.0
            if isinstance(val, float) or isinstance(val, int):
                return float(val)
            if isinstance(val, str):
                return float(val.replace(',', '.'))
            return 0.0

        for _, row in df.iterrows():
            if pd.notna(row.get('programa.codigo')):
                programa_codigo = str(row['programa.codigo']).strip()
                if programa_codigo not in programas_dict:
                    # Buscar el usuario (jefe de producto) asociado a esta fila
                    usuario_nombre = str(row.get('usuario.nombre', '')).strip() if pd.notna(row.get('usuario.nombre')) else ''
                    usuario_jp = usuarios_dict.get(usuario_nombre)
                    id_jefe_producto = usuario_jp.id_usuario if usuario_jp else 1  # Valor predeterminado en caso de no encontrar usuario
                    programa_data = {
                        'codigo': programa_codigo,
                        'nombre': str(row.get('programa.nombre', 'Programa')).strip() if pd.notna(row.get('programa.nombre')) else f"Programa {programa_codigo}",
                        'moneda': str(row.get('programa.moneda', 'PEN')).strip() if pd.notna(row.get('programa.moneda')) else 'PEN',
                        'precio_lista': parse_float(row.get('programa.precio_lista', 0)) if pd.notna(row.get('programa.precio_lista')) else 0,
                        'id_propuesta': propuesta_unica.id_propuesta,
                        'id_jefe_producto': id_jefe_producto
                    }
                    # Asociar cartera si existe en la fila
                    if pd.notna(row.get('cartera.nombre')):
                        programa_data['cartera'] = str(row.get('cartera.nombre')).strip()
                    else:
                        programa_data['cartera'] = None
                    try:
                        programa_data['fecha_de_inicio'] = row.get('programa.fecha_de_inicio').date() if pd.notna(row.get('programa.fecha_de_inicio')) else datetime.date.today()
                    except:
                        programa_data['fecha_de_inicio'] = datetime.date.today()
                    try:
                        programa_data['fecha_de_inauguracion'] = row.get('programa.fecha_de_inauguracion').date() if pd.notna(row.get('programa.fecha_de_inauguracion')) else datetime.date.today()
                    except:
                        programa_data['fecha_de_inauguracion'] = datetime.date.today()
                    try:
                        programa_data['fecha_ultima_postulante'] = row.get('programa.fecha_ultima_postulante').date() if pd.notna(row.get('programa.fecha_ultima_postulante')) else None
                    except:
                        programa_data['fecha_ultima_postulante'] = None
                    programa = Programa(**programa_data)
                    db.add(programa)
                    db.flush()
                    programas_dict[programa_codigo] = programa


    # 6. Crear tipos de cambio únicos para monedas encontradas
    today = datetime.date.today()
    tipo_cambios = {}
    # Siempre crear tipo de cambio para PEN->PEN
    tipo_cambio_pen = db.query(TipoCambio).filter(
        TipoCambio.moneda_origen == 'PEN',
        TipoCambio.moneda_target == 'PEN',
        TipoCambio.fecha_tipo_cambio == today
    ).first()
    if not tipo_cambio_pen:
        tipo_cambio_pen = TipoCambio(
            moneda_origen='PEN',
            moneda_target='PEN',
            equivalencia=1.0,
            fecha_tipo_cambio=today,
            creado_en=datetime.datetime.now()
        )
        db.add(tipo_cambio_pen)
        db.flush()
    tipo_cambios['PEN'] = tipo_cambio_pen

    # Siempre crear tipo de cambio para USD->PEN
    tipo_cambio_usd = db.query(TipoCambio).filter(
        TipoCambio.moneda_origen == 'USD',
        TipoCambio.moneda_target == 'PEN',
        TipoCambio.fecha_tipo_cambio == today
    ).first()
    if not tipo_cambio_usd:
        tipo_cambio_usd = TipoCambio(
            moneda_origen='USD',
            moneda_target='PEN',
            equivalencia=3.75,
            fecha_tipo_cambio=today,
            creado_en=datetime.datetime.now()
        )
        db.add(tipo_cambio_usd)
        db.flush()
    tipo_cambios['USD'] = tipo_cambio_usd

    # Siempre crear tipo de cambio para EUR->PEN
    tipo_cambio_eur = db.query(TipoCambio).filter(
        TipoCambio.moneda_origen == 'EUR',
        TipoCambio.moneda_target == 'PEN',
        TipoCambio.fecha_tipo_cambio == today
    ).first()
    if not tipo_cambio_eur:
        tipo_cambio_eur = TipoCambio(
            moneda_origen='EUR',
            moneda_target='PEN',
            equivalencia=4.10,
            fecha_tipo_cambio=today,
            creado_en=datetime.datetime.now()
        )
        db.add(tipo_cambio_eur)
        db.flush()
    tipo_cambios['EUR'] = tipo_cambio_eur

    # 6.1 Crear PropuestaPrograma para cada programa único y la propuesta única
    for programa_codigo, programa in programas_dict.items():
        propuesta_programa_existente = db.query(PropuestaPrograma).filter(
            PropuestaPrograma.id_propuesta == propuesta_unica.id_propuesta,
            PropuestaPrograma.id_programa == programa.id_programa
        ).first()
        if not propuesta_programa_existente:
            propuesta_programa = PropuestaPrograma(
                id_propuesta=propuesta_unica.id_propuesta,
                id_programa=programa.id_programa
            )
            db.add(propuesta_programa)
    db.flush()


    # 7. Crear oportunidades y vincularlas a la propuesta única
    for _, row in df.iterrows():
        if pd.notna(row.get('oportunidad.nombre')) and pd.notna(row.get('programa.codigo')):
            oportunidad_nombre = str(row['oportunidad.nombre']).strip()
            programa_codigo = str(row['programa.codigo']).strip()
            programa = programas_dict.get(programa_codigo)
            if not programa:
                continue
            descuento = parse_float(row.get('oportunidad.descuento', 0)) if pd.notna(row.get('oportunidad.descuento')) else 0.0
            def es_atipico(desc, monto=None, precio_lista=None):
                # Verificar si el descuento es atípico
                if not isinstance(desc, float):
                    return False
                if desc < 0 or desc > 1:
                    return True
                decimales = str(desc).split('.')
                if len(decimales) == 2:
                    dec = decimales[1].ljust(4, '0')
                    if dec[2] != '0' or dec[3] != '0':
                        return True
                
                # Verificar si la división monto/precio_lista es atípica
                if monto is not None and precio_lista is not None and precio_lista != 0:
                    ratio = monto / precio_lista
                    ratio_decimales = str(ratio).split('.')
                    if len(ratio_decimales) == 2:
                        ratio_dec = ratio_decimales[1].ljust(4, '0')
                        if ratio_dec[2] != '0' or ratio_dec[3] != '0':
                            return True
                
                return False
            oportunidad_data = {
                'nombre': oportunidad_nombre,
                'documento_identidad': str(row.get('oportunidad.documento_identidad', '')).strip() if pd.notna(row.get('oportunidad.documento_identidad')) else '',
                'correo': str(row.get('oportunidad.correo', '')).strip() if pd.notna(row.get('oportunidad.correo')) else '',
                'telefono': str(row.get('oportunidad.telefono', '')).strip() if pd.notna(row.get('oportunidad.telefono')) else '',
                'etapa_venta': str(row.get('oportunidad.etapa_venta', 'NUEVA')).strip() if pd.notna(row.get('oportunidad.etapa_venta')) else 'NUEVA',
                'descuento': descuento,
                'moneda': str(row.get('oportunidad.moneda', 'PEN')).strip() if pd.notna(row.get('oportunidad.moneda')) else 'PEN',
                'monto': parse_float(row.get('oportunidad.monto', 0)) if pd.notna(row.get('oportunidad.monto')) else 0.0,
                'becado': bool(row.get('oportunidad.becado', False)) if pd.notna(row.get('oportunidad.becado')) else False,
                'conciliado': bool(row.get('oportunidad.conciliado', False)) if pd.notna(row.get('oportunidad.conciliado')) else False,
                'posible_atipico': es_atipico(
                    descuento, 
                    parse_float(row.get('oportunidad.monto', 0)) if pd.notna(row.get('oportunidad.monto')) else 0.0,
                    programa.precio_lista if programa and programa.precio_lista else 0
                ),
                'id_programa': programa.id_programa,
            }
            oportunidad = Oportunidad(**oportunidad_data)
            db.add(oportunidad)
            db.flush()
            # Buscar el id_propuesta_programa correspondiente (ya debe existir)
            propuesta_programa = db.query(PropuestaPrograma).filter(
                PropuestaPrograma.id_propuesta == propuesta_unica.id_propuesta,
                PropuestaPrograma.id_programa == programa.id_programa
            ).first()
            id_propuesta_programa = propuesta_programa.id_propuesta_programa if propuesta_programa else None

            # Buscar el id_tipo_cambio correspondiente a la moneda de la oportunidad
            tipo_cambio = tipo_cambios.get(oportunidad_data['moneda'])
            id_tipo_cambio = tipo_cambio.id_tipo_cambio if tipo_cambio else None

            # El monto propuesto es el monto de la oportunidad
            monto_propuesto = oportunidad.monto

            propuesta_oportunidad = PropuestaOportunidad(
                id_propuesta=propuesta_unica.id_propuesta,
                id_oportunidad=oportunidad.id_oportunidad,
                id_propuesta_programa=id_propuesta_programa,
                id_tipo_cambio=id_tipo_cambio,
                monto_propuesto=monto_propuesto,
                etapa_venta_propuesto=oportunidad.etapa_venta
            )
            db.add(propuesta_oportunidad)

    db.commit()
    return {
        "status": "success",
        "message": "CSV procesado con éxito",
        "propuesta_id": propuesta_unica.id_propuesta,
        "propuesta_nombre": propuesta_unica.nombre
    }