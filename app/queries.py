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
                'Año': anio_n,
                'Tasa_Permanencia_ECAS': round(tasa_permanencia, 2)
        })

    df_permanencia = pd.DataFrame(lista_permanencia)
    if anio:
        return df_permanencia[df_permanencia['Año'] == anio]
    else:
        tasa_general = df_permanencia['Tasa_Permanencia_ECAS'].mean()
        return df_permanencia, round(tasa_general, 2)
 
def kpi2_institucion_destino_opt(db_conn, anio_n=None):
    """
    Calcula la distribución de la fuga de ECAS por institución de destino
    utilizando una consulta SQL única para eficiencia.
    """
    filter_anio = ""
    if anio_n is not None:
        filter_anio = f"AND T1.cat_periodo = {anio_n}"
        
    sql_query = f"""
    WITH Cohorte_Origen AS (
        -- Paso 1: Identificar a los estudiantes en ECAS en el año N, aplicando la exclusión por graduación estimada
        SELECT
            mrun,
            cat_periodo AS anio
        FROM (
            SELECT
                mrun, cat_periodo, cod_inst, jornada, dur_estudio_carr, anio_ing_carr_ori
            FROM 
                vista_matriculas_unificada
            WHERE
                cod_inst = {COD_INST_ECAS}
        ) AS T1
        WHERE 
            -- Exclusión: Permanencia (en semestres) < Duración Teórica
            (T1.cat_periodo - T1.anio_ing_carr_ori) * 2 < 
            (CASE WHEN T1.jornada LIKE '%Vespertino%' THEN {DURACION_VESPERTINA_SEMESTRES} ELSE {DURACION_DIURNA_SEMESTRES} END)
            
        {filter_anio}
    ),

    Fuga_Destino AS (
        -- Paso 2: Unir la cohorte con el destino en el año N+1
        SELECT 
            C.mrun,
            D.nomb_inst AS inst_destino
        FROM
            Cohorte_Origen AS C
        INNER JOIN
            vista_matriculas_unificada AS D ON C.mrun = D.mrun AND D.cat_periodo = C.anio + 1
        WHERE
            D.cod_inst != {COD_INST_ECAS} -- Filtrar la FUGA (se fueron a otra institución)
    )

    -- Paso 3: Agrupar y calcular el porcentaje total
    SELECT
        inst_destino AS INST_DESTINO,
        COUNT(mrun) AS Total_Fuga
    FROM
        Fuga_Destino
    GROUP BY
        inst_destino
    ORDER BY
        Total_Fuga DESC;
    """
    
    df_kpi2 = pd.read_sql(sql_query, db_conn)
    
    # Calcular el porcentaje en Python (más fácil que en SQL)
    total_fuga_general = df_kpi2['Total_Fuga'].sum()
    if total_fuga_general > 0:
        df_kpi2['Porcentaje'] = (df_kpi2['Total_Fuga'] / total_fuga_general) * 100
        
    return df_kpi2

def kpi3_carrera_destino(db_conn, anio_n=None):
    
    filter_anio=""
    if anio_n is None:
        filter_anio = f"AND T1.cat_periodo = {anio_n}"

    sql_query = f"""
    WITH Cohorte_Origen AS (
        -- Paso 1: Identificar a los estudiantes en ECAS en el año N, aplicando la exclusión por graduación estimada
        SELECT
            mrun,
            cat_periodo AS anio
        FROM (
            SELECT
                mrun, cat_periodo, cod_inst, jornada, dur_estudio_carr, anio_ing_carr_ori
            FROM 
                vista_matriculas_unificada
            WHERE
                cod_inst = {COD_INST_ECAS}
        ) AS T1
        WHERE 
            -- Exclusión: Permanencia (en semestres) < Duración Teórica
            (T1.cat_periodo - T1.anio_ing_carr_ori) * 2 < 
            (CASE WHEN T1.jornada LIKE '%Vespertino%' THEN {DURACION_VESPERTINA_SEMESTRES} ELSE {DURACION_DIURNA_SEMESTRES} END)
            
        {filter_anio}
    ),

    Fuga_Destino AS (
        -- Paso 2: Unir la cohorte con el destino en el año N+1
        SELECT 
            C.mrun,
            D.nomb_carrera AS carrera_destino -- CAMBIO CLAVE: Capturamos la carrera de destino
        FROM
            Cohorte_Origen AS C
        INNER JOIN
            vista_matriculas_unificada AS D ON C.mrun = D.mrun AND D.cat_periodo = C.anio + 1
        WHERE
            D.cod_inst != {COD_INST_ECAS} -- Filtrar la FUGA (se fueron a otra institución)
    )

    -- Paso 3: Agrupar y calcular el porcentaje total
    SELECT
        carrera_destino AS CARRERA_DESTINO, -- CAMBIO CLAVE: Alias de salida
        COUNT(mrun) AS Total_Fuga
    FROM
        Fuga_Destino
    GROUP BY
        carrera_destino
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
    if anio_n is not None:
        filter_anio = f"AND T1.cat_periodo = {anio_n}"

    sql_query = f"""
    WITH Cohorte_Origen AS (
        -- Paso 1: Identificar a los estudiantes en ECAS en el año N, aplicando la exclusión por graduación estimada
        SELECT
            mrun,
            cat_periodo AS anio
        FROM (
            SELECT
                mrun, cat_periodo, cod_inst, jornada, dur_estudio_carr, anio_ing_carr_ori
            FROM 
                vista_matriculas_unificada
            WHERE
                cod_inst = {COD_INST_ECAS}
        ) AS T1
        WHERE 
            -- Exclusión: Permanencia (en semestres) < Duración Teórica
            (T1.cat_periodo - T1.anio_ing_carr_ori) * 2 < 
            (CASE WHEN T1.jornada LIKE '%Vespertino%' THEN {DURACION_VESPERTINA_SEMESTRES} ELSE {DURACION_DIURNA_SEMESTRES} END)
            
        {filter_anio}
    ),

    Fuga_Destino AS (
        -- Paso 2: Unir la cohorte con el destino en el año N+1
        SELECT 
            C.mrun,
            D.area_conocimiento AS area_destino 
        FROM
            Cohorte_Origen AS C
        INNER JOIN
            vista_matriculas_unificada AS D ON C.mrun = D.mrun AND D.cat_periodo = C.anio + 1
        WHERE
            D.cod_inst != {COD_INST_ECAS} -- Filtrar la FUGA (se fueron a otra institución)
    )

    -- Paso 3: Agrupar y calcular el porcentaje total
    SELECT
        area_destino AS AREA_DESTINO, -- 🔑 CAMBIO CLAVE: Alias de salida
        COUNT(mrun) AS Total_Fuga
    FROM
        Fuga_Destino
    GROUP BY
        area_destino
    ORDER BY
        Total_Fuga DESC;
    """
    
    df_kpi4 = pd.read_sql(sql_query, db_conn)
    
    # Calcular el porcentaje en Python 
    total_fuga_general = df_kpi4['Total_Fuga'].sum()
    if total_fuga_general > 0:
        df_kpi4['Porcentaje'] = (df_kpi4['Total_Fuga'] / total_fuga_general) * 100
        
    return df_kpi4
