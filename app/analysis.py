#Archivo para realizar visualizaciones con Dash

import dash
from dash import dcc
from dash import html
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np # Necesario para la función get_df_fuga_base (si no está ya importado en queries.py)
import os # Solo si necesitas configurar el entorno de conexión, aunque no se usa directamente en el código de Dash

# --- Importar todas las funciones de queries.py ---
# Asumimos que todas las funciones están en queries.py
from queries import (
    kpi1_permanencia_ecas, 
    get_df_fuga_base, 
    kpi2_institucion_destino,
    kpi3_carrera_destino,
    kpi4_area_destino,
    kpi5_titulacion_fuga_estimada
)
# Asumimos que get_db_engine viene de connector.py
from connector_db import get_db_engine

app = dash.Dash(__name__, title="ECAS Fuga y Permanencia")
engine = get_db_engine() # Establecer conexión a la DB

# Obtener la lista de años disponibles (para el Dropdown) y la tasa promedio para KPI 1
try:
    df_permanencia_full, tasa_general_permanencia = kpi1_permanencia_ecas(engine)
    years_available = sorted(df_permanencia_full['Año'].unique())
except Exception as e:
    print(f"Error al cargar datos iniciales de permanencia: {e}")
    df_permanencia_full = pd.DataFrame()
    tasa_general_permanencia = 0
    years_available = []

# Opciones para el Dropdown
year_options = [{'label': 'Total General (Promedio)', 'value': 'ALL'}]
if years_available:
    year_options.extend([{'label': str(y), 'value': y} for y in years_available])

app.layout = html.Div(style={'backgroundColor': '#f8f9fa', 'padding': '20px'}, children=[
    html.H1("📈 Análisis de Permanencia y Fuga de Estudiantes ECAS", style={'textAlign': 'center', 'color': '#007bff', 'marginBottom': '20px'}),
    
    html.Div(style={'width': '30%', 'margin': '0 auto 30px auto'}, children=[
        html.Label("Seleccionar Cohorte de Fuga (Año N -> N+1):", style={'fontWeight': 'bold', 'color': '#495057'}),
        dcc.Dropdown(
            id='year-selector',
            options=year_options,
            value='ALL', # Valor inicial: Total General
            clearable=False,
            style={'borderRadius': '5px'}
        )
    ]),
    
    html.Hr(style={'borderColor': '#ced4da'}),

    # Contenedor para la Gráfica de Permanencia (KPI 1)
    html.Div(id='kpi1-output', style={'padding': '20px', 'backgroundColor': 'white', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,.1)'}),
    
    html.Hr(style={'borderColor': '#ced4da', 'marginTop': '30px'}),

    # Contenedores para Gráficos de Fuga (KPI 2, 3, 4 y 5)
    html.Div(style={'display': 'flex', 'flexWrap': 'wrap', 'justifyContent': 'space-around', 'gap': '20px'}, children=[
        html.Div(id='kpi2-output', style={'width': '48%', 'minWidth': '300px', 'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,.1)'}),
        html.Div(id='kpi3-output', style={'width': '48%', 'minWidth': '300px', 'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,.1)'}),
        html.Div(id='kpi4-output', style={'width': '48%', 'minWidth': '300px', 'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,.1)'}),
        html.Div(id='kpi5-output', style={'width': '48%', 'minWidth': '300px', 'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,.1)'}),
    ])
])

# ----------------------------------------------------------------------
# 3. DEFINICIÓN DEL CALLBACK (Manejo de la Interacción)
# ----------------------------------------------------------------------

@app.callback(
    [
        dash.Output('kpi1-output', 'children'),
        dash.Output('kpi2-output', 'children'),
        dash.Output('kpi3-output', 'children'),
        dash.Output('kpi4-output', 'children'),
        dash.Output('kpi5-output', 'children'),
    ],
    [dash.Input('year-selector', 'value')]
)
def update_dashboard(selected_year):
    
    # 1. Ajustar el parámetro para las queries
    if selected_year == 'ALL':
        # Cuando es 'ALL', la query debe procesar el total (anio_n=None)
        anio_n_param = None
        title_suffix = "Total General"
    else:
        # Cuando es un año, la query debe filtrar por esa cohorte
        anio_n_param = selected_year
        title_suffix = f"Cohorte {selected_year} → {selected_year + 1}"
    
    # 2. Lógica y Gráficos para KPI 1 (Permanencia)
    
    # KPI 1 siempre usa la serie completa para mostrar el contexto temporal
    fig1 = px.line(df_permanencia_full, x='Año', y='Tasa_Permanencia_ECAS', 
                   title=f'KPI 1: Tasa de Permanencia Anual en ECAS', markers=True,
                   template="plotly_white", line_shape='spline')
    
    # Añadir línea de promedio general
    fig1.add_hline(y=tasa_general_permanencia, line_dash="dash", line_color="red",
                   annotation_text=f"Promedio Total: {tasa_general_permanencia}%", 
                   annotation_position="top right")
    
    # Resaltar el año seleccionado
    if selected_year != 'ALL':
         fig1.add_vline(x=selected_year, line_dash="dot", line_color="blue", opacity=0.8)
         # Mostrar la tasa específica del año seleccionado
         tasa_anual = df_permanencia_full[df_permanencia_full['Año'] == selected_year]['Tasa_Permanencia_ECAS'].iloc[0]
         fig1.add_annotation(x=selected_year, y=tasa_anual, text=f"{tasa_anual}%", showarrow=True, arrowhead=1)

    kpi1_chart = dcc.Graph(figure=fig1)

    
    # 3. Lógica y Gráficos para KPI 2, 3, 4 y 5 (Fuga y Destino)

    # Obtener el DataFrame base de fugados (una sola llamada optimizada)
    df_fuga = get_df_fuga_base(engine, anio_n=anio_n_param)
    
    # Si no hay fugados, mostrar mensajes de "Datos no disponibles"
    if df_fuga.empty:
        empty_message = html.P(f"No hay datos de fuga disponibles para la {title_suffix}.", style={'textAlign': 'center', 'color': 'gray'})
        empty_chart = dcc.Graph(figure=go.Figure())
        return kpi1_chart, empty_message, empty_message, empty_message, empty_message

    
    # --- KPI 2: Institución de Destino ---
    df_kpi2 = kpi2_institucion_destino(df_fuga)
    df_kpi2_top = df_kpi2.head(10).sort_values(by='Porcentaje', ascending=True)
    fig2 = px.bar(df_kpi2_top, x='Porcentaje', y='INST_DESTINO', orientation='h',
                  title=f'KPI 2: Top 10 Instituciones de Destino ({title_suffix})',
                  text='Porcentaje', template="plotly_white")
    fig2.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
    fig2.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
    kpi2_chart = dcc.Graph(figure=fig2)


    # --- KPI 3: Carrera de Destino ---
    df_kpi3 = kpi3_carrera_destino(df_fuga)
    df_kpi3_top = df_kpi3.head(10).sort_values(by='Porcentaje', ascending=True)
    fig3 = px.bar(df_kpi3_top, x='Porcentaje', y='CARRERA_DESTINO', orientation='h',
                  title=f'KPI 3: Top 10 Carreras de Destino ({title_suffix})',
                  text='Porcentaje', template="plotly_white")
    fig3.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
    fig3.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
    kpi3_chart = dcc.Graph(figure=fig3)


    # --- KPI 4: Cambio de Área ---
    df_kpi4 = kpi4_area_destino(df_fuga, solo_cambio=False) # Analiza la distribución de ÁREAS de destino (no solo Sí/No)
    fig4 = px.pie(df_kpi4, names='AREA_DESTINO', values='Total_Fuga',
                  title=f'KPI 4: Distribución de Fuga por Área de Destino ({title_suffix})',
                  template="plotly_white")
    fig4.update_traces(textposition='inside', textinfo='percent+label')
    kpi4_chart = dcc.Graph(figure=fig4)
    
    
    # --- KPI 5: Titulación Estimada ---
    df_kpi5, total_estimado = kpi5_titulacion_fuga_estimada(engine, anio_n=anio_n_param)
    
    if df_kpi5.empty:
        fig5 = go.Figure().update_layout(title=f'KPI 5: Titulación Estimada ({title_suffix})', annotations=[dict(text="No hay titulados estimados en esta cohorte.", showarrow=False)])
    else:
        # Mostrar las 10 carreras con mayor estimación de titulación
        df_kpi5_top = df_kpi5.head(10).sort_values(by='Titulados_Estimados', ascending=True)
        fig5 = px.bar(df_kpi5_top, x='Titulados_Estimados', y='nomb_carrera', orientation='h',
                      title=f'KPI 5: Titulación Estimada en Carreras de Destino (Total: {total_estimado})',
                      template="plotly_white")
        fig5.update_traces(texttemplate='%{x}', textposition='outside')
        fig5.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
        
    kpi5_chart = dcc.Graph(figure=fig5)


    # 4. Retornar todos los gráficos
    return kpi1_chart, kpi2_chart, kpi3_chart, kpi4_chart, kpi5_chart

if __name__ == '__main__':
    app.run(debug=True)