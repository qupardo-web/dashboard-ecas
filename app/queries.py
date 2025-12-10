#Archivo para realizar consultas SQL que nos entreguen dataframes personalizados
#por cada KPI
import pandas as pd
from connector_db import get_db_engine
import numpy as np

COD_INST_ECAS = 104
DURACION_DIURNA_SEMESTRES = 8  # 4 años
DURACION_VESPERTINA_SEMESTRES = 9 # 4.5 años

#KPI 1: Tasa de permanencia de los estudiantes año a año.
def kpi1_permanencia_ecas(db_conn, anio=None):
    """
    Calcula el porcentaje de permanencia dentro de ECAS (COD_INST = 104) usando la vista unificada.
    """
    
    query_base = f"""
    SELECT 
        cat_periodo AS ANIO, 
        mrun AS mrun,
        anio_ing_carr_ori,
        jornada as jornada
    FROM 
        vista_matriculas_unificada 
    WHERE 
        cod_inst = 104
    """
    df_ecas = pd.read_sql(query_base, db_conn)
    
    lista_permanencia = []
    
    # Rango de años y lógica de sets para calcular la tasa anual
    for anio_n in range(2007, 2025):
        anio_n_mas_1 = anio_n + 1
        
        df_n = df_ecas[df_ecas['ANIO'] == anio_n].copy()
        
        df_n['Duracion_Teorica'] = np.where(
            df_n['jornada'].str.contains('Vespertino', na=False), 
            DURACION_VESPERTINA_SEMESTRES, 
            DURACION_DIURNA_SEMESTRES
        )

        df_n['Permanencia_Anios'] = df_n['ANIO'] - df_n['anio_ing_carr_ori']
        df_n['Permanencia_Semestres'] = df_n['Permanencia_Anios'] * 2 # <--- COLUMNA CREADA AHORA
        df_n_activos = df_n[df_n['Permanencia_Semestres'] < df_n['Duracion_Teorica']].copy()

        mrun_anio_n_activos = set(df_n_activos['mrun'])
        
        df_n_mas_1 = df_ecas[df_ecas['ANIO'] == anio_n_mas_1].copy()
        mrun_anio_n_mas_1_ecas = set(df_n_mas_1['mrun'])
        
        if len(mrun_anio_n_activos) > 0:
            # Intersección: Población activa en N que permanece en N+1
            estudiantes_permanecen = len(mrun_anio_n_activos.intersection(mrun_anio_n_mas_1_ecas))
            
            # El denominador es la POBLACIÓN ACTIVA (mrun_anio_n_activos)
            tasa_permanencia = (estudiantes_permanecen / len(mrun_anio_n_activos)) * 100
            
            lista_permanencia.append({
                'Año': anio_n_mas_1,
                'Tasa_Permanencia_ECAS': round(tasa_permanencia, 2)
        })

    df_permanencia = pd.DataFrame(lista_permanencia)
    if anio:
        return df_permanencia[df_permanencia['Año'] == anio]
    else:
        tasa_general = df_permanencia['Tasa_Permanencia_ECAS'].mean()
        return df_permanencia, round(tasa_general, 2)
 
def kpi2_institucion_destino_opt(db_conn, anio_n=None):

    filter_anio = ""

    if isinstance(anio_n, int): 
        filter_anio = f"AND T1.cat_periodo = {anio_n}"
    
    sql_query = f"""
        SELECT
        T2.nomb_inst AS INST_DESTINO,
        COUNT(T2.mrun) AS Total_Fuga
        FROM
            vista_matriculas_unificada AS T1
        INNER JOIN
            vista_matriculas_unificada AS T2
            ON T1.mrun = T2.mrun AND T2.cat_periodo = T1.cat_periodo + 1
        WHERE
            T1.cod_inst = {COD_INST_ECAS} -- Origen: ECAS
            AND T2.cod_inst != {COD_INST_ECAS} -- Destino: No es ECAS (Es fuga)
            -- Exclusión (misma lógica de permanencia)
            AND (
                (T1.cat_periodo - T1.anio_ing_carr_ori) * 2 < 
                (CASE 
                    WHEN T1.jornada LIKE '%Vespertino%' 
                    THEN {DURACION_VESPERTINA_SEMESTRES} 
                    ELSE {DURACION_DIURNA_SEMESTRES} 
                END)
            )
            {filter_anio} -- Aplica el filtro de año
        GROUP BY
            T2.nomb_inst
        ORDER BY
            Total_Fuga DESC;
    """

    df_kpi2 = pd.read_sql(sql_query, db_conn)
    
    #Calculo de porcentaje
    total_fuga_general = df_kpi2['Total_Fuga'].sum()
    if total_fuga_general > 0:
        df_kpi2['Porcentaje'] = (df_kpi2['Total_Fuga'] / total_fuga_general) * 100
        
    return df_kpi2

def kpi3_carrera_destino(db_conn, anio_n=None):
    
    filter_anio=""

    if isinstance(anio_n, int): 
        filter_anio = f"AND T1.cat_periodo = {anio_n}"

    sql_query = f"""
    SELECT
        T2.nomb_carrera AS CARRERA_DESTINO,
        COUNT(T2.mrun) AS Total_Fuga
    FROM
        vista_matriculas_unificada AS T1
    INNER JOIN
        vista_matriculas_unificada AS T2
        ON T1.mrun = T2.mrun AND T2.cat_periodo = T1.cat_periodo + 1
    WHERE
        T1.cod_inst = {COD_INST_ECAS}
        AND T2.cod_inst != {COD_INST_ECAS}
        -- Exclusión (misma lógica de permanencia)
        AND (
            (T1.cat_periodo - T1.anio_ing_carr_ori) * 2 < 
            (CASE 
                WHEN T1.jornada LIKE '%Vespertino%' 
                THEN {DURACION_VESPERTINA_SEMESTRES} 
                ELSE {DURACION_DIURNA_SEMESTRES}
            END)
        )
        {filter_anio}
    GROUP BY
        T2.nomb_carrera
    ORDER BY
        Total_Fuga DESC;
    """
    
    df_kpi3 = pd.read_sql(sql_query, db_conn)
    
    # Calcular el porcentaje en Python (más fácil que en SQL)
    total_fuga_general = df_kpi3['Total_Fuga'].sum()
    if total_fuga_general > 0:
        df_kpi3['Porcentaje'] = (df_kpi3['Total_Fuga'] / total_fuga_general) * 100
        
    return df_kpi3

def kpi4_area_destino(db_conn, anio_n=None):
    """
    Calcula la distribución de la fuga de ECAS por área de la carrera de destino.
    """
    filter_anio = ""
    
    if isinstance(anio_n, int): 
        filter_anio = f"AND T1.cat_periodo = {anio_n}"

    sql_query = f"""
    SELECT
        T2.area_conocimiento AS AREA_DESTINO,
        COUNT(T2.mrun) AS Total_Fuga
    FROM
        vista_matriculas_unificada AS T1
    INNER JOIN
        vista_matriculas_unificada AS T2
        ON T1.mrun = T2.mrun AND T2.cat_periodo = T1.cat_periodo + 1
    WHERE
        T1.cod_inst = {COD_INST_ECAS}
        AND T2.cod_inst != {COD_INST_ECAS}
        -- Exclusión (misma lógica de permanencia)
        AND (
            (T1.cat_periodo - T1.anio_ing_carr_ori) * 2 < 
            (CASE 
                WHEN T1.jornada LIKE '%Vespertino%' 
                THEN {DURACION_VESPERTINA_SEMESTRES}
                ELSE {DURACION_DIURNA_SEMESTRES}
            END)
        )
        {filter_anio}
    GROUP BY
        T2.area_conocimiento
    ORDER BY
        Total_Fuga DESC;
    """
    
    df_kpi4 = pd.read_sql(sql_query, db_conn)
    
    # Calcular el porcentaje en Python 
    total_fuga_general = df_kpi4['Total_Fuga'].sum()
    if total_fuga_general > 0:
        df_kpi4['Porcentaje'] = (df_kpi4['Total_Fuga'] / total_fuga_general) * 100
        
    return df_kpi4

def kpi5_estimacion_titulacion(db_conn, anio_n=None):