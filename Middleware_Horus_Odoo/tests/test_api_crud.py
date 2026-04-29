# tests/test_api_crud.py
import requests

BASE_URL = "http://localhost:8000/api/empleados"

def crear(uid, nombre, departamento):
    resp = requests.post(BASE_URL, json={"uid": uid, "nombre": nombre, "departamento": departamento})
    print("CREAR:", resp.status_code, resp.json())
    return resp

def listar():
    resp = requests.get(BASE_URL)
    print("LISTAR:", resp.status_code, resp.json())
    return resp

def actualizar(uid, nombre=None, departamento=None):
    payload = {}
    if nombre: payload["nombre"] = nombre
    if departamento: payload["departamento"] = departamento
    resp = requests.put(f"{BASE_URL}/{uid}", json=payload)
    print("ACTUALIZAR:", resp.status_code, resp.json())
    return resp

def eliminar(uid):
    resp = requests.delete(f"{BASE_URL}/{uid}")
    print("ELIMINAR:", resp.status_code, resp.json())
    return resp

if __name__ == "__main__":
    # Crear
    crear(7777, "Usuario Prueba", "TI")
    listar()
    # Actualizar
    actualizar(7777, nombre="Usuario Modificado", departamento="RH")
    listar()
    # Eliminar
    eliminar(7777)
    listar()