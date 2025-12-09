import dash
import plotly.express as px
from dash import dcc
from dash import html

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
