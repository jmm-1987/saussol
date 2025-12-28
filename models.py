from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Cliente(db.Model):
    __tablename__ = 'clientes'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    dni = db.Column(db.String(20), unique=True)
    telefono = db.Column(db.String(20))
    email = db.Column(db.String(100))
    direccion = db.Column(db.String(200))
    codigo_postal = db.Column(db.String(10))
    poblacion = db.Column(db.String(100))
    provincia = db.Column(db.String(100))
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    
    facturas = db.relationship('Factura', backref='cliente', lazy=True)
    
    def __repr__(self):
        return f'<Cliente {self.nombre}>'

class Coche(db.Model):
    __tablename__ = 'coches'
    
    id = db.Column(db.Integer, primary_key=True)
    matricula = db.Column(db.String(20), unique=True, nullable=False)
    marca = db.Column(db.String(50))
    modelo = db.Column(db.String(50))
    tipo = db.Column(db.String(50))
    año = db.Column(db.Integer)
    color = db.Column(db.String(30))
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=True)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    
    cliente = db.relationship('Cliente', backref='vehiculos', lazy=True)
    intervenciones = db.relationship('Intervencion', backref='coche', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Vehiculo {self.matricula}>'

class Intervencion(db.Model):
    __tablename__ = 'intervenciones'
    
    id = db.Column(db.Integer, primary_key=True)
    coche_id = db.Column(db.Integer, db.ForeignKey('coches.id'), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    km = db.Column(db.Integer, nullable=True)
    descripcion = db.Column(db.Text, nullable=False)
    precio = db.Column(db.Float, nullable=False, default=0.0)
    horas_trabajo = db.Column(db.Float, default=0.0)
    
    factura_id = db.Column(db.Integer, db.ForeignKey('facturas.id'), nullable=True)
    
    cliente = db.relationship('Cliente', backref='intervenciones', lazy=True)
    
    def __repr__(self):
        return f'<Intervencion {self.id} - {self.descripcion[:30]}>'

class Factura(db.Model):
    __tablename__ = 'facturas'
    
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    numero_factura = db.Column(db.String(50), unique=True, nullable=False)
    base_imponible = db.Column(db.Float, nullable=False, default=0.0)
    descuento_porcentaje = db.Column(db.Float, nullable=False, default=0.0)
    descuento_importe = db.Column(db.Float, nullable=False, default=0.0)
    iva_porcentaje = db.Column(db.Float, nullable=False, default=21.0)  # IVA por defecto 21%
    iva_importe = db.Column(db.Float, nullable=False, default=0.0)
    total = db.Column(db.Float, nullable=False, default=0.0)
    enviada_verifactu = db.Column(db.Boolean, default=False)
    fecha_envio_verifactu = db.Column(db.DateTime, nullable=True)
    
    intervenciones = db.relationship('Intervencion', backref='factura', lazy=True)
    
    def __repr__(self):
        return f'<Factura {self.numero_factura}>'

