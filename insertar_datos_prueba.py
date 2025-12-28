"""
Script para insertar datos de prueba en la base de datos.
Ejecutar con: python insertar_datos_prueba.py
"""
from app import app, insertar_datos_prueba

if __name__ == '__main__':
    with app.app_context():
        print("Iniciando inserción de datos de prueba...")
        resultado = insertar_datos_prueba()
        if resultado:
            print("\n✓ ¡Datos de prueba insertados correctamente!")
        else:
            print("\n✗ No se insertaron datos. Ya existen datos en la base de datos o hubo un error.")

