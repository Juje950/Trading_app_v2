import plotly.express as px
import plotly.graph_objects as go
from config import COLORES_INVERSORES

class PlotGenerator:
    @staticmethod
    def create_combined_chart(df, investor=None):
        """Crea gráfico combinado de capital y ganancias"""
        if investor:
            df = df[df['Inversor'] == investor]
        
        fig = go.Figure()
        
        # Línea punteada para capital
        fig.add_trace(go.Scatter(
            x=df['Fecha'],
            y=df['Capital'],
            name='Capital',
            line=dict(dash='dot', color='#636EFA'),
            mode='lines'
        ))
        
        # Línea sólida para ganancias
        fig.add_trace(go.Scatter(
            x=df['Fecha'],
            y=df['Ganancia'],
            name='Ganancia',
            line=dict(color='#00CC96'),
            mode='lines'
        ))
        
        # Configuración del layout
        fig.update_layout(
            title='Evolución de Capital y Ganancias' + (f' - {investor}' if investor else ''),
            xaxis_title='Fecha',
            yaxis_title='Monto (USD)',
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            separators=',.'
        )
        
        return fig
    
    @staticmethod
    def create_pie_chart(df, values_col, names_col, title):
        """Crea gráfico de torta para distribución"""
        fig = px.pie(
            df,
            values=values_col,
            names=names_col,
            title=title,
            color=names_col,
            color_discrete_map=COLORES_INVERSORES
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        return fig
    
    @staticmethod
    def create_bar_chart(df, x_col, y_col, color_col=None, title='', barmode='group'):
        """Crea gráfico de barras agrupadas"""
        fig = px.bar(
            df,
            x=x_col,
            y=y_col,
            color=color_col,
            title=title,
            barmode=barmode,
            color_discrete_map=COLORES_INVERSORES
        )
        fig.update_layout(
            xaxis_title=x_col,
            yaxis_title=y_col,
            hovermode='x unified',
            yaxis_tickformat=',.2f'
        )
        return fig
