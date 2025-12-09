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
        mrun
    FROM 
        vista_matriculas_unificada 
    WHERE 
        cod_inst = {COD_INST_ECAS}
    GROUP BY cat_periodo, mrun; 
    """
    df_ecas = pd.read_sql(query_base, db_conn)
    
    lista_permanencia = []
    
    for anio_n in range(2007, 2025):
        anio_n_mas_1 = anio_n + 1
        
        # Estudiantes matriculados en ECAS en el año N
        mrun_anio_n_ecas = set(df_ecas[df_ecas['ANIO'] == anio_n]['mrun'])
        
        # Estudiantes matriculados en ECAS en el año N+1
        mrun_anio_n_mas_1_ecas = set(df_ecas[df_ecas['ANIO'] == anio_n_mas_1]['mrun'])
        
        if len(mrun_anio_n_ecas) > 0:
            estudiantes_permanecen = len(mrun_anio_n_ecas.intersection(mrun_anio_n_mas_1_ecas))
            tasa_permanencia = (estudiantes_permanecen / len(mrun_anio_n_ecas)) * 100
            
            lista_permanencia.append({
                'Año': anio_n,
                'Estudiantes_Iniciales_ECAS': len(mrun_anio_n_ecas),
                'Estudiantes_Permanecen_ECAS': estudiantes_permanecen,
                'Tasa_Permanencia_ECAS': round(tasa_permanencia, 2)
            })

    df_permanencia = pd.DataFrame(lista_permanencia)

    if anio:
        return df_permanencia[df_permanencia['Año'] == anio]
    else:
        tasa_general = df_permanencia['Tasa_Permanencia_ECAS'].mean()
        return df_permanencia, round(tasa_general, 2)

#Metodo para KPIs que calculan la fuga de estudiantes
def get_df_fuga_base(db_conn, anio_n=None):

    # 1. Obtener todos los datos clave de la vista unificada
    query_fuga_base = """
    SELECT 
        cat_periodo AS ANIO, 
        mrun, 
        cod_inst, 
        nomb_inst, 
        nomb_carrera, 
        area_conocimiento,
        dur_estudio_carr,  
        jornada,
        anio_ing_carr_ori
    FROM 
        vista_matriculas_unificada; 
    """
    df_completo = pd.read_sql(query_fuga_base, db_conn)
    
    df_fuga = pd.DataFrame()
    
    rango_anios = [anio_n] if anio_n else range(df_completo['ANIO'].min(), df_completo['ANIO'].max())
    
    for anio in rango_anios:
        anio_siguiente = anio + 1
        
        # a. Matrícula en Año N (solo ECAS - Origen)
        df_n_ecas = df_completo[(df_completo['ANIO'] == anio) & 
                                (df_completo['cod_inst'] == COD_INST_ECAS)].drop_duplicates(subset=['MRUN'])
        
        # LÓGICA DE EXCLUSIÓN
        df_n_ecas['Permanencia_Anios'] = df_n_ecas['ANIO'] - df_n_ecas['anio_ing_carr_ori']
        df_n_ecas['Permanencia_Semestres'] = df_n_ecas['Permanencia_Anios'] * 2
        df_n_ecas['Duracion_Teorica'] = np.where(
            df_n_ecas['jornada'].str.contains('Vespertino', na=False), 
            DURACION_VESPERTINA_SEMESTRES, 
            DURACION_DIURNA_SEMESTRES
        )
        
        # Filtrar: Estudiantes que AÚN NO han cumplido la duración teórica
        df_n_filtrado = df_n_ecas[df_n_ecas['Permanencia_Semestres'] < df_n_ecas['Duracion_Teorica']].copy()
        
        df_n_filtrado.rename(columns={'cod_inst': 'COD_INST_ORIGEN', 'nomb_inst': 'INST_ORIGEN', 'nomb_carrera': 'CARRERA_ORIGEN', 'area_conocimiento': 'AREA_ORIGEN'}, inplace=True)
        
        # b. Matrícula en Año N+1 (Destino)
        df_n_mas_1 = df_completo[df_completo['ANIO'] == anio_siguiente].drop_duplicates(subset=['MRUN'])
        df_n_mas_1.rename(columns={'cod_inst': 'COD_INST_DESTINO', 'nomb_inst': 'INST_DESTINO', 'nomb_carrera': 'CARRERA_DESTINO', 'area_conocimiento': 'AREA_DESTINO'}, inplace=True)
        
        # c. Combinar
        cols_origen = ['MRUN', 'INST_ORIGEN', 'CARRERA_ORIGEN', 'AREA_ORIGEN']
        cols_destino = ['MRUN', 'COD_INST_DESTINO', 'INST_DESTINO', 'CARRERA_DESTINO', 'AREA_DESTINO']
        df_merged = pd.merge(df_n_filtrado[cols_origen], df_n_mas_1[cols_destino], on='MRUN', how='inner')
        df_merged['ANIO_INICIAL'] = anio
        
        # d. Filtrar: Estudiantes que se fueron de ECAS (Fuga)
        df_fuga_anual = df_merged[df_merged['COD_INST_DESTINO'] != COD_INST_ECAS].copy()
        
        df_fuga = pd.concat([df_fuga, df_fuga_anual], ignore_index=True)

    return df_fuga

#KPI2: Calcula la institución de destino
def kpi2_institucion_destino(df_fuga):
    """Calcula el destino de la fuga (Institución)."""
    total_fuga = df_fuga['MRUN'].nunique()
    
    if total_fuga == 0:
        return pd.DataFrame(columns=['INST_DESTINO', 'Total_Fuga', 'Porcentaje'])

    kpi2_df = df_fuga.groupby('INST_DESTINO')['MRUN'].nunique().sort_values(ascending=False).reset_index(name='Total_Fuga')
    kpi2_df['Porcentaje'] = (kpi2_df['Total_Fuga'] / total_fuga) * 100
    
    return kpi2_df

#KPI3: Calcula la carrera de destino
def kpi3_carrera_destino(df_fuga):
    """Calcula el destino de la fuga (Carrera)."""
    total_fuga = df_fuga['MRUN'].nunique()
    
    if total_fuga == 0:
        return pd.DataFrame(columns=['CARRERA_DESTINO', 'Total_Fuga', 'Porcentaje'])
        
    kpi3_df = df_fuga.groupby('CARRERA_DESTINO')['MRUN'].nunique().sort_values(ascending=False).reset_index(name='Total_Fuga')
    kpi3_df['Porcentaje'] = (kpi3_df['Total_Fuga'] / total_fuga) * 100
    
    return kpi3_df

def kpi4_area_destino(df_fuga, solo_cambio=False):
    """
    Calcula la distribución de MRUNs por el Área de Conocimiento de Destino.
    Si solo_cambio=True, excluye a los que se quedaron en la misma área (si aplica).
    """
    
    # Crea la bandera de cambio (si se requiere para filtrar o etiquetar)
    df_fuga['CAMBIO_AREA'] = df_fuga['AREA_ORIGEN'] != df_fuga['AREA_DESTINO']

    if solo_cambio:
        df_analisis = df_fuga[df_fuga['CAMBIO_AREA'] == True].copy()
    else:
        # Usar todos los fugados para ver la distribución completa de destino
        df_analisis = df_fuga.copy()
    
    total_fuga = df_analisis['MRUN'].nunique()
    
    if total_fuga == 0:
        return pd.DataFrame(columns=['AREA_DESTINO', 'Total_Fuga', 'Porcentaje'])
        
    # Agrupar por el nombre del área de destino
    kpi4_df = df_analisis.groupby('AREA_DESTINO')['MRUN'].nunique().sort_values(ascending=False).reset_index(name='Total_Fuga')
    
    kpi4_df['Porcentaje'] = (kpi4_df['Total_Fuga'] / total_fuga) * 100
    
    return kpi4_df

#KPI 5: Estima la titulación de aquellos estudiantes que se fugaron.
def kpi5_titulacion_fuga_estimada(db_conn, anio_n=None):
    
    # 1. Obtener la lista de MRUN que se fugaron de ECAS, usando la nueva función base.
    # Esta llamada YA incluye la lógica de exclusión de titulados estimados de ECAS.
    try:
        # Llamar a la función base y obtener el DataFrame de MRUNs fugados
        df_fuga = get_df_fuga_base(db_conn, anio_n=anio_n)
    except NameError:
        print("Error: get_df_fuga_base no está definida o no puede ejecutarse.")
        return pd.DataFrame({'NOMB_CARRERA': [], 'Titulados_Estimados': []}), 0

    mruns_fugados = df_fuga['MRUN'].unique()
    
    if len(mruns_fugados) == 0:
        return pd.DataFrame({'NOMB_CARRERA': [], 'Titulados_Estimados': []}), 0

    # 2. Obtener la historia completa de matrículas (después de la fuga) para los MRUNs fugados.
    mrun_list_str = ', '.join([f"'{mrun}'" for mrun in mruns_fugados])
    
    # Se consulta la historia de matrícula de los fugados.
    query_titulacion = f"""
    SELECT 
        mrun, 
        cat_periodo AS ANIO, 
        codigo_unico, 
        nomb_carrera,
        CAST(dur_total_carr AS INT) AS DURACION_SEMESTRES
    FROM 
        vista_matriculas_unificada 
    WHERE 
        mrun IN ({mrun_list_str}) AND
        dur_total_carr IS NOT NULL 
    """
    df_historia = pd.read_sql(query_titulacion, db_conn)
    
    df_ultima_matricula = df_historia.groupby('MRUN')['ANIO'].max().reset_index(name='Ultimo_ANIO')
    df_final = pd.merge(df_historia, df_ultima_matricula, on=['MRUN', 'ANIO'])
    df_ultima_carrera = df_final.sort_values(by=['MRUN', 'ANIO'], ascending=False).drop_duplicates(subset=['MRUN'])
    
    df_ultima_carrera['CLAVE_CARRERA_FINAL'] = df_ultima_carrera['MRUN'].astype(str) + '_' + df_ultima_carrera['CODIGO_UNICO'].astype(str)
    df_historia['CLAVE_CARRERA_FINAL'] = df_historia['MRUN'].astype(str) + '_' + df_historia['CODIGO_UNICO'].astype(str)

    claves_finales = df_ultima_carrera['CLAVE_CARRERA_FINAL'].unique()
    df_permanencia_final = df_historia[df_historia['CLAVE_CARRERA_FINAL'].isin(claves_finales)].copy()

    df_permanencia_carrera = df_permanencia_final.groupby(['MRUN', 'CODIGO_UNICO', 'nomb_carrera', 'DURACION_SEMESTRES']).agg(
        Anios_Matriculado=('ANIO', 'nunique')
    ).reset_index()
    
    df_permanencia_carrera['Duracion_Anios_Teorica'] = df_permanencia_carrera['DURACION_SEMESTRES'] / 2
    
    df_titulados_estimados = df_permanencia_carrera[
        df_permanencia_carrera['Anios_Matriculado'] >= df_permanencia_carrera['Duracion_Anios_Teorica']
    ].copy()
    
    total_estimado = df_titulados_estimados['MRUN'].nunique()
    resultados_carrera = df_titulados_estimados.groupby('nomb_carrera')['MRUN'].nunique().reset_index(name='Titulados_Estimados')
    
    return resultados_carrera, total_estimado