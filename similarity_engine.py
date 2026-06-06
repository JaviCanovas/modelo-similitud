import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity

def cargar_datos(ruta_csv: str) -> pd.DataFrame:
    """Carga el CSV de delanteros procesados."""
    return pd.read_csv(ruta_csv)

def obtener_metricas_clave() -> list[str]:
    """Retorna la lista de columnas métricas usadas en el modelo."""
    return ['gls_per90', 'ast_per90', 'sh_per90', 'sot_pct', 'goals_per_shot', 'goals_per_sot', 'sot_per90']

def ajustar_metricas_por_coeficiente(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ajusta las métricas multiplicándolas por el coeficiente de dificultad de la liga.
    España (La Liga) = 1.0
    Bélgica (Pro League) = 0.85
    """
    coeficientes = {
        'ESP-La Liga': 1.0,
        'BEL-Pro League': 0.85
    }
    
    df_ajustado = df.copy()
    metricas = obtener_metricas_clave()
    
    # Mapeamos la liga a su coeficiente, default 1.0
    factor = df_ajustado['league'].map(coeficientes).fillna(1.0)
    
    for m in metricas:
        if m in df_ajustado.columns:
            df_ajustado[m] = df_ajustado[m] * factor
            
    return df_ajustado

def calcular_similitud(df: pd.DataFrame, jugador_objetivo: str) -> pd.DataFrame:
    """
    1. Extrae las columnas métricas clave.
    2. Aplica StandardScaler (Z-score) a toda la matriz.
    3. Identifica el vector del jugador objetivo.
    4. Calcula cosine_similarity contra el resto.
    5. Convierte a porcentaje (0-100%).
    6. Retorna DataFrame ordenado descendente con columnas:
       [player, team, age, league, similitud_%]
    """
    metricas = obtener_metricas_clave()
    
    # Asegurarnos de que las métricas existen en el df
    metricas_existentes = [m for m in metricas if m in df.columns]
    
    if len(metricas_existentes) == 0:
        raise ValueError("No se encontraron las columnas de métricas clave en el DataFrame.")
        
    df_modelo = df.dropna(subset=metricas_existentes).copy()
    
    if jugador_objetivo not in df_modelo['player'].values:
        raise ValueError(f"Jugador objetivo '{jugador_objetivo}' no encontrado en los datos.")
        
    # Extraemos la matriz de características
    X = df_modelo[metricas_existentes].values
    
    # Estandarizamos (Z-score)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Buscamos el índice del jugador objetivo
    idx_objetivo = df_modelo.index[df_modelo['player'] == jugador_objetivo].tolist()[0]
    
    # Vector del jugador estandarizado
    # StandardScaler mantiene el orden de filas, pero index_objetivo es del index de pandas.
    # Dado que reseteamos y no cambiamos el orden, es mejor usar la posición iloc
    pos_objetivo = df_modelo.index.get_loc(idx_objetivo)
    vector_objetivo = X_scaled[pos_objetivo].reshape(1, -1)
    
    # Calculamos similitud de coseno
    similitudes = cosine_similarity(X_scaled, vector_objetivo).flatten()
    
    # Rango de coseno es [-1, 1], mapeamos a [0, 100]
    # Transformación lineal: (sim + 1) / 2 * 100
    # O más sencillo, tomar max(0, sim) * 100 si asumimos que negativos no son similares
    # Utilizaremos (sim + 1) / 2 * 100 para un mapeo completo
    similitudes_pct = ((similitudes + 1) / 2) * 100
    
    # Añadimos resultados al dataframe original
    df_res = df_modelo.copy()
    df_res['similitud_%'] = similitudes_pct
    
    # Ordenamos
    df_res = df_res.sort_values(by='similitud_%', ascending=False)
    
    # Devolvemos solo las columnas relevantes
    columnas_out = ['player', 'team', 'age', 'league', 'similitud_%'] + metricas_existentes
    # Si alguna columna base no existe, la ignoramos
    columnas_out = [c for c in columnas_out if c in df_res.columns]
    
    return df_res[columnas_out]

def obtener_top_n(df_similitud: pd.DataFrame, jugador_objetivo: str, n: int = 5) -> pd.DataFrame:
    """Retorna los N jugadores más similares (excluyendo al objetivo)."""
    df_filtrado = df_similitud[df_similitud['player'] != jugador_objetivo]
    return df_filtrado.head(n)
