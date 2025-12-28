from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from models import db, Cliente, Coche, Intervencion, Factura
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu-clave-secreta-aqui-cambiar-en-produccion'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///taller.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Inicializar base de datos
with app.app_context():
    db.create_all()
    
    # Migración: añadir columna cliente_id a coches si no existe
    try:
        from sqlalchemy import text, inspect
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('coches')]
        
        if 'cliente_id' not in columns:
            with db.engine.begin() as conn:
                conn.execute(text('ALTER TABLE coches ADD COLUMN cliente_id INTEGER'))
                conn.execute(text('CREATE INDEX IF NOT EXISTS ix_coches_cliente_id ON coches(cliente_id)'))
            print("Migración: columna cliente_id añadida a la tabla coches")
    except Exception as e:
        # Si la tabla no existe o hay otro error, lo ignoramos (db.create_all() lo manejará)
        if 'no such table' not in str(e).lower():
            print(f"Error en migración (puede ser normal si la columna ya existe): {e}")
    
    # Migración: añadir columnas de IVA y descuento a facturas si no existen
    try:
        from sqlalchemy import text, inspect
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('facturas')]
        
        columnas_añadidas = False
        with db.engine.begin() as conn:
            if 'base_imponible' not in columns:
                conn.execute(text('ALTER TABLE facturas ADD COLUMN base_imponible FLOAT DEFAULT 0.0'))
                print("Migración: columna base_imponible añadida a la tabla facturas")
                columnas_añadidas = True
            
            if 'descuento_porcentaje' not in columns:
                conn.execute(text('ALTER TABLE facturas ADD COLUMN descuento_porcentaje FLOAT DEFAULT 0.0'))
                print("Migración: columna descuento_porcentaje añadida a la tabla facturas")
                columnas_añadidas = True
            
            if 'descuento_importe' not in columns:
                conn.execute(text('ALTER TABLE facturas ADD COLUMN descuento_importe FLOAT DEFAULT 0.0'))
                print("Migración: columna descuento_importe añadida a la tabla facturas")
                columnas_añadidas = True
            
            if 'iva_porcentaje' not in columns:
                conn.execute(text('ALTER TABLE facturas ADD COLUMN iva_porcentaje FLOAT DEFAULT 21.0'))
                print("Migración: columna iva_porcentaje añadida a la tabla facturas")
                columnas_añadidas = True
            
            if 'iva_importe' not in columns:
                conn.execute(text('ALTER TABLE facturas ADD COLUMN iva_importe FLOAT DEFAULT 0.0'))
                print("Migración: columna iva_importe añadida a la tabla facturas")
                columnas_añadidas = True
        
        # Actualizar facturas existentes si se añadieron columnas
        if columnas_añadidas:
            facturas = Factura.query.all()
            for factura in facturas:
                # Calcular base imponible desde las intervenciones
                base_imponible = sum(interv.precio for interv in factura.intervenciones)
                factura.base_imponible = base_imponible
                
                # Si no tiene IVA configurado, usar 21% por defecto
                if factura.iva_porcentaje is None or factura.iva_porcentaje == 0:
                    factura.iva_porcentaje = 21.0
                
                # Calcular descuento
                descuento_importe = base_imponible * (factura.descuento_porcentaje / 100) if factura.descuento_porcentaje else 0.0
                factura.descuento_importe = descuento_importe
                
                # Base después de descuento
                base_despues_descuento = base_imponible - descuento_importe
                
                # Calcular IVA
                iva_importe = base_despues_descuento * (factura.iva_porcentaje / 100)
                factura.iva_importe = iva_importe
                
                # Actualizar total
                nuevo_total = base_despues_descuento + iva_importe
                factura.total = nuevo_total
            
            db.session.commit()
            print("Migración: facturas existentes actualizadas con IVA y descuento")
    except Exception as e:
        # Si la tabla no existe o hay otro error, lo ignoramos
        if 'no such table' not in str(e).lower():
            print(f"Error en migración de facturas (puede ser normal si las columnas ya existen): {e}")

# ========== RUTAS PRINCIPALES ==========

@app.route('/')
def index():
    return render_template('index.html')

# ========== RUTAS DE CLIENTES ==========

@app.route('/clientes')
def listar_clientes():
    clientes = Cliente.query.order_by(Cliente.nombre).all()
    return render_template('clientes/listar.html', clientes=clientes)

@app.route('/clientes/nuevo', methods=['GET', 'POST'])
def nuevo_cliente():
    if request.method == 'POST':
        cliente = Cliente(
            nombre=request.form['nombre'],
            dni=request.form.get('dni') or None,
            telefono=request.form.get('telefono') or None,
            email=request.form.get('email') or None,
            direccion=request.form.get('direccion') or None,
            codigo_postal=request.form.get('codigo_postal') or None,
            poblacion=request.form.get('poblacion') or None,
            provincia=request.form.get('provincia') or None
        )
        try:
            db.session.add(cliente)
            db.session.commit()
            flash('Cliente registrado correctamente', 'success')
            return redirect(url_for('listar_clientes'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar cliente: {str(e)}', 'error')
    
    return render_template('clientes/nuevo.html')

@app.route('/clientes/nuevo/ajax', methods=['POST'])
def nuevo_cliente_ajax():
    """Ruta AJAX para crear cliente desde modal"""
    try:
        cliente = Cliente(
            nombre=request.form['nombre'],
            dni=request.form.get('dni') or None,
            telefono=request.form.get('telefono') or None,
            email=request.form.get('email') or None,
            direccion=request.form.get('direccion') or None,
            codigo_postal=request.form.get('codigo_postal') or None,
            poblacion=request.form.get('poblacion') or None,
            provincia=request.form.get('provincia') or None
        )
        db.session.add(cliente)
        db.session.commit()
        return jsonify({'success': True, 'cliente_id': cliente.id, 'nombre': cliente.nombre, 'dni': cliente.dni})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/clientes/<int:id>/editar', methods=['GET', 'POST'])
def editar_cliente(id):
    cliente = Cliente.query.get_or_404(id)
    
    if request.method == 'POST':
        cliente.nombre = request.form['nombre']
        cliente.dni = request.form.get('dni') or None
        cliente.telefono = request.form.get('telefono') or None
        cliente.email = request.form.get('email') or None
        cliente.direccion = request.form.get('direccion') or None
        cliente.codigo_postal = request.form.get('codigo_postal') or None
        cliente.poblacion = request.form.get('poblacion') or None
        cliente.provincia = request.form.get('provincia') or None
        
        try:
            db.session.commit()
            flash('Cliente actualizado correctamente', 'success')
            return redirect(url_for('listar_clientes'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar cliente: {str(e)}', 'error')
    
    return render_template('clientes/editar.html', cliente=cliente)

@app.route('/clientes/<int:id>/eliminar', methods=['POST'])
def eliminar_cliente(id):
    cliente = Cliente.query.get_or_404(id)
    try:
        db.session.delete(cliente)
        db.session.commit()
        flash('Cliente eliminado correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar cliente: {str(e)}', 'error')
    
    return redirect(url_for('listar_clientes'))

# ========== RUTAS DE VEHÍCULOS ==========

@app.route('/coches')
def listar_coches():
    from sqlalchemy.orm import joinedload
    coches = Coche.query.options(joinedload(Coche.cliente)).order_by(Coche.matricula).all()
    return render_template('vehiculos/listar.html', coches=coches)

@app.route('/coches/nuevo', methods=['GET', 'POST'])
def nuevo_coche():
    if request.method == 'POST':
        cliente_id = request.form.get('cliente_id')
        cliente_id = int(cliente_id) if cliente_id else None
        
        coche = Coche(
            matricula=request.form['matricula'].upper(),
            marca=request.form.get('marca') or None,
            modelo=request.form.get('modelo') or None,
            tipo=request.form.get('tipo') or None,
            año=int(request.form['año']) if request.form.get('año') else None,
            color=request.form.get('color') or None,
            cliente_id=cliente_id
        )
        try:
            db.session.add(coche)
            db.session.commit()
            flash('Vehículo registrado correctamente', 'success')
            return redirect(url_for('listar_coches'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar vehículo: {str(e)}', 'error')
    
    clientes = Cliente.query.order_by(Cliente.nombre).all()
    return render_template('vehiculos/nuevo.html', clientes=clientes)

@app.route('/coches/nuevo/ajax', methods=['POST'])
def nuevo_coche_ajax():
    """Ruta AJAX para crear vehículo desde modal"""
    try:
        cliente_id = request.form.get('cliente_id')
        cliente_id = int(cliente_id) if cliente_id else None
        
        coche = Coche(
            matricula=request.form['matricula'].upper(),
            marca=request.form.get('marca') or None,
            modelo=request.form.get('modelo') or None,
            tipo=request.form.get('tipo') or None,
            año=int(request.form['año']) if request.form.get('año') else None,
            color=request.form.get('color') or None,
            cliente_id=cliente_id
        )
        db.session.add(coche)
        db.session.commit()
        return jsonify({'success': True, 'vehiculo_id': coche.id, 'matricula': coche.matricula})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/coches/<int:id>/editar', methods=['GET', 'POST'])
def editar_coche(id):
    coche = Coche.query.get_or_404(id)
    
    if request.method == 'POST':
        coche.matricula = request.form['matricula'].upper()
        coche.marca = request.form.get('marca') or None
        coche.modelo = request.form.get('modelo') or None
        coche.tipo = request.form.get('tipo') or None
        coche.año = int(request.form['año']) if request.form.get('año') else None
        coche.color = request.form.get('color') or None
        
        cliente_id = request.form.get('cliente_id')
        coche.cliente_id = int(cliente_id) if cliente_id else None
        
        try:
            db.session.commit()
            flash('Vehículo actualizado correctamente', 'success')
            return redirect(url_for('listar_coches'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar vehículo: {str(e)}', 'error')
    
    clientes = Cliente.query.order_by(Cliente.nombre).all()
    return render_template('vehiculos/editar.html', coche=coche, clientes=clientes)

@app.route('/coches/<int:id>/eliminar', methods=['POST'])
def eliminar_coche(id):
    coche = Coche.query.get_or_404(id)
    try:
        db.session.delete(coche)
        db.session.commit()
        flash('Vehículo eliminado correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar vehículo: {str(e)}', 'error')
    
    return redirect(url_for('listar_coches'))

@app.route('/coches/<int:id>/ficha')
def ficha_coche(id):
    coche = Coche.query.get_or_404(id)
    intervenciones = Intervencion.query.filter_by(coche_id=id).order_by(Intervencion.fecha.desc()).all()
    return render_template('vehiculos/ficha.html', coche=coche, intervenciones=intervenciones)

# ========== RUTAS DE INTERVENCIONES ==========

@app.route('/intervenciones')
def listar_intervenciones():
    from sqlalchemy.orm import joinedload
    intervenciones = Intervencion.query.options(
        joinedload(Intervencion.coche),
        joinedload(Intervencion.cliente)
    ).order_by(Intervencion.fecha.desc()).all()
    return render_template('intervenciones/listar.html', intervenciones=intervenciones)

@app.route('/intervenciones/nueva/vehiculo')
def seleccionar_vehiculo_intervencion():
    """Página para seleccionar vehículo antes de crear intervención"""
    from sqlalchemy.orm import joinedload
    vehiculos = Coche.query.options(joinedload(Coche.cliente)).order_by(Coche.matricula).all()
    return render_template('intervenciones/seleccionar_vehiculo.html', vehiculos=vehiculos)

@app.route('/intervenciones/nueva', methods=['GET', 'POST'])
def nueva_intervencion():
    """Crear nueva intervención con selector de vehículo"""
    if request.method == 'POST':
        coche_id = int(request.form['coche_id']) if request.form.get('coche_id') else None
        if not coche_id:
            flash('Debe seleccionar un vehículo', 'error')
            vehiculos = Coche.query.order_by(Coche.matricula).all()
            clientes = Cliente.query.order_by(Cliente.nombre).all()
            return render_template('intervenciones/nueva.html', vehiculos=vehiculos, clientes=clientes, coche=None)
        
        fecha = datetime.strptime(request.form['fecha'], '%Y-%m-%d')
        km = int(request.form['km']) if request.form.get('km') else None
        
        # Obtener todas las líneas de intervención
        descripciones = request.form.getlist('descripcion[]')
        precios = request.form.getlist('precio[]')
        horas = request.form.getlist('horas_trabajo[]')
        
        if not descripciones or not any(descripciones):
            flash('Debe añadir al menos una línea de intervención', 'error')
            vehiculos = Coche.query.order_by(Coche.matricula).all()
            clientes = Cliente.query.order_by(Cliente.nombre).all()
            coche = Coche.query.get(coche_id)
            return render_template('intervenciones/nueva.html', vehiculos=vehiculos, clientes=clientes, coche=coche)
        
        cliente_id = int(request.form['cliente_id']) if request.form.get('cliente_id') else None
        
        intervenciones_creadas = 0
        try:
            for i in range(len(descripciones)):
                if descripciones[i].strip():  # Solo crear si hay descripción
                    intervencion = Intervencion(
                        coche_id=coche_id,
                        cliente_id=cliente_id,
                        fecha=fecha,
                        km=km,
                        descripcion=descripciones[i].strip(),
                        precio=float(precios[i].replace(',', '.')) if precios[i] and precios[i].strip() else 0.0,
                        horas_trabajo=float(horas[i].replace(',', '.')) if horas[i] and horas[i].strip() else 0.0
                    )
                    db.session.add(intervencion)
                    intervenciones_creadas += 1
            
            db.session.commit()
            flash(f'{intervenciones_creadas} intervención(es) registrada(s) correctamente', 'success')
            return redirect(url_for('listar_intervenciones'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar intervención: {str(e)}', 'error')
    
    vehiculos = Coche.query.order_by(Coche.matricula).all()
    clientes = Cliente.query.order_by(Cliente.nombre).all()
    return render_template('intervenciones/nueva.html', vehiculos=vehiculos, clientes=clientes, coche=None)

@app.route('/coches/<int:coche_id>/intervenciones/nueva', methods=['GET', 'POST'])
def nueva_intervencion_vehiculo(coche_id):
    """Crear nueva intervención para un vehículo específico (mantener compatibilidad)"""
    coche = Coche.query.get_or_404(coche_id)
    
    if request.method == 'POST':
        fecha = datetime.strptime(request.form['fecha'], '%Y-%m-%d')
        km = int(request.form['km']) if request.form.get('km') else None
        
        # Obtener todas las líneas de intervención
        descripciones = request.form.getlist('descripcion[]')
        precios = request.form.getlist('precio[]')
        horas = request.form.getlist('horas_trabajo[]')
        
        if not descripciones or not any(descripciones):
            flash('Debe añadir al menos una línea de intervención', 'error')
            clientes = Cliente.query.order_by(Cliente.nombre).all()
            vehiculos = Coche.query.order_by(Coche.matricula).all()
            return render_template('intervenciones/nueva.html', coche=coche, clientes=clientes, vehiculos=vehiculos)
        
        cliente_id = int(request.form['cliente_id']) if request.form.get('cliente_id') else None
        
        intervenciones_creadas = 0
        try:
            for i in range(len(descripciones)):
                if descripciones[i].strip():  # Solo crear si hay descripción
                    intervencion = Intervencion(
                        coche_id=coche_id,
                        cliente_id=cliente_id,
                        fecha=fecha,
                        km=km,
                        descripcion=descripciones[i].strip(),
                        precio=float(precios[i].replace(',', '.')) if precios[i] and precios[i].strip() else 0.0,
                        horas_trabajo=float(horas[i].replace(',', '.')) if horas[i] and horas[i].strip() else 0.0
                    )
                    db.session.add(intervencion)
                    intervenciones_creadas += 1
            
            db.session.commit()
            flash(f'{intervenciones_creadas} intervención(es) registrada(s) correctamente', 'success')
            return redirect(url_for('ficha_coche', id=coche_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar intervención: {str(e)}', 'error')
    
    clientes = Cliente.query.order_by(Cliente.nombre).all()
    vehiculos = Coche.query.order_by(Coche.matricula).all()
    return render_template('intervenciones/nueva.html', coche=coche, clientes=clientes, vehiculos=vehiculos)

@app.route('/intervenciones/<int:id>/editar', methods=['GET', 'POST'])
def editar_intervencion(id):
    intervencion = Intervencion.query.get_or_404(id)
    
    if request.method == 'POST':
        intervencion.fecha = datetime.strptime(request.form['fecha'], '%Y-%m-%d')
        intervencion.km = int(request.form['km']) if request.form.get('km') else None
        intervencion.cliente_id = int(request.form['cliente_id']) if request.form.get('cliente_id') else None
        intervencion.descripcion = request.form['descripcion']
        precio_str = request.form['precio'].replace(',', '.') if request.form.get('precio') else '0'
        horas_str = request.form.get('horas_trabajo', '0').replace(',', '.') if request.form.get('horas_trabajo') else '0'
        intervencion.precio = float(precio_str)
        intervencion.horas_trabajo = float(horas_str)
        
        try:
            db.session.commit()
            flash('Intervención actualizada correctamente', 'success')
            # Redirigir a la lista de intervenciones si viene de ahí, sino a la ficha del vehículo
            if request.referrer and 'intervenciones' in request.referrer:
                return redirect(url_for('listar_intervenciones'))
            return redirect(url_for('ficha_coche', id=intervencion.coche_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar intervención: {str(e)}', 'error')
    
    clientes = Cliente.query.order_by(Cliente.nombre).all()
    return render_template('intervenciones/editar.html', intervencion=intervencion, clientes=clientes)

@app.route('/intervenciones/<int:id>/eliminar', methods=['POST'])
def eliminar_intervencion(id):
    intervencion = Intervencion.query.get_or_404(id)
    coche_id = intervencion.coche_id
    
    # No permitir eliminar si está facturada
    if intervencion.factura_id:
        flash('No se puede eliminar una intervención que ya está facturada', 'error')
        return redirect(url_for('ficha_coche', id=coche_id))
    
    try:
        db.session.delete(intervencion)
        db.session.commit()
        flash('Intervención eliminada correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar intervención: {str(e)}', 'error')
    
    return redirect(url_for('ficha_coche', id=coche_id))

# ========== RUTAS DE FACTURAS ==========

@app.route('/facturas')
def listar_facturas():
    from sqlalchemy.orm import joinedload
    # Obtener intervenciones sin facturar
    intervenciones_sin_facturar = Intervencion.query.options(
        joinedload(Intervencion.coche),
        joinedload(Intervencion.cliente)
    ).filter_by(factura_id=None).order_by(Intervencion.fecha.desc()).all()
    
    # También obtener facturas para mostrar en otra sección
    facturas = Factura.query.order_by(Factura.fecha.desc()).all()
    
    return render_template('facturas/listar.html', 
                         intervenciones_sin_facturar=intervenciones_sin_facturar, 
                         facturas=facturas)

@app.route('/facturas/nueva', methods=['GET', 'POST'])
def nueva_factura():
    if request.method == 'POST':
        cliente_id = int(request.form['cliente_id'])
        
        # Obtener intervenciones existentes seleccionadas
        intervenciones_ids = [int(id) for id in request.form.getlist('intervenciones')]
        intervenciones_existentes = []
        if intervenciones_ids:
            intervenciones_existentes = Intervencion.query.filter(Intervencion.id.in_(intervenciones_ids)).all()
            # Verificar que no estén ya facturadas
            for interv in intervenciones_existentes:
                if interv.factura_id:
                    flash(f'La intervención {interv.id} ya está facturada', 'error')
                    return redirect(url_for('nueva_factura'))
        
        # Obtener nuevas intervenciones del modal (formato: nueva_intervencion_N_campo)
        nuevas_intervenciones_data = []
        import re
        
        # Agrupar por índice de línea
        lineas_dict = {}
        for key in request.form.keys():
            match = re.match(r'nueva_intervencion_(\d+)_(.+)', key)
            if match:
                linea_idx = int(match.group(1))
                campo = match.group(2)
                if linea_idx not in lineas_dict:
                    lineas_dict[linea_idx] = {}
                lineas_dict[linea_idx][campo] = request.form[key]
        
        # Procesar cada línea como una intervención independiente
        for idx in sorted(lineas_dict.keys()):
            linea_data = lineas_dict[idx]
            vehiculo_id = linea_data.get('vehiculo_id')
            fecha = linea_data.get('fecha')
            km = linea_data.get('km', '')
            cliente_id_interv = linea_data.get('cliente_id', '')
            descripcion = linea_data.get('descripcion', '')
            precio = linea_data.get('precio', '').strip()
            horas = linea_data.get('horas_trabajo', '0').strip()
            
            if vehiculo_id and fecha and descripcion and precio:
                try:
                    precio_float = float(precio.replace(',', '.')) if precio else 0.0
                    horas_float = float(horas.replace(',', '.')) if horas else 0.0
                except (ValueError, AttributeError):
                    precio_float = 0.0
                    horas_float = 0.0
                
                nuevas_intervenciones_data.append({
                    'vehiculo_id': int(vehiculo_id),
                    'fecha': fecha,
                    'km': int(km) if km and km.strip() else None,
                    'cliente_id': int(cliente_id_interv) if cliente_id_interv and cliente_id_interv.strip() else None,
                    'descripcion': descripcion.strip(),
                    'precio': precio_float,
                    'horas_trabajo': horas_float
                })
        
        # Validar que haya al menos una intervención nueva o una existente
        if not intervenciones_existentes and len(nuevas_intervenciones_data) == 0:
            flash('Debe añadir al menos una intervención o seleccionar una intervención existente', 'error')
            return redirect(url_for('nueva_factura'))
        
        # Obtener descuento e IVA del formulario
        descuento_porcentaje = float(request.form.get('descuento_porcentaje', '0').replace(',', '.')) if request.form.get('descuento_porcentaje') else 0.0
        iva_porcentaje = float(request.form.get('iva_porcentaje', '21').replace(',', '.')) if request.form.get('iva_porcentaje') else 21.0
        
        # Calcular base imponible inicial con intervenciones existentes
        base_imponible = sum(interv.precio for interv in intervenciones_existentes)
        
        # Generar número de factura
        ultima_factura = Factura.query.order_by(Factura.id.desc()).first()
        numero_factura = f"FAC-{datetime.now().year}-{ultima_factura.id + 1 if ultima_factura else 1:04d}"
        
        # Crear factura
        factura = Factura(
            cliente_id=cliente_id,
            numero_factura=numero_factura,
            base_imponible=0,  # Se actualizará después
            descuento_porcentaje=descuento_porcentaje,
            descuento_importe=0,  # Se calculará después
            iva_porcentaje=iva_porcentaje,
            iva_importe=0,  # Se calculará después
            total=0  # Se actualizará después
        )
        
        try:
            db.session.add(factura)
            db.session.flush()  # Para obtener el ID
            
            # Asociar intervenciones existentes
            for interv in intervenciones_existentes:
                interv.factura_id = factura.id
                base_imponible += interv.precio
            
            # Crear nuevas intervenciones desde el modal
            for interv_data in nuevas_intervenciones_data:
                fecha_interv = datetime.strptime(interv_data['fecha'], '%Y-%m-%d') if interv_data['fecha'] else datetime.utcnow()
                
                nueva_intervencion = Intervencion(
                    coche_id=interv_data['vehiculo_id'],
                    cliente_id=interv_data['cliente_id'],
                    fecha=fecha_interv,
                    km=interv_data['km'],
                    descripcion=interv_data['descripcion'],
                    precio=interv_data['precio'],
                    horas_trabajo=interv_data['horas_trabajo'],
                    factura_id=factura.id
                )
                db.session.add(nueva_intervencion)
                base_imponible += nueva_intervencion.precio
            
            # Calcular descuento
            descuento_importe = base_imponible * (descuento_porcentaje / 100)
            
            # Base después de descuento
            base_despues_descuento = base_imponible - descuento_importe
            
            # Calcular IVA sobre la base después de descuento
            iva_importe = base_despues_descuento * (iva_porcentaje / 100)
            
            # Total final
            total = base_despues_descuento + iva_importe
            
            # Actualizar valores de la factura
            factura.base_imponible = base_imponible
            factura.descuento_importe = descuento_importe
            factura.iva_importe = iva_importe
            factura.total = total
            
            db.session.commit()
            flash('Factura creada correctamente', 'success')
            return redirect(url_for('ver_factura', id=factura.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear factura: {str(e)}', 'error')
    
    # GET: mostrar formulario
    clientes = Cliente.query.order_by(Cliente.nombre).all()
    vehiculos = Coche.query.order_by(Coche.matricula).all()
    
    # Obtener intervenciones precargadas desde query string
    intervenciones_precargadas = []
    intervencion_id = request.args.get('intervencion_id', type=int)
    intervenciones_ids = request.args.get('intervenciones', '')
    
    if intervencion_id:
        # Una sola intervención
        interv = Intervencion.query.get(intervencion_id)
        if interv and not interv.factura_id:
            intervenciones_precargadas = [interv]
    elif intervenciones_ids:
        # Múltiples intervenciones separadas por comas
        ids_list = [int(id.strip()) for id in intervenciones_ids.split(',') if id.strip().isdigit()]
        if ids_list:
            intervenciones_precargadas = Intervencion.query.filter(
                Intervencion.id.in_(ids_list),
                Intervencion.factura_id == None
            ).all()
    
    # Preparar datos de intervenciones precargadas para JavaScript
    import json
    intervenciones_precargadas_json = []
    cliente_precargado_id = None
    
    if intervenciones_precargadas:
        # Obtener el cliente de la primera intervención (o el común si todas tienen el mismo)
        if len(intervenciones_precargadas) > 0:
            primera_interv = intervenciones_precargadas[0]
            cliente_precargado_id = primera_interv.cliente_id
            
            # Verificar si todas las intervenciones tienen el mismo cliente
            todos_mismo_cliente = all(
                interv.cliente_id == cliente_precargado_id 
                for interv in intervenciones_precargadas
            )
            
            # Si no todas tienen el mismo cliente, no precargar ninguno
            if not todos_mismo_cliente:
                cliente_precargado_id = None
        
        for interv in intervenciones_precargadas:
            intervenciones_precargadas_json.append({
                'id': interv.id,
                'vehiculo_id': interv.coche_id,
                'vehiculo_texto': interv.coche.matricula,
                'fecha': interv.fecha.strftime('%Y-%m-%d'),
                'km': interv.km,
                'cliente_id': interv.cliente_id,
                'cliente_texto': interv.cliente.nombre if interv.cliente else None,
                'descripcion': interv.descripcion,
                'precio': float(interv.precio),
                'horas_trabajo': float(interv.horas_trabajo)
            })
    
    return render_template('facturas/nueva.html', 
                         clientes=clientes, 
                         vehiculos=vehiculos, 
                         intervenciones_precargadas_json=json.dumps(intervenciones_precargadas_json),
                         cliente_precargado_id=cliente_precargado_id)

@app.route('/facturas/<int:id>')
def ver_factura(id):
    factura = Factura.query.get_or_404(id)
    return render_template('facturas/ver.html', factura=factura)

@app.route('/facturas/<int:id>/enviar_verifactu', methods=['POST'])
def enviar_verifactu(id):
    factura = Factura.query.get_or_404(id)
    
    if factura.enviada_verifactu:
        flash('Esta factura ya fue enviada a Verifactu', 'info')
        return redirect(url_for('ver_factura', id=id))
    
    # Llamar a la función de envío
    resultado = enviar_factura_verifactu(factura)
    
    if resultado['exito']:
        factura.enviada_verifactu = True
        factura.fecha_envio_verifactu = datetime.utcnow()
        db.session.commit()
        flash(f'Factura enviada a Verifactu: {resultado["mensaje"]}', 'success')
    else:
        flash(f'Error al enviar a Verifactu: {resultado["mensaje"]}', 'error')
    
    return redirect(url_for('ver_factura', id=id))

# ========== FUNCIÓN API VERIFACTU ==========

def enviar_factura_verifactu(factura):
    """
    Función para enviar facturas a Verifactu a través de su API.
    Esta función está preparada pero no implementada completamente.
    
    Args:
        factura: Objeto Factura de la base de datos
    
    Returns:
        dict: {'exito': bool, 'mensaje': str}
    """
    # TODO: Implementar la integración con la API de Verifactu
    # Necesitarás:
    # - URL de la API de Verifactu
    # - Credenciales (API key, token, etc.)
    # - Formato de datos requerido por Verifactu
    
    # Ejemplo de estructura (no funcional):
    """
    import requests
    
    api_url = "https://api.verifactu.es/facturas"  # URL ejemplo
    api_key = os.getenv('VERIFACTU_API_KEY')
    
    datos_factura = {
        'numero_factura': factura.numero_factura,
        'fecha': factura.fecha.isoformat(),
        'cliente': {
            'nombre': factura.cliente.nombre,
            'dni': factura.cliente.dni,
            'direccion': factura.cliente.direccion
        },
        'lineas': [
            {
                'descripcion': interv.descripcion,
                'precio': interv.precio,
                'fecha': interv.fecha.isoformat()
            }
            for interv in factura.intervenciones
        ],
        'total': factura.total
    }
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(api_url, json=datos_factura, headers=headers)
        response.raise_for_status()
        return {'exito': True, 'mensaje': 'Factura enviada correctamente'}
    except requests.exceptions.RequestException as e:
        return {'exito': False, 'mensaje': str(e)}
    """
    
    # Por ahora retorna un mensaje indicando que no está implementado
    return {
        'exito': False,
        'mensaje': 'Función de envío a Verifactu no implementada. Revisar documentación de la API de Verifactu para completar la integración.'
    }

# ========== DATOS DE PRUEBA ==========

def insertar_datos_prueba():
    """Función para insertar datos de prueba en la base de datos"""
    from random import choice, randint, uniform
    from datetime import timedelta
    
    try:
        # Verificar si ya hay datos
        if Cliente.query.count() > 0:
            print("Ya existen datos en la base de datos. No se insertarán datos de prueba.")
            return False
        
        # 1. Crear 10 clientes
        clientes_data = [
            {'nombre': 'Juan Pérez García', 'dni': '12345678A', 'telefono': '600123456', 'email': 'juan.perez@email.com', 'direccion': 'Calle Mayor 1', 'codigo_postal': '28001', 'poblacion': 'Madrid', 'provincia': 'Madrid'},
            {'nombre': 'María López Sánchez', 'dni': '23456789B', 'telefono': '600234567', 'email': 'maria.lopez@email.com', 'direccion': 'Avenida Libertad 15', 'codigo_postal': '41001', 'poblacion': 'Sevilla', 'provincia': 'Sevilla'},
            {'nombre': 'Carlos Martínez Ruiz', 'dni': '34567890C', 'telefono': '600345678', 'email': 'carlos.martinez@email.com', 'direccion': 'Plaza España 3', 'codigo_postal': '08001', 'poblacion': 'Barcelona', 'provincia': 'Barcelona'},
            {'nombre': 'Ana Fernández Torres', 'dni': '45678901D', 'telefono': '600456789', 'email': 'ana.fernandez@email.com', 'direccion': 'Calle Gran Vía 25', 'codigo_postal': '28013', 'poblacion': 'Madrid', 'provincia': 'Madrid'},
            {'nombre': 'Pedro González Moreno', 'dni': '56789012E', 'telefono': '600567890', 'email': 'pedro.gonzalez@email.com', 'direccion': 'Avenida Diagonal 100', 'codigo_postal': '08008', 'poblacion': 'Barcelona', 'provincia': 'Barcelona'},
            {'nombre': 'Laura Jiménez Díaz', 'dni': '67890123F', 'telefono': '600678901', 'email': 'laura.jimenez@email.com', 'direccion': 'Calle Sierpes 8', 'codigo_postal': '41004', 'poblacion': 'Sevilla', 'provincia': 'Sevilla'},
            {'nombre': 'Miguel Sánchez Pérez', 'dni': '78901234G', 'telefono': '600789012', 'email': 'miguel.sanchez@email.com', 'direccion': 'Calle Alcalá 50', 'codigo_postal': '28014', 'poblacion': 'Madrid', 'provincia': 'Madrid'},
            {'nombre': 'Carmen Ruiz Martín', 'dni': '89012345H', 'telefono': '600890123', 'email': 'carmen.ruiz@email.com', 'direccion': 'Paseo de Gracia 200', 'codigo_postal': '08008', 'poblacion': 'Barcelona', 'provincia': 'Barcelona'},
            {'nombre': 'Francisco García López', 'dni': '90123456I', 'telefono': '600901234', 'email': 'francisco.garcia@email.com', 'direccion': 'Calle Betis 12', 'codigo_postal': '41010', 'poblacion': 'Sevilla', 'provincia': 'Sevilla'},
            {'nombre': 'Isabel Torres Navarro', 'dni': '01234567J', 'telefono': '600012345', 'email': 'isabel.torres@email.com', 'direccion': 'Calle Serrano 75', 'codigo_postal': '28006', 'poblacion': 'Madrid', 'provincia': 'Madrid'},
        ]
        
        clientes = []
        for data in clientes_data:
            cliente = Cliente(**data)
            db.session.add(cliente)
            clientes.append(cliente)
        
        db.session.flush()  # Para obtener los IDs
        
        # 2. Crear vehículos (algunos clientes tendrán varios vehículos)
        vehiculos_data = [
            # Cliente 1 (Juan Pérez) - 2 vehículos
            {'matricula': '1234ABC', 'marca': 'Seat', 'modelo': 'Ibiza', 'tipo': 'Turismo', 'año': 2018, 'color': 'Blanco', 'cliente_id': clientes[0].id},
            {'matricula': '5678DEF', 'marca': 'Volkswagen', 'modelo': 'Golf', 'tipo': 'Turismo', 'año': 2020, 'color': 'Negro', 'cliente_id': clientes[0].id},
            # Cliente 2 (María López) - 1 vehículo
            {'matricula': '9012GHI', 'marca': 'Renault', 'modelo': 'Clio', 'tipo': 'Turismo', 'año': 2019, 'color': 'Rojo', 'cliente_id': clientes[1].id},
            # Cliente 3 (Carlos Martínez) - 2 vehículos
            {'matricula': '3456JKL', 'marca': 'Ford', 'modelo': 'Focus', 'tipo': 'Turismo', 'año': 2021, 'color': 'Azul', 'cliente_id': clientes[2].id},
            {'matricula': '7890MNO', 'marca': 'Peugeot', 'modelo': '308', 'tipo': 'Turismo', 'año': 2017, 'color': 'Gris', 'cliente_id': clientes[2].id},
            # Cliente 4 (Ana Fernández) - 1 vehículo
            {'matricula': '1357PQR', 'marca': 'Opel', 'modelo': 'Corsa', 'tipo': 'Turismo', 'año': 2020, 'color': 'Blanco', 'cliente_id': clientes[3].id},
            # Cliente 5 (Pedro González) - 2 vehículos
            {'matricula': '2468STU', 'marca': 'Audi', 'modelo': 'A3', 'tipo': 'Turismo', 'año': 2022, 'color': 'Negro', 'cliente_id': clientes[4].id},
            {'matricula': '3691VWX', 'marca': 'BMW', 'modelo': 'Serie 1', 'tipo': 'Turismo', 'año': 2019, 'color': 'Azul', 'cliente_id': clientes[4].id},
            # Cliente 6 (Laura Jiménez) - 1 vehículo
            {'matricula': '4826YZA', 'marca': 'Mercedes', 'modelo': 'Clase A', 'tipo': 'Turismo', 'año': 2021, 'color': 'Plata', 'cliente_id': clientes[5].id},
            # Cliente 7 (Miguel Sánchez) - 1 vehículo
            {'matricula': '5927BCD', 'marca': 'Toyota', 'modelo': 'Corolla', 'tipo': 'Turismo', 'año': 2020, 'color': 'Rojo', 'cliente_id': clientes[6].id},
            # Cliente 8 (Carmen Ruiz) - 1 vehículo
            {'matricula': '6048EFG', 'marca': 'Hyundai', 'modelo': 'i30', 'tipo': 'Turismo', 'año': 2019, 'color': 'Blanco', 'cliente_id': clientes[7].id},
            # Cliente 9 (Francisco García) - 1 vehículo
            {'matricula': '7159HIJ', 'marca': 'Nissan', 'modelo': 'Micra', 'tipo': 'Turismo', 'año': 2018, 'color': 'Negro', 'cliente_id': clientes[8].id},
            # Cliente 10 (Isabel Torres) - 1 vehículo
            {'matricula': '8260KLM', 'marca': 'Citroën', 'modelo': 'C3', 'tipo': 'Turismo', 'año': 2021, 'color': 'Gris', 'cliente_id': clientes[9].id},
        ]
        
        vehiculos = []
        for data in vehiculos_data:
            coche = Coche(**data)
            db.session.add(coche)
            vehiculos.append(coche)
        
        db.session.flush()
        
        # 3. Crear 20 intervenciones distribuidas entre los vehículos
        descripciones_intervenciones = [
            'Cambio de aceite y filtro',
            'Revisión general',
            'Cambio de pastillas de freno delanteras',
            'Reparación de sistema de aire acondicionado',
            'Cambio de neumáticos',
            'Alineación y balanceo',
            'Cambio de correa de distribución',
            'Reparación de motor',
            'Cambio de batería',
            'Revisión de sistema eléctrico',
            'Limpieza de inyectores',
            'Cambio de filtro de aire',
            'Reparación de sistema de escape',
            'Cambio de amortiguadores',
            'Revisión de frenos',
            'Cambio de líquido de frenos',
            'Reparación de caja de cambios',
            'Cambio de bujías',
            'Revisión de sistema de dirección',
            'Limpieza y mantenimiento general',
        ]
        
        intervenciones = []
        fecha_base = datetime.now() - timedelta(days=180)  # Últimos 6 meses
        
        # Asignar intervenciones de forma controlada para las primeras 13 (que se facturarán)
        # y aleatoria para las restantes
        asignaciones_controladas = [
            # Cliente 0: 2 intervenciones (índices 0, 1)
            {'cliente_idx': 0, 'vehiculo_idx': 0},  # Primer vehículo del cliente 0
            {'cliente_idx': 0, 'vehiculo_idx': 1},  # Segundo vehículo del cliente 0
            # Cliente 1: 1 intervención (índice 2)
            {'cliente_idx': 1, 'vehiculo_idx': 2},  # Vehículo del cliente 1
            # Cliente 2: 3 intervenciones (índices 3, 4, 5)
            {'cliente_idx': 2, 'vehiculo_idx': 3},  # Primer vehículo del cliente 2
            {'cliente_idx': 2, 'vehiculo_idx': 4},  # Segundo vehículo del cliente 2
            {'cliente_idx': 2, 'vehiculo_idx': 3},  # Primer vehículo del cliente 2
            # Cliente 3: 1 intervención (índice 6)
            {'cliente_idx': 3, 'vehiculo_idx': 5},  # Vehículo del cliente 3
            # Cliente 4: 2 intervenciones (índices 7, 8)
            {'cliente_idx': 4, 'vehiculo_idx': 6},  # Primer vehículo del cliente 4
            {'cliente_idx': 4, 'vehiculo_idx': 7},  # Segundo vehículo del cliente 4
            # Cliente 5: 1 intervención (índice 9)
            {'cliente_idx': 5, 'vehiculo_idx': 8},  # Vehículo del cliente 5
            # Cliente 6: 2 intervenciones (índices 10, 11)
            {'cliente_idx': 6, 'vehiculo_idx': 9},  # Vehículo del cliente 6
            {'cliente_idx': 6, 'vehiculo_idx': 9},  # Vehículo del cliente 6
            # Cliente 7: 1 intervención (índice 12)
            {'cliente_idx': 7, 'vehiculo_idx': 10},  # Vehículo del cliente 7
        ]
        
        for i in range(20):
            if i < len(asignaciones_controladas):
                # Asignación controlada para las primeras 13 intervenciones
                asignacion = asignaciones_controladas[i]
                cliente = clientes[asignacion['cliente_idx']]
                vehiculo = vehiculos[asignacion['vehiculo_idx']]
                cliente_intervencion = cliente.id
            else:
                # Asignación aleatoria para las restantes
                vehiculo = choice(vehiculos)
                cliente_vehiculo = vehiculo.cliente_id
                cliente_intervencion = cliente_vehiculo if randint(0, 1) else choice(clientes).id
            
            fecha_intervencion = fecha_base + timedelta(days=randint(0, 180))
            km = randint(10000, 150000)
            descripcion = descripciones_intervenciones[i]
            precio = round(uniform(50.0, 800.0), 2)
            horas = round(uniform(0.5, 8.0), 1)
            
            intervencion = Intervencion(
                coche_id=vehiculo.id,
                cliente_id=cliente_intervencion,
                fecha=fecha_intervencion,
                km=km,
                descripcion=descripcion,
                precio=precio,
                horas_trabajo=horas
            )
            db.session.add(intervencion)
            intervenciones.append(intervencion)
        
        db.session.flush()
        
        # 4. Crear 8 facturas (algunas intervenciones estarán facturadas)
        # Definir qué intervenciones van en cada factura
        facturas_config = [
            # Factura 1: 2 intervenciones del cliente 1
            {'cliente_id': clientes[0].id, 'intervenciones': [intervenciones[0], intervenciones[1]]},
            # Factura 2: 1 intervención del cliente 2
            {'cliente_id': clientes[1].id, 'intervenciones': [intervenciones[2]]},
            # Factura 3: 3 intervenciones del cliente 3
            {'cliente_id': clientes[2].id, 'intervenciones': [intervenciones[3], intervenciones[4], intervenciones[5]]},
            # Factura 4: 1 intervención del cliente 4
            {'cliente_id': clientes[3].id, 'intervenciones': [intervenciones[6]]},
            # Factura 5: 2 intervenciones del cliente 5
            {'cliente_id': clientes[4].id, 'intervenciones': [intervenciones[7], intervenciones[8]]},
            # Factura 6: 1 intervención del cliente 6
            {'cliente_id': clientes[5].id, 'intervenciones': [intervenciones[9]]},
            # Factura 7: 2 intervenciones del cliente 7
            {'cliente_id': clientes[6].id, 'intervenciones': [intervenciones[10], intervenciones[11]]},
            # Factura 8: 1 intervención del cliente 8
            {'cliente_id': clientes[7].id, 'intervenciones': [intervenciones[12]]},
        ]
        
        facturas = []
        intervenciones_facturadas = []
        
        for i, config in enumerate(facturas_config):
            intervenciones_factura = config['intervenciones']
            total = sum(interv.precio for interv in intervenciones_factura)
            numero_factura = f"FAC-{datetime.now().year}-{i + 1:04d}"
            
            factura = Factura(
                cliente_id=config['cliente_id'],
                numero_factura=numero_factura,
                total=total,
                fecha=intervenciones_factura[0].fecha  # Fecha de la primera intervención
            )
            db.session.add(factura)
            db.session.flush()
            
            # Asociar intervenciones a la factura
            for interv in intervenciones_factura:
                interv.factura_id = factura.id
                intervenciones_facturadas.append(interv)
            
            facturas.append(factura)
        
        db.session.commit()
        
        print(f"✓ Datos de prueba insertados correctamente:")
        print(f"  - {len(clientes)} clientes")
        print(f"  - {len(vehiculos)} vehículos")
        print(f"  - {len(intervenciones)} intervenciones")
        print(f"  - {len(facturas)} facturas")
        print(f"  - {len(intervenciones_facturadas)} intervenciones facturadas")
        print(f"  - {len(intervenciones) - len(intervenciones_facturadas)} intervenciones sin facturar")
        
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"Error al insertar datos de prueba: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

@app.route('/insertar-datos-prueba', methods=['GET', 'POST'])
def ruta_insertar_datos_prueba():
    """Ruta para insertar datos de prueba (solo si no hay datos existentes)"""
    if request.method == 'POST':
        resultado = insertar_datos_prueba()
        if resultado:
            flash('Datos de prueba insertados correctamente', 'success')
        else:
            flash('No se insertaron datos. Ya existen datos en la base de datos o hubo un error.', 'error')
        return redirect(url_for('index'))
    
    # GET: mostrar confirmación
    tiene_datos = Cliente.query.count() > 0
    return render_template('index.html', mostrar_confirmacion_datos=True, tiene_datos=tiene_datos)

if __name__ == '__main__':
    app.run(debug=True)

