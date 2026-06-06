# Especificación de Requisitos del Software (ERS)
## Proyecto: Motor de Inteligencia Artificial para Similitud de Jugadores

### 1. Descripción General y Objetivo Deportivo
El sistema es una herramienta analítica orientada a la dirección deportiva que permite identificar reemplazos o "clones estadísticos" de futbolistas específicos. Mediante la ingesta masiva de datos y el cálculo de distancias matemáticas, la aplicación devolverá los perfiles más afines a un jugador objetivo (ej. buscar el reemplazo de Toni Martínez combinando mercados de Primera y Segunda División).

### 2. Arquitectura y Pila Tecnológica
El agente deberá construir la solución utilizando el siguiente stack:
*   **Lenguaje:** Python 3.x
*   **Extracción de Datos:** `soccerdata` (API no oficial de FBref)
*   **Manejo de Datos y Matemáticas:** `pandas`, `numpy`, `scikit-learn` (`StandardScaler`, `cosine_similarity`)
*   **Frontend / UI:** `streamlit`
*   **Gráficos interactivos:** `plotly` (para los gráficos de radar)

### 3. Fase 1: Pipeline de Datos (Script ETL)
Se debe crear un script independiente (ej. `data_pipeline.py`) que ejecute lo siguiente:
1.  **Ingesta:** Extraer las tablas `standard` y `shooting` de la temporada 2025-2026 para "ESP-La Liga" y "ESP-La Liga 2".
2.  **Limpieza:** 
    *   Unir (merge) las tablas utilizando el nombre del jugador como índice común.
    *   Filtrar para mantener estrictamente a jugadores con posición `FW` o `MF,FW`.
    *   Eliminar registros con menos de 600 minutos disputados para evitar anomalías estadísticas.
3.  **Métricas Clave:** Seleccionar o calcular en base a 90 minutos: Goles Esperados (xG), % Duelos aéreos ganados, Toques en área rival, y % de Tiros a Puerta.
4.  **Persistencia:** Guardar el dataframe resultante en un archivo local `delanteros_procesados.csv`.

### 4. Fase 2: Motor Algorítmico y Backend
1.  **Estandarización:** Al cargar el CSV, el sistema debe aplicar un Z-score (`StandardScaler`) a las métricas clave para que todas pesen lo mismo en el cálculo, independientemente de su escala de magnitud.
2.  **Cálculo de Distancia:** Implementar la **Similitud del Coseno** comparando el vector estandarizado del jugador seleccionado por el usuario frente a la matriz de todo el resto de jugadores disponibles.
3.  **Conversión:** Transformar el valor bruto del coseno a un índice porcentual de similitud (0% a 100%).

### 5. Fase 3: Interfaz de Usuario (Streamlit)
El script principal (`app.py`) debe renderizar una aplicación web con la siguiente estructura:
1.  **Barra lateral (Sidebar):**
    *   Título de la herramienta.
    *   Selectores desplegables para elegir la "Liga Objetivo" y el "Jugador a reemplazar".
2.  **Panel Principal:**
    *   **Ranking:** Mostrar un *DataFrame* ordenado con los 5 jugadores con mayor porcentaje de similitud (excluyendo al propio jugador evaluado). Las columnas deben mostrar: Nombre, Equipo, Edad, Liga y % de Similitud.
    *   **Visualización:** Generar un *Spider Chart* (Gráfico de Radar) usando Plotly que superponga las estadísticas del jugador a reemplazar frente a las del candidato número 1 sugerido por el modelo.

### 6. Criterios de Ejecución para el Agente
*   El código debe estar documentado en español.
*   El manejo de excepciones debe estar contemplado (ej. control de errores si no hay suficientes datos para dibujar el radar).