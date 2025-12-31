# Sistema de Gestión de Taller de Automoción

Software sencillo para gestionar clientes, coches, intervenciones y facturas en un taller de automoción.

## Características

- **Gestión de Clientes**: Registro y administración de clientes del taller
- **Gestión de Coches**: Registro de vehículos con fichas técnicas
- **Intervenciones**: Registro de todas las intervenciones realizadas en cada coche
- **Facturas**: Creación de facturas asociando intervenciones a clientes (los coches no son fijos para los clientes)
- **Integración Verifactu**: Función preparada para enviar facturas a Verifactu (pendiente de implementar con credenciales reales)

## Instalación

1. Instalar Python 3.8 o superior

2. Instalar las dependencias:
```bash
pip install -r requirements.txt
```

## Uso

1. Ejecutar la aplicación:
```bash
python app.py
```

2. Abrir el navegador en: `http://localhost:5000`

## Estructura de la Base de Datos

- **Clientes**: Información de los clientes (nombre, DNI, teléfono, email, dirección)
- **Coches**: Información de los vehículos (matrícula, marca, modelo, año, color)
- **Intervenciones**: Trabajos realizados en cada coche (fecha, descripción, precio, horas)
- **Facturas**: Facturas que asocian intervenciones a clientes

## Notas Importantes

- Las intervenciones se registran en la ficha de cada coche
- Cualquier intervención puede ser facturada a cualquier cliente
- Una vez facturada, una intervención no puede ser eliminada
- La función de envío a Verifactu está preparada pero requiere configuración de credenciales API

## Integración con Verifactu

La función `enviar_factura_verifactu()` en `app.py` está preparada para integrarse con la API de Verifactu. Para completar la integración:

1. Obtener las credenciales de la API de Verifactu
2. Configurar la URL de la API
3. Descomentar y completar el código en la función
4. Configurar variables de entorno para las credenciales (recomendado)





