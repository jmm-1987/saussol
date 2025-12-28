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
        
        # Calcular total inicial con intervenciones existentes
        total = sum(interv.precio for interv in intervenciones_existentes)
        
        # Generar número de factura
        ultima_factura = Factura.query.order_by(Factura.id.desc()).first()
        numero_factura = f"FAC-{datetime.now().year}-{ultima_factura.id + 1 if ultima_factura else 1:04d}"
        
        # Crear factura
        factura = Factura(
            cliente_id=cliente_id,
            numero_factura=numero_factura,
            total=0  # Se actualizará después
        )
        
        try:
            db.session.add(factura)
            db.session.flush()  # Para obtener el ID
            
            # Asociar intervenciones existentes
            for interv in intervenciones_existentes:
                interv.factura_id = factura.id
                total += interv.precio
            
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
                total += nueva_intervencion.precio
            
            # Actualizar total de la factura
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
    # Obtener intervenciones no facturadas
    intervenciones = Intervencion.query.filter_by(factura_id=None).order_by(Intervencion.fecha.desc()).all()
    
    return render_template('facturas/nueva.html', clientes=clientes, vehiculos=vehiculos, intervenciones=intervenciones)

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

if __name__ == '__main__':
    app.run(debug=True)

