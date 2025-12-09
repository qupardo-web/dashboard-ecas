#Archivo para la creación de vistas, como la vista unificada.

from connector_db import get_db_engine
from sqlalchemy import text

#Metodo para obtener los nombres de las tablas que utilizaremos.
def get_table_names(engine):
   
    query = """
    SELECT TABLE_NAME 
    FROM INFORMATION_SCHEMA.TABLES 
    WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME LIKE 'matricula_[0-9]%'
    ORDER BY TABLE_NAME;
    """
    try:
        with engine.connect() as connection:

            result = connection.execute(text(query)).fetchall()

            return [row[0] for row in result]

    except Exception as e:
        print(f"ERROR al obtener nombres de tablas: {e}")
        return []

def create_unified_view():
    """Crea o reemplaza la vista unificada 'vista_matriculas_unificada'."""
    engine = get_db_engine()
    if not engine:
        return False, "Error de conexión a la DB."
        
    table_names = get_table_names(engine)
    if not table_names:
        return False, "No se encontraron tablas 'matricula_AÑO' en la DB. ¡Asegúrate de ejecutar carga_csv.py primero!"

    #Query para dropear la vista unificada si ya existe
    drop_query = """
    IF OBJECT_ID('dbo.vista_matriculas_unificada', 'V') IS NOT NULL
        DROP VIEW dbo.vista_matriculas_unificada;
    """
    
    # Construcción de la parte UNION ALL
    select_statements = []
    for table in table_names:
        select_statements.append(f"""
        SELECT 
            CAST(cat_periodo AS INT) AS cat_periodo, 
            mrun, 
            nomb_inst, 
            nomb_carrera,
            area_conocimiento,
            codigo_unico,
            dur_total_carr,
            cod_inst,
            jornada, 
            dur_estudio_carr, 
            dur_proceso_tit,
            anio_ing_carr_ori
        FROM dbo.{table}
        """)

    union_query = "\nUNION ALL\n".join(select_statements)

    create_view_query = f"""
    CREATE VIEW dbo.vista_matriculas_unificada AS
    {union_query};
    """

    try:
        with engine.connect() as connection:
            #Eliminar vista unificada
            connection.execute(text(drop_query)) 
            connection.commit()
            
            #Crear nueva vista unificada
            connection.execute(text(create_view_query))
            connection.commit()
            
            return True, f"Vista 'vista_matriculas_unificada' creada/actualizada con {len(table_names)} tablas."
            
    except Exception as e:
        return False, f"ERROR al crear la vista SQL: {e}"

if __name__ == '__main__':
    success, message = create_unified_view()
    print(message)