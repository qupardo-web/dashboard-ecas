#Archivo para generar conexión con base de datos

from sqlalchemy import create_engine
import urllib

SERVER = 'QUPARDO'
DATABASE = 'DBMatriculas'
DRIVER_NAME = 'ODBC Driver 17 for SQL Server' 

def get_db_engine():
    """Establece y devuelve el motor de conexión (Engine) a SQL Server usando Autenticación de Windows."""
    try:
        
        DRIVER = urllib.parse.quote_plus(DRIVER_NAME)
        
        DB_URL = f"mssql+pyodbc://{SERVER}/{DATABASE}?driver={DRIVER}&trusted_connection=yes"
        
        engine = create_engine(DB_URL, fast_executemany=True)
        
        # Probar la conexión
        with engine.connect():
            return engine
            
    except Exception as e:
        print("="*50)
        print(f"ERROR DE CONEXIÓN A SQL SERVER: {e}")
        print(f"Revisa el nombre del servidor ({SERVER}) y el driver ({DRIVER_NAME}).")
        print("="*50)
        return None

if __name__ == '__main__':
    # Prueba de conexión rápida
    if get_db_engine():
        print("conector_db.py: Conexión exitosa. Engine listo.")