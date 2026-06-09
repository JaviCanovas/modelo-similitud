import streamlit as st
import os
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client
from similarity_engine import cargar_datos, calcular_similitud, obtener_top_n, ajustar_metricas_por_coeficiente
from utils import crear_radar_chart, formatear_porcentaje

st.set_page_config(
    page_title="Scouting IA - Similitud",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo personalizado (Modo Oscuro profesional BeScout)
st.markdown("""
<style>
    .reportview-container {
        background: #0f172a;
        color: #f8fafc;
    }
    .sidebar .sidebar-content {
        background: #1e293b;
    }
    h1, h2, h3 {
        color: #e2e8f0;
    }
    .metric-value {
        font-size: 1.5rem;
        font-weight: bold;
        color: #10b981; /* emerald */
    }
</style>
""", unsafe_allow_html=True)

CSV_PATH = 'delanteros_procesados.csv'

@st.cache_data
def load_data():
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    if url and key:
        try:
            supabase: Client = create_client(url, key)
            response = supabase.table("delanteros").select("*").execute()
            if response.data:
                df = pd.DataFrame(response.data)
                return ajustar_metricas_por_coeficiente(df)
        except Exception as e:
            st.error(f"Error conectando a Supabase: {e}")
            
    # Fallback to CSV if Supabase fails or is not configured
    if not os.path.exists(CSV_PATH):
        return None
    df = cargar_datos(CSV_PATH)
    return ajustar_metricas_por_coeficiente(df)

def main():
    st.sidebar.title("⚽ Motor de Similitud")
    st.sidebar.markdown("---")
    
    df = load_data()
    
    if df is None:
        st.error(f"No se encontró el archivo `{CSV_PATH}`. Por favor, ejecuta primero `python data_pipeline.py` para generar los datos.")
        return
    
    # 1. Filtro de Liga Objetivo
    ligas_disponibles = ['Todas'] + df['league'].dropna().unique().tolist()
    liga_objetivo = st.sidebar.selectbox("Liga Objetivo", options=ligas_disponibles)
    
    if liga_objetivo == 'Todas':
        df_filtrado = df.copy()
    else:
        df_filtrado = df[df['league'] == liga_objetivo]
        
    if df_filtrado.empty:
        st.sidebar.warning("No hay jugadores en esta liga.")
        return
        
    # 2. Selección de Jugador a Reemplazar
    # El usuario podría querer buscar el reemplazo de cualquier jugador de la bbdd completa,
    # pero mostraremos los de la bbdd completa para buscar reemplazo en la liga objetivo,
    # o bien buscar un jugador que juegue en la liga filtrada. Asumimos lo segundo por simplicidad,
    # pero lo ideal es seleccionar de TODOS los jugadores y buscar en la LIGA OBJETIVO.
    jugadores_disponibles = sorted(df['player'].dropna().unique().tolist())
    jugador_seleccionado = st.sidebar.selectbox("Jugador a reemplazar", options=jugadores_disponibles)
    
    if st.sidebar.button("Buscar Similares", type="primary"):
        # Calculamos similitud contra todos (para obtener el vector base correctamente)
        try:
            df_sim = calcular_similitud(df, jugador_seleccionado)
        except Exception as e:
            st.error(f"Error al calcular similitud: {e}")
            return
            
        # Filtramos los resultados por la liga objetivo
        if liga_objetivo != 'Todas':
            df_sim = df_sim[df_sim['league'] == liga_objetivo]
            
        # Obtenemos top N (excluyendo al propio jugador si está en la misma liga)
        top_n = obtener_top_n(df_sim, jugador_seleccionado, n=5)
        
        if top_n.empty:
            st.info("No se encontraron candidatos suficientes en la liga objetivo.")
            return
            
        st.title(f"🔍 Buscando reemplazo para: {jugador_seleccionado}")
        
        # Info del jugador base
        datos_base = df[df['player'] == jugador_seleccionado].iloc[0].to_dict()
        st.markdown(f"**Equipo:** {datos_base.get('team', 'N/A')} | **Liga:** {datos_base.get('league', 'N/A')} | **Edad:** {datos_base.get('age', 'N/A')}")
        st.markdown("---")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("🏆 Ranking de Similitud (Top 5)")
            
            # Formatear salida
            df_display = top_n[['player', 'team', 'age', 'league', 'similitud_%']].copy()
            df_display['similitud_%'] = df_display['similitud_%'].apply(formatear_porcentaje)
            
            # Renombrar columnas para mostrar
            df_display = df_display.rename(columns={
                'player': 'Nombre',
                'team': 'Equipo',
                'age': 'Edad',
                'league': 'Liga',
                'similitud_%': '% Similitud'
            })
            
            st.dataframe(
                df_display, 
                use_container_width=True,
                hide_index=True
            )
            
        with col2:
            st.subheader("📊 Comparativa vs Candidato #1")
            
            candidato_1 = top_n.iloc[0].to_dict()
            sim_pct = formatear_porcentaje(candidato_1.get('similitud_%', 0))
            st.markdown(f"**{candidato_1.get('player')}** — Similitud: <span class='metric-value'>{sim_pct}</span>", unsafe_allow_html=True)
            
            from similarity_engine import obtener_metricas_clave
            metricas = obtener_metricas_clave()
            
            # Normalizamos para el radar usando el maximo del dataset
            fig = crear_radar_chart(datos_base, candidato_1, metricas, df)
            st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
