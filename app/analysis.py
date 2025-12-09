#Archivo para realizar visualizaciones con Dash

import dash
from dash import dcc
from dash import html
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np # Necesario para la función get_df_fuga_base (si no está ya importado en queries.py)
import os # Solo si necesitas configurar el entorno de conexión, aunque no se usa directamente en el código de Dash

DURACION_DIURNA_SEMESTRES = 8 # 4 años
DURACION_VESPERTINA_SEMESTRES = 9 # 4.5 años
# --- Importar todas las funciones de queries.py ---
# Asumimos que todas las funciones están en queries.py
from queries import (
    kpi1_permanencia_ecas,  
    kpi2_institucion_destino_opt,
    kpi3_carrera_destino
)
# Asumimos que get_db_engine viene de connector.py
from connector_db import get_db_engine

app = dash.Dash(__name__, title="ECAS Fuga y Permanencia")
engine = get_db_engine() # Establecer conexión a la DB

# Variables globales para los datos.
df_permanencia_full = pd.DataFrame()
tasa_general_permanencia = 0
years_available = []
FUGA_CACHE_ANUAL = {}

if engine is not None:
    try:
        # Carga del KPI más simple
        df_permanencia_full, tasa_general_permanencia = kpi1_permanencia_ecas(engine)
        years_available = sorted(df_permanencia_full['Año'])
    except Exception as e:
        print(f"❌ ERROR AL CARGAR KPI 1: {e}")
        df_permanencia_full = pd.DataFrame({'Año': [2007], 'Tasa_Permanencia_ECAS': [0]}) # DataFrame falso si falla la carga
else:
    print("❌ ERROR DE CONEXIÓN A LA DB.")

fig1 = px.line(df_permanencia_full, x='Año', y='Tasa_Permanencia_ECAS', 
               title=f'KPI 1: Tasa de Permanencia Anual en ECAS', markers=True,
               template="plotly_white")

# Añadir línea de promedio general
fig1.add_hline(y=tasa_general_permanencia, line_dash="dash", line_color="red",
               annotation_text=f"Promedio Total: {tasa_general_permanencia:.2f}%", 
               annotation_position="top right")

app.layout = html.Div(style={'backgroundColor': '#f8f9fa', 'padding': '20px'}, children=[
    html.H1("📈 Análisis de Permanencia y Fuga de Estudiantes ECAS", style={'textAlign': 'center', 'color': '#007bff', 'marginBottom': '20px'}),

    
    html.Hr(style={'borderColor': '#ced4da'}),

    # 2. CONTENEDOR DE SALIDA PARA KPI 1
    # Nota: Aquí se muestra fig1 inicialmente, pero el callback lo actualizará.
    html.Div(id='kpi1-output', 
             children=[dcc.Graph(figure=fig1)], # Mostrar fig1 como contenido inicial
             style={'padding': '20px', 'backgroundColor': 'white', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,.1)'}),
    
    html.Hr(style={'borderColor': '#ced4da', 'marginTop': '30px'}),

    html.Div(style={'width': '30%', 'margin': '0 auto 30px auto'}, children=[
        html.Label("Seleccionar Cohorte de Fuga (Año N -> N+1):", style={'fontWeight': 'bold', 'color': '#495057'}),
        
        # 1. COMPONENTE DE ENTRADA NECESARIO: year-selector
        dcc.Dropdown(
            id='year-selector', 
            options=years_available,
            value=2007, # Valor inicial: Total General
            clearable=False,
            style={'borderRadius': '5px'}
        )
    ]),

    # 3. CONTENEDORES DE SALIDA PARA KPI 2, 3, 4, 5
    html.Div(style={'display': 'flex', 'flexWrap': 'wrap', 'justifyContent': 'space-around', 'gap': '20px'}, children=[
        html.Div(id='kpi2-output', style={'width': '48%', 'minWidth': '300px', 'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,.1)'}),
        html.Div(id='kpi3-output', style={'width': '48%', 'minWidth': '300px', 'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,.1)'}),
        html.Div(id='kpi4-output', style={'width': '48%', 'minWidth': '300px', 'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,.1)'}),
        html.Div(id='kpi5-output', style={'width': '48%', 'minWidth': '300px', 'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,.1)'}),
    ])
])

@app.callback(
    [
        dash.Output('kpi1-output', 'children'),
        dash.Output('kpi2-output', 'children'), # <--- KPI 2 OUTPUT
        dash.Output('kpi3-output', 'children'),
        dash.Output('kpi4-output', 'children'),
        dash.Output('kpi5-output', 'children'),
    ],
    [dash.Input('year-selector', 'value')]
)
def update_dashboard(selected_year):
    
    # 1. Ajustar el parámetro para las queries
    if selected_year == 'ALL':
        anio_n_param = None
        title_suffix = "Total General"
    else:
        anio_n_param = selected_year
        title_suffix = f"Cohorte {selected_year} → {selected_year + 1}"
    
    # --- PASO 2: LÓGICA DE KPI 1 (SE MANTIENE IGUAL) ---
    # Esto asume que df_permanencia_full está disponible globalmente
    # ... (Cálculo y retorno de kpi1_chart) ...
    fig1 = px.line(df_permanencia_full, x='Año', y='Tasa_Permanencia_ECAS', 
                    title=f'KPI 1: Tasa de Permanencia Anual en ECAS', markers=True,
                    template="plotly_white", line_shape='spline')
    # ... (Añadir hline y vline) ...
    kpi1_chart = dcc.Graph(figure=fig1)
    
    try:
        # Ejecutar la consulta SQL optimizada para el KPI 2
        df_kpi2 = kpi2_institucion_destino_opt(engine, anio_n=anio_n_param)
        
        # Manejo de Datos Vacíos
        if df_kpi2.empty:
            kpi2_chart = html.P(f"No hay datos de fuga hacia otras instituciones para la {title_suffix}.", 
                                style={'textAlign': 'center', 'color': 'gray'})
        else:
            # Seleccionar Top 10 y ordenar para la visualización
            df_kpi2_top = df_kpi2.head(10).sort_values(by='Porcentaje', ascending=True)
            
            # Generar el Gráfico de Barras Horizontales
            fig2 = px.bar(df_kpi2_top, 
                          x='Porcentaje', 
                          y='INST_DESTINO', 
                          orientation='h',
                          title=f'KPI 2: Top 10 Instituciones de Destino ({title_suffix})',
                          text='Porcentaje',
                          template="plotly_white")
            
            # Ajustes de formato
            fig2.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
            fig2.update_layout(uniformtext_minsize=8, uniformtext_mode='hide', yaxis={'categoryorder': 'total ascending'})
            
            kpi2_chart = dcc.Graph(figure=fig2)

    except Exception as e:
        print(f"Error en KPI 2 para el año {selected_year}: {e}")
        error_msg = html.Div([
            html.P("Error al cargar KPI 2 (Fuga por Institución).", style={'color': 'darkred'}),
            html.Pre(f"Detalle: {e}")
        ])
        kpi2_chart = error_msg


    try:
        # 1. Obtener datos del KPI 3 (Consulta SQL)
        df_kpi3 = kpi3_carrera_destino(engine, anio_n=anio_n_param)

        # 2. Manejo de Datos Vacíos
        if df_kpi3.empty:
            kpi3_chart = html.P(f"No hay datos de fuga hacia otras carreras para la {title_suffix}.", 
                                 style={'textAlign': 'center', 'color': 'gray'})
        else:
            # INTEGRACIÓN COMPLETA DE PLOTLY DENTRO DEL CALLBACK (KPI 3)
            df_kpi3_top = df_kpi3.head(10).sort_values(by='Porcentaje', ascending=True)
            
            fig3 = px.bar(df_kpi3_top, 
                          x='Porcentaje', 
                          y='CARRERA_DESTINO', # Columna correcta
                          orientation='h',
                          title=f'KPI 3: Top 10 Carreras de Destino ({title_suffix})',
                          text='Porcentaje',
                          template="plotly_white")
            
            fig3.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
            fig3.update_layout(uniformtext_minsize=8, uniformtext_mode='hide', yaxis={'categoryorder': 'total ascending'})
            
            kpi3_chart = dcc.Graph(figure=fig3)

    except Exception as e:
        print(f"Error en KPI 3 para el año {selected_year}: {e}")
        error_msg = html.Div([
            html.P("Error al cargar KPI 3 (Fuga por Carrera).", style={'color': 'darkred'}),
            html.Pre(f"Detalle: {e}")
        ])
        kpi3_chart = error_msg

    empty_content = html.P("KPI no implementado aún.")
    kpi4_chart = empty_content
    kpi5_chart = empty_content

    # 5. Retornar todos los Outputs
    return kpi1_chart, kpi2_chart, kpi3_chart, kpi4_chart, kpi5_chart

if __name__ == '__main__':
    app.run(debug=True)