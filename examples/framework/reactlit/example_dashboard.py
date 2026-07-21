"""
Complete Real-World Example: Analytics Dashboard
=================================================

Dashboard analytics completo que demuestra:
- Fragmentos reactivos en cascada
- Gestión de estado compartido
- Formularios reactivos
- Prevención de ciclos
- Buenas prácticas

Ejecutar:
    streamlit run example_dashboard.py
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from streamlit_plugins.framework.reactlit import (
    reactlit_fragment,
    debug_dependency_graph,
    reset_reactive_state,
)


# =============================================================================
# 🎨 CONFIGURACIÓN INICIAL
# =============================================================================

def configure_page():
    """Configura la página Streamlit"""
    st.set_page_config(
        page_title="Analytics Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # CSS customizado
    st.markdown("""
    <style>
    [data-testid="stMetricValue"] {
        font-size: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)


def initialize_state():
    """Inicializa el estado compartido de la aplicación"""

    if 'dashboard_initialized' not in st.session_state:
        st.session_state.dashboard_initialized = True

        # Filtros
        st.session_state.date_range = (
            datetime.now() - timedelta(days=30),
            datetime.now()
        )
        st.session_state.selected_metric = "Revenue"
        st.session_state.selected_regions = ["North", "South"]

        # Datos
        st.session_state.raw_data = generate_sample_data()
        st.session_state.filtered_data = None
        st.session_state.aggregated_data = None

        # UI State
        st.session_state.show_debug = False


# =============================================================================
# 📊 DATOS SIMULADOS
# =============================================================================

def generate_sample_data():
    """Genera datos de ejemplo para el dashboard"""
    np.random.seed(42)

    dates = pd.date_range(
        start=datetime.now() - timedelta(days=30),
        end=datetime.now(),
        freq='D'
    )

    regions = ["North", "South", "East", "West"]
    data = []

    for date in dates:
        for region in regions:
            data.append({
                'date': date,
                'region': region,
                'revenue': np.random.randint(1000, 5000),
                'users': np.random.randint(100, 500),
                'engagement': np.random.uniform(0.3, 0.9),
                'churn_rate': np.random.uniform(0.01, 0.1),
            })

    return pd.DataFrame(data)


# =============================================================================
# 🎛️ FRAGMENTO 1: CONTROLES (ROOT)
# =============================================================================

@reactlit_fragment(watch_params=True)
def fragment_filters():
    """
    Panel de controles (Root Fragment)
    - No depende de nada
    - Sus cambios disparan el resto
    """

    st.subheader("🎛️ Filtros & Controles")

    with st.container(border=True):
        col1, col2, col3 = st.columns(3)

        # Date Range
        with col1:
            date_range = st.date_input(
                "Rango de fechas:",
                value=(
                    st.session_state.date_range[0],
                    st.session_state.date_range[1]
                ),
                key="date_range_picker"
            )

            if len(date_range) == 2:
                st.session_state.date_range = (date_range[0], date_range[1])

        # Metric Selection
        with col2:
            metric = st.selectbox(
                "Métrica:",
                ["Revenue", "Users", "Engagement", "Churn"],
                index=["Revenue", "Users", "Engagement", "Churn"].index(
                    st.session_state.selected_metric
                ),
                key="metric_select"
            )
            st.session_state.selected_metric = metric

        # Region Selection
        with col3:
            regions = st.multiselect(
                "Regiones:",
                ["North", "South", "East", "West"],
                default=st.session_state.selected_regions,
                key="region_select"
            )
            st.session_state.selected_regions = regions

        # Debug toggle
        st.session_state.show_debug = st.checkbox(
            "🔍 Mostrar Debug",
            value=st.session_state.show_debug
        )


# =============================================================================
# 🔄 FRAGMENTO 2: FILTRADO DE DATOS (DEPENDS ON CONTROLES)
# =============================================================================

@reactlit_fragment(
    dependencies=['date_range', 'selected_regions'],
    watch_params=True
)
def fragment_filter_data():
    """
    Filtra datos según controles
    - Se actualiza cuando date_range o regions cambian
    - Guarda datos filtrados en session_state
    """

    # Obtiene parámetros
    date_from, date_to = st.session_state.date_range
    regions = st.session_state.selected_regions

    # Filtra datos
    raw_data = st.session_state.raw_data

    filtered = raw_data[
        (raw_data['date'].dt.date >= date_from) &
        (raw_data['date'].dt.date <= date_to) &
        (raw_data['region'].isin(regions))
    ]

    st.session_state.filtered_data = filtered

    # Log interno
    st.session_state._dashboard_log = (
        st.session_state.get('_dashboard_log', []) +
        [f"Filtered: {len(filtered)} rows"]
    )


# =============================================================================
# 📈 FRAGMENTO 3: AGREGACIÓN (DEPENDS ON FILTERED DATA)
# =============================================================================

@reactlit_fragment(
    dependencies=['filtered_data', 'selected_metric'],
    watch_params=True
)
def fragment_aggregate():
    """
    Agrega datos según métrica seleccionada
    - Se actualiza cuando métrica o datos filtrados cambian
    """

    filtered_data = st.session_state.get('filtered_data')
    metric = st.session_state.selected_metric

    if filtered_data is None or len(filtered_data) == 0:
        st.session_state.aggregated_data = None
        return

    # Mapea métrica a columna
    metric_map = {
        'Revenue': 'revenue',
        'Users': 'users',
        'Engagement': 'engagement',
        'Churn': 'churn_rate',
    }

    column = metric_map.get(metric, 'revenue')

    # Agrega por fecha
    aggregated = filtered_data.groupby('date')[column].sum().reset_index()
    aggregated = aggregated.rename(columns={column: metric})
    aggregated = aggregated.sort_values('date')

    st.session_state.aggregated_data = aggregated

    # Log
    st.session_state._dashboard_log = (
        st.session_state.get('_dashboard_log', []) +
        [f"Aggregated: {metric} - {len(aggregated)} datapoints"]
    )


# =============================================================================
# 📊 FRAGMENTO 4: METRICS DISPLAY (DEPENDS ON AGGREGATED DATA)
# =============================================================================

@reactlit_fragment(
    dependencies=['aggregated_data', 'selected_metric'],
    watch_params=True
)
def fragment_metrics():
    """
    Muestra métricas resumidas
    - Se actualiza cuando datos agregados cambian
    """

    st.subheader("📊 Métricas Clave")

    data = st.session_state.get('aggregated_data')

    if data is None or len(data) == 0:
        st.warning("No hay datos para mostrar")
        return

    metric = st.session_state.selected_metric

    col1, col2, col3, col4 = st.columns(4)

    # Calcula valores
    current = data.iloc[-1][metric]
    previous = data.iloc[-2][metric] if len(data) > 1 else current
    delta = current - previous
    delta_pct = (delta / previous * 100) if previous != 0 else 0

    total = data[metric].sum()
    avg = data[metric].mean()

    with col1:
        st.metric(
            "Valor Actual",
            f"{current:,.0f}",
            delta=f"{delta_pct:.1f}%"
        )

    with col2:
        st.metric("Total", f"{total:,.0f}")

    with col3:
        st.metric("Promedio", f"{avg:,.0f}")

    with col4:
        st.metric(
            "Min/Max",
            f"{data[metric].min():.0f} / {data[metric].max():.0f}"
        )


# =============================================================================
# 📉 FRAGMENTO 5: CHARTS (DEPENDS ON AGGREGATED DATA)
# =============================================================================

@reactlit_fragment(
    dependencies=['aggregated_data', 'selected_metric'],
    watch_params=True
)
def fragment_charts():
    """
    Renderiza gráficos
    - Se actualiza cuando datos agregados cambian
    """

    st.subheader("📈 Gráficos")

    data = st.session_state.get('aggregated_data')
    metric = st.session_state.selected_metric

    if data is None or len(data) == 0:
        st.warning("No hay datos para visualizar")
        return

    col1, col2 = st.columns(2)

    with col1:
        # Line chart
        st.line_chart(
            data.set_index('date')[metric],
            width="content"
        )

    with col2:
        # Area chart
        st.area_chart(
            data.set_index('date')[metric],
            width="content"
        )


# =============================================================================
# 📋 FRAGMENTO 6: DETAILED TABLE (DEPENDS ON FILTERED DATA)
# =============================================================================

@reactlit_fragment(
    dependencies=['filtered_data'],
    watch_params=True
)
def fragment_detailed_table():
    """
    Tabla detallada de datos
    - Se actualiza cuando datos filtrados cambian
    """

    st.subheader("📋 Datos Detallados")

    data = st.session_state.get('filtered_data')

    if data is None or len(data) == 0:
        st.info("No hay datos para mostrar")
        return

    # Prepara para mostrar
    display_data = data.copy()
    display_data['date'] = display_data['date'].dt.strftime('%Y-%m-%d')
    display_data = display_data.sort_values('date', ascending=False)

    # Muestra tabla con opciones
    st.dataframe(
        display_data,
        width="content",
        hide_index=True,
        column_config={
            'revenue': st.column_config.NumberColumn(
                'Revenue',
                format='$%d'
            ),
            'users': st.column_config.NumberColumn(
                'Users',
                format='%d'
            ),
            'engagement': st.column_config.ProgressColumn(
                'Engagement',
                min_value=0,
                max_value=1,
            ),
            'churn_rate': st.column_config.ProgressColumn(
                'Churn Rate',
                min_value=0,
                max_value=1,
            ),
        }
    )


# =============================================================================
# 🔧 SIDEBAR: HERRAMIENTAS DE DEBUG
# =============================================================================

def sidebar_debug():
    """Sidebar con herramientas de debug"""

    with st.sidebar:
        st.divider()

        with st.expander("🔧 Herramientas de Debug", expanded=False):

            if st.button("📊 Mostrar Grafo de Dependencias"):
                debug_dependency_graph()

            if st.button("🔄 Reset Estado"):
                reset_reactive_state()
                st.rerun()

            st.write("**Logs Internos:**")
            logs = st.session_state.get('_dashboard_log', [])
            for log in logs[-10:]:
                st.text(log)


# =============================================================================
# 🎨 LAYOUT PRINCIPAL
# =============================================================================

def main():
    """Función principal de la aplicación"""

    configure_page()
    initialize_state()

    st.title("📊 Analytics Dashboard - Reactive Fragments")

    with st.sidebar:
        st.markdown("""
        Dashboard que demuestra el framework reactivo de Streamlit.
        
        **Cómo funciona:**
        1. Cambia los filtros → Se actualiza automáticamente
        2. Cada cambio dispara una cascada de fragmentos
        3. Los gráficos se actualizan sin refrescar la página completa
        
        **Fragmentos:**
        - Controles → Filtrado → Agregación → Métricas & Gráficos
        """)

    # FRAGMENTO 1: Controles
    fragment_filters()

    st.divider()

    # FRAGMENTO 2: Filtrado (no visible, solo actualiza state)
    fragment_filter_data()

    # FRAGMENTO 3: Agregación (no visible, solo actualiza state)
    fragment_aggregate()

    # FRAGMENTO 4: Métricas
    fragment_metrics()

    st.divider()

    # FRAGMENTO 5: Gráficos
    fragment_charts()

    st.divider()

    # FRAGMENTO 6: Tabla
    fragment_detailed_table()

    # Sidebar
    sidebar_debug()

    # Footer
    st.divider()
    st.caption("🚀 Powered by Reactlit - Reactive Fragment Framework")


# =============================================================================
# 🚀 ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    main()
