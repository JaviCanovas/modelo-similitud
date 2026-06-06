import pandas as pd
import soccerdata as sd
import logging
import traceback
import os
from dotenv import load_dotenv
from supabase import create_client, Client

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def run_pipeline():
    try:
        # Extraemos la temporada 2025-2026. soccerdata usa el formato '2526' para la 25/26.
        season = '2526' 
        
        logging.info(f"Iniciando extracción de datos para la temporada {season}...")
        try:
            fbref = sd.FBref(leagues=["ESP-La Liga", "BEL-Pro League", "ESP-La Liga 2"], seasons=season)
        except ValueError as ve:
            logging.warning(f"Error cargando ligas: {ve}")
            logging.info("Haciendo fallback a 'ESP-La Liga' y 'BEL-Pro League'.")
            fbref = sd.FBref(leagues=["ESP-La Liga", "BEL-Pro League"], seasons=season)
        
        logging.info("Extrayendo tabla 'standard'...")
        df_standard = fbref.read_player_season_stats(stat_type="standard")
        
        logging.info("Extrayendo tabla 'shooting'...")
        df_shooting = fbref.read_player_season_stats(stat_type="shooting")
        
        # soccerdata genera MultiIndex (league, season, team, player). Reseteamos.
        df_standard = df_standard.reset_index()
        df_shooting = df_shooting.reset_index()
        
        logging.info("Uniendo tablas...")
        merge_cols = ['league', 'season', 'team', 'player']
        df_merged = pd.merge(df_standard, df_shooting, on=merge_cols, how='inner', suffixes=('', '_shoot'))
        
        # Normalizar nombres de columnas a nivel plano si son MultiIndex (a veces soccerdata devuelve tuplas)
        if isinstance(df_merged.columns, pd.MultiIndex):
            df_merged.columns = ['_'.join([str(c) for c in col]).strip('_') for col in df_merged.columns.values]

        logging.info("Filtrando por posición (FW, MF,FW) y minutos jugados (>= 600)...")
        
        def get_col(df, possible_names):
            for name in possible_names:
                for col in df.columns:
                    if col.lower() == name.lower():
                        return col
            return None

        pos_col = get_col(df_merged, ['pos', 'position'])
        if pos_col is None:
            logging.error(f"No se encontró columna de posición. Columnas disponibles: {df_merged.columns.tolist()}")
            return

        df_filtered = df_merged[df_merged[pos_col].isin(['FW', 'MF,FW', 'FW,MF'])]
        
        min_col = get_col(df_filtered, ['Playing Time_Min', 'playing time_min', 'min', 'minutes'])
        if min_col is None:
            logging.error(f"No se encontró columna de minutos. Columnas: {df_filtered.columns.tolist()}")
            return

        df_filtered[min_col] = pd.to_numeric(df_filtered[min_col], errors='coerce').fillna(0)
        df_filtered = df_filtered[df_filtered[min_col] >= 600].copy()
        logging.info(f"Jugadores tras filtros: {len(df_filtered)}")
        
        if len(df_filtered) == 0:
            logging.warning("No hay jugadores tras aplicar filtros. Revisa si hay datos para la temporada seleccionada.")
            return

        # Métricas Clave (adaptadas a los datos básicos disponibles en la API gratuita de FBref actualmente)
        # Añadimos métricas ofensivas solicitadas: Goals/Shot, Goals/Shot on Target, Shots on Target/90
        col_gls = get_col(df_filtered, ['Per 90 Minutes_Gls'])
        col_ast = get_col(df_filtered, ['Per 90 Minutes_Ast'])
        col_sh = get_col(df_filtered, ['Standard_Sh/90_shoot', 'Standard_Sh/90'])
        col_sot_pct = get_col(df_filtered, ['Standard_SoT%_shoot', 'Standard_SoT%'])
        
        # Nuevas métricas
        col_g_sh = get_col(df_filtered, ['Standard_G/Sh_shoot', 'Standard_G/Sh'])
        col_g_sot = get_col(df_filtered, ['Standard_G/SoT_shoot', 'Standard_G/SoT'])
        col_sot_90 = get_col(df_filtered, ['Standard_SoT/90_shoot', 'Standard_SoT/90'])

        metricas_finales = {
            'gls_per90': col_gls,
            'ast_per90': col_ast,
            'sh_per90': col_sh,
            'sot_pct': col_sot_pct,
            'goals_per_shot': col_g_sh,
            'goals_per_sot': col_g_sot,
            'sot_per90': col_sot_90
        }

        for m_name, m_col in metricas_finales.items():
            if m_col is None:
                logging.warning(f"No se encontró columna para métrica: {m_name}")
            else:
                df_filtered[m_col] = pd.to_numeric(df_filtered[m_col], errors='coerce').fillna(0)

        # Seleccionar y renombrar columnas
        cols_base = ['player', 'team', 'league', 'age']
        cols_base_found = [get_col(df_filtered, [c]) for c in cols_base]
        
        final_cols = [c for c in cols_base_found if c is not None]
        rename_dict = {bf: b for b, bf in zip(cols_base, cols_base_found) if bf}
        
        for m_name, m_col in metricas_finales.items():
            if m_col:
                final_cols.append(m_col)
                rename_dict[m_col] = m_name

        df_final = df_filtered[final_cols].rename(columns=rename_dict)
        
        # Manejar múltiples filas del mismo jugador (ej: traspasos a mitad de temporada)
        # Nos quedamos con la fila original por ahora
        df_final = df_final.drop_duplicates(subset=['player'])

        # Guardar en CSV local (backup)
        out_file = 'delanteros_procesados.csv'
        df_final.to_csv(out_file, index=False)
        logging.info(f"Datos guardados en CSV local {out_file} ({len(df_final)} jugadores).")

        # Guardar en Supabase
        load_dotenv()
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
        if url and key:
            logging.info("Conectando a Supabase para subir los datos...")
            supabase: Client = create_client(url, key)
            
            # Convertimos a diccionario de registros reemplazando NaNs si los hubiera
            # En Pandas fillna(0) ya se aplicó, así que debería estar limpio
            records = df_final.to_dict(orient='records')
            
            try:
                response = supabase.table("delanteros").upsert(records, on_conflict="player").execute()
                logging.info(f"Subida a Supabase exitosa. Se han procesado {len(records)} registros.")
            except Exception as supa_err:
                logging.error(f"Error al subir a Supabase: {supa_err}")
        else:
            logging.warning("Variables SUPABASE_URL o SUPABASE_KEY no encontradas. Saltando subida a base de datos.")
            
        logging.info("Pipeline completado.")

    except Exception as e:
        logging.error(f"Error en el pipeline: {e}")
        traceback.print_exc()

if __name__ == '__main__':
    run_pipeline()
