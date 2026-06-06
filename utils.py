import pandas as pd
import plotly.graph_objects as go

def crear_radar_chart(jugador_base: dict, jugador_candidato: dict, metricas: list[str], df: pd.DataFrame = None) -> go.Figure:
    """
    Genera un Spider Chart (radar) con Plotly superponiendo
    las estadísticas del jugador a reemplazar vs. el candidato #1.
    """
    # Nombres amigables para las métricas
    nombres_metricas = {
        'gls_per90': 'Goles por 90',
        'ast_per90': 'Asistencias por 90',
        'sh_per90': 'Tiros por 90',
        'sot_pct': '% Tiros a Puerta',
        'goals_per_shot': 'Goles / Tiro',
        'goals_per_sot': 'Goles / Tiro a Puerta',
        'sot_per90': 'Tiros a Puerta por 90'
    }
    
    categorias = [nombres_metricas.get(m, m) for m in metricas]
    
    # Extraer valores, si hay None o NaN lo ponemos a 0
    valores_base = []
    valores_cand = []
    
    for m in metricas:
        v_base = jugador_base.get(m, 0)
        v_cand = jugador_candidato.get(m, 0)
        
        # Lógica básica de limpieza
        try:
            v_base = float(v_base)
            import math
            if math.isnan(v_base): v_base = 0.0
        except:
            v_base = 0.0
            
        try:
            v_cand = float(v_cand)
            import math
            if math.isnan(v_cand): v_cand = 0.0
        except:
            v_cand = 0.0
            
        # Normalización por Percentiles (0.0 a 1.0)
        if df is not None and m in df.columns:
            s = df[m].dropna()
            if not s.empty:
                v_base = (s <= v_base).mean()
                v_cand = (s <= v_cand).mean()
            else:
                v_base = 0.0
                v_cand = 0.0
                
        valores_base.append(v_base)
        valores_cand.append(v_cand)
        
    # Plotly requiere cerrar el círculo repitiendo el primer valor
    categorias.append(categorias[0])
    valores_base.append(valores_base[0])
    valores_cand.append(valores_cand[0])
    
    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=valores_base,
        theta=categorias,
        fill='toself',
        name=jugador_base.get('player', 'Jugador Base'),
        line=dict(color='cyan')
    ))
    
    fig.add_trace(go.Scatterpolar(
        r=valores_cand,
        theta=categorias,
        fill='toself',
        name=jugador_candidato.get('player', 'Candidato'),
        line=dict(color='#10b981') # emerald-500 en Tailwind
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                showticklabels=False, # Ocultamos los números porque las escalas son distintas
                range=[0, 1]          # Fijamos el límite exterior para los percentiles
            )
        ),
        showlegend=True,
        template="plotly_dark",
        margin=dict(l=40, r=40, t=40, b=40)
    )
    
    return fig

def formatear_porcentaje(valor: float) -> str:
    """Formatea un float como porcentaje con 1 decimal."""
    return f"{valor:.1f}%"
