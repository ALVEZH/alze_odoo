# tests/verificar_bd.py
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'middleware.db')

def consultar(tabla, condicion=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    query = f"SELECT * FROM {tabla}"
    if condicion:
        query += f" WHERE {condicion}"
    cursor.execute(query)
    rows = cursor.fetchall()
    # Obtener nombres de columnas
    columnas = [description[0] for description in cursor.description]
    conn.close()
    return columnas, rows

if __name__ == "__main__":
    # Ejemplo: ver empleados con foto_enviada
    cols, rows = consultar("empleados", "pin_horus = '49'")
    print("Columnas:", cols)
    for row in rows:
        print(row)