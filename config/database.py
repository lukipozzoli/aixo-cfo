import os

# Configuración de la base de datos.
# Este archivo no contiene ningún dato de ninguna empresa: solo dice qué
# variables se leen del entorno. Los valores reales viven en el .env, que no
# está versionado. Por eso el mismo archivo sirve igual para cualquier empresa.

DATABASE_PROVIDER: str = os.environ["DATABASE_PROVIDER"]

# Los datos que necesita el proveedor elegido, listos para el factory.
# Mismo criterio que en messaging.py: solo se leen las variables del proveedor
# que se va a usar realmente.
#
# os.environ[...] con corchetes revienta si la variable falta, y es a propósito:
# sin base de datos el agente no puede hacer nada, así que mejor un error claro
# al arrancar que un fallo raro más adelante.
if DATABASE_PROVIDER == "supabase":
    DATABASE_CONFIG: dict = {
        "url": os.environ["DATABASE_URL"],
        "key": os.environ["DATABASE_KEY"],
    }
else:
    DATABASE_CONFIG = {}
