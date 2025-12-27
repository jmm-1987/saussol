from flask import Flask, render_template, request, redirect, url_for, flash
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

# ========== RUTAS DE COCHES ==========

@app.route('/coches')
def listar_coches():
    coches = Coche.query.order_by(Coche.matricula).all()
    return render_template('coches/listar.html', coches=coches)

@app.route('/coches/nuevo', methods=['GET', 'POST'])
def nuevo_coche():
    if request.method == 'POST':
        coche = Coche(
            matricula=request.form['matricula'].upper(),
            marca=request.form.get('marca') or None,
            modelo=request.form.get('modelo') or None,
            año=int(request.form['año']) if request.form.get('año') else None,
            color=request.form.get('color') or None
        )
        try:
            db.session.add(coche)
            db.session.commit()
            flash('Coche registrado correctamente', 'success')
            return redirect(url_for('listar_coches'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar coche: {str(e)}', 'error')
    
    return render_template('coches/nuevo.html')

@app.route('/coches/<int:id>/editar', methods=['GET', 'POST'])
def editar_coche(id):
    coche = Coche.query.get_or_404(id)
    
    if request.method == 'POST':
        coche.matricula = request.form['matricula'].upper()
        coche.marca = request.form.get('marca') or None
        coche.modelo = request.form.get('modelo') or None
        coche.año = int(request.form['año']) if request.form.get('año') else None
        coche.color = request.form.get('color') or None
        
        try:
            db.session.commit()
            flash('Coche actualizado correctamente', 'success')
            return redirect(url_for('listar_coches'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar coche: {str(e)}', 'error')
    
    return render_template('coches/editar.html', coche=coche)

@app.route('/coches/<int:id>/eliminar', methods=['POST'])
def eliminar_coche(id):
    coche = Coche.query.get_or_404(id)
    try:
        db.session.delete(coche)
        db.session.commit()
        flash('Coche eliminado correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar coche: {str(e)}', 'error')
    
    return redirect(url_for('listar_coches'))

@app.route('/coches/<int:id>/ficha')
def ficha_coche(id):
    coche = Coche.query.get_or_404(id)
    intervenciones = Intervencion.query.filter_by(coche_id=id).order_by(Intervencion.fecha.desc()).all()
    return render_template('coches/ficha.html', coche=coche, intervenciones=intervenciones)

# ========== RUTAS DE INTERVENCIONES ==========

@app.route('/coches/<int:coche_id>/intervenciones/nueva', methods=['GET', 'POST'])
def nueva_intervencion(coche_id):
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
            return render_template('intervenciones/nueva.html', coche=coche)
        
        intervenciones_creadas = 0
        try:
            for i in range(len(descripciones)):
                if descripciones[i].strip():  # Solo crear si hay descripción
                    intervencion = Intervencion(
                        coche_id=coche_id,
                        fecha=fecha,
                        km=km,
                        descripcion=descripciones[i].strip(),
                        precio=float(precios[i]) if precios[i] else 0.0,
                        horas_trabajo=float(horas[i]) if horas[i] else 0.0
                    )
                    db.session.add(intervencion)
                    intervenciones_creadas += 1
            
            db.session.commit()
            flash(f'{intervenciones_creadas} intervención(es) registrada(s) correctamente', 'success')
            return redirect(url_for('ficha_coche', id=coche_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar intervención: {str(e)}', 'error')
    
    return render_template('intervenciones/nueva.html', coche=coche)

@app.route('/intervenciones/<int:id>/editar', methods=['GET', 'POST'])
def editar_intervencion(id):
    intervencion = Intervencion.query.get_or_404(id)
    
    if request.method == 'POST':
        intervencion.fecha = datetime.strptime(request.form['fecha'], '%Y-%m-%d')
        intervencion.km = int(request.form['km']) if request.form.get('km') else None
        intervencion.descripcion = request.form['descripcion']
        intervencion.precio = float(request.form['precio'])
        intervencion.horas_trabajo = float(request.form.get('horas_trabajo') or 0)
        
        try:
            db.session.commit()
            flash('Intervención actualizada correctamente', 'success')
            return redirect(url_for('ficha_coche', id=intervencion.coche_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar intervención: {str(e)}', 'error')
    
    return render_template('intervenciones/editar.html', intervencion=intervencion)

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
    facturas = Factura.query.order_by(Factura.fecha.desc()).all()
    return render_template('facturas/listar.html', facturas=facturas)

@app.route('/facturas/nueva', methods=['GET', 'POST'])
def nueva_factura():
    if request.method == 'POST':
        cliente_id = int(request.form['cliente_id'])
        intervenciones_ids = [int(id) for id in request.form.getlist('intervenciones')]
        
        if not intervenciones_ids:
            flash('Debe seleccionar al menos una intervención', 'error')
            return redirect(url_for('nueva_factura'))
        
        # Verificar que las intervenciones no estén ya facturadas
        intervenciones = Intervencion.query.filter(Intervencion.id.in_(intervenciones_ids)).all()
        for interv in intervenciones:
            if interv.factura_id:
                flash(f'La intervención {interv.id} ya está facturada', 'error')
                return redirect(url_for('nueva_factura'))
        
        # Calcular total
        total = sum(interv.precio for interv in intervenciones)
        
        # Generar número de factura
        ultima_factura = Factura.query.order_by(Factura.id.desc()).first()
        numero_factura = f"FAC-{datetime.now().year}-{ultima_factura.id + 1 if ultima_factura else 1:04d}"
        
        # Crear factura
        factura = Factura(
            cliente_id=cliente_id,
            numero_factura=numero_factura,
            total=total
        )
        
        try:
            db.session.add(factura)
            db.session.flush()  # Para obtener el ID
            
            # Asociar intervenciones
            for interv in intervenciones:
                interv.factura_id = factura.id
            
            db.session.commit()
            flash('Factura creada correctamente', 'success')
            return redirect(url_for('ver_factura', id=factura.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear factura: {str(e)}', 'error')
    
    # GET: mostrar formulario
    clientes = Cliente.query.order_by(Cliente.nombre).all()
    # Obtener intervenciones no facturadas
    intervenciones = Intervencion.query.filter_by(factura_id=None).order_by(Intervencion.fecha.desc()).all()
    
    return render_template('facturas/nueva.html', clientes=clientes, intervenciones=intervenciones)

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

