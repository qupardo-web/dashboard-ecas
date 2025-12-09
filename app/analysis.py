#Archivo para realizar visualizaciones con Dash

import dash
from dash import dcc
from dash import html
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from queries import (
    kpi1_permanencia_ecas,  
    kpi2_institucion_destino_opt,
    kpi3_carrera_destino
)
from connector_db import get_db_engine
from graphics_gen import generate_bar_chart

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

    fig1 = px.line(df_permanencia_full, x='Año', y='Tasa_Permanencia_ECAS', 
                    title=f'KPI 1: Tasa de Permanencia Anual en ECAS', markers=True,
                    template="plotly_white", line_shape='spline')
    # ... (Añadir hline y vline) ...
    kpi1_chart = dcc.Graph(figure=fig1)
    
    df_kpi2 = kpi2_institucion_destino_opt(engine, anio_n=anio_n_param)

    institucion = 'INST_DESTINO'
    titulo = f'KPI 2: Top 10 Instituciones de Destino ({title_suffix})'
    kpi2_chart = generate_bar_chart(df_kpi2, institucion, titulo)

    df_kpi3 = kpi3_carrera_destino(engine, anio_n=anio_n_param)

    carrera= 'CARRERA_DESTINO'
    titulo = f'KPI 3: Top 10 Carreras de Destino ({title_suffix})'
    kpi3_chart = generate_bar_chart(df_kpi3, carrera, titulo)

    empty_content = html.P("KPI no implementado aún.")
    kpi4_chart = empty_content
    kpi5_chart = empty_content

    # 5. Retornar todos los Outputs
    return kpi1_chart, kpi2_chart, kpi3_chart, kpi4_chart, kpi5_chart

if __name__ == '__main__':
    app.run(debug=True)