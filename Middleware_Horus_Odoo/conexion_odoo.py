import xmlrpc.client

url = "http://devo.uaalze.com"
db = "bd_odoo1"
username = "admin"
password = "admin"

common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
print("Versión de Odoo:", common.version())

uid = common.authenticate(db, username, password, {})
print("UID:", uid)
if uid:
    print("✅ Conexión exitosa")
else:
    print("❌ Falló autenticación")