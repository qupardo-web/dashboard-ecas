import dash
import plotly.express as px
from dash import dcc
from dash import html

FUGA_CACHE_ANUAL = {}

def get_kpi_data(kpi_func, year, kpi_key, db_engine):
    global FUGA_CACHE_ANUAL
    year_key = year if year is not None else 'ALL'
    
    # 1. Verificar si el año ya está en el caché
    if year_key not in FUGA_CACHE_ANUAL:
        FUGA_CACHE_ANUAL[year_key] = {}
        
    # 2. Verificar si el KPI específico ya está en el caché
    if kpi_key not in FUGA_CACHE_ANUAL[year_key]:
        # Si no está en caché, ejecutar la consulta y almacenar
        print(f"Buscando datos en DB para KPI {kpi_key} - Cohorte: {year_key}")
        df = kpi_func(db_engine, anio_n=year)
        FUGA_CACHE_ANUAL[year_key][kpi_key] = df
    else:
        print(f"Usando caché para KPI {kpi_key} - Cohorte: {year_key}")

    return FUGA_CACHE_ANUAL[year_key][kpi_key]

#Generador de graficos de barra
def generate_bar_chart(df, y_col, title):
    """
    Genera un gráfico de barras horizontales para KPIs de destino (2 o 3).
    Acepta un DataFrame con las columnas [Total_Fuga, Porcentaje, y_col].
    """
    
    # Manejo de datos vacíos
    if df.empty:
        return html.P(f"No hay datos disponibles para {title}.", style={'textAlign': 'center', 'color': 'gray'})
        
    # Seleccionar el Top 10 y ordenar para la visualización
    df_top = df.head(10).sort_values(by='Porcentaje', ascending=True)
    
    # Generar el gráfico de barras horizontales
    fig = px.bar(
        df_top, 
        x='Porcentaje', 
        y=y_col, # Usamos el argumento para la columna Y
        orientation='h', 
        title=title, 
        text='Porcentaje',
        template="plotly_white"
    )
    
    # Ajustes de formato (Iguales para KPI 2 y KPI 3)
    fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
    fig.update_layout(uniformtext_minsize=8, 
                      uniformtext_mode='hide', 
                      yaxis={'categoryorder': 'total ascending'})
                      
    return dcc.Graph(figure=fig)

def generate_pie_chart(df, names_col, values_col, title):
    
    # Manejo de datos vacíos
    if df.empty:
        return html.P(f"No hay datos de distribución disponibles para {title}.", 
                      style={'textAlign': 'center', 'color': 'gray'})
    
    # Generar el gráfico de pastel
    fig = px.pie(
        df, 
        names=names_col, 
        values=values_col, 
        title=title, 
        template="plotly_white"
    )
    
    # Ajustes de formato: mostrar el porcentaje y la etiqueta
    fig.update_traces(
        textposition='inside', 
        textinfo='percent+label',
        # Opción para ordenar las porciones por tamaño (opcional, pero útil)
        sort=True
    )
    
    fig.update_layout(
        showlegend=True,
        uniformtext_minsize=12,
        uniformtext_mode='hide'
    )
                      
    return dcc.Graph(figure=fig)