"""
Interfaz web (Streamlit) del Analizador de Obra Literaria de Escritor Gordo.

PASO 5 — cierre de la Fase 1. Pone una UI encima del pipeline RAG completo:
pregunta del usuario + filtros -> SintetizadorRAG.responder() -> respuesta en
prosa con sus textos citados.

EJECUCIÓN:
    streamlit run app.py

NO se ejecuta con `python app.py` (Streamlit necesita su propio runner).
La API key la carga solo SintetizadorRAG desde el .env; acá no se toca.
"""

import os
import sys

import streamlit as st

# app.py vive en la raíz; el código fuente está en src/. Lo agregamos al path
# para poder importar el módulo de síntesis (que a su vez importa retrieval).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from sintesis import SintetizadorRAG  # noqa: E402  (import tras ajustar sys.path)


# Rango de años cubierto por la obra (aprox. 2002–2025).
ANIO_MIN = 2002
ANIO_MAX = 2025

# Categorías canónicas. "Fruta de Estación" lleva tilde (valor exacto en la BD).
CATEGORIAS = ["Todas", "Cuento", "Fruta de Estación"]


@st.cache_resource(show_spinner="Cargando el motor RAG (embeddings + ChromaDB)...")
def cargar_sintetizador() -> SintetizadorRAG:
    """Instancia el SintetizadorRAG UNA sola vez por sesión del servidor.

    @st.cache_resource evita recargar el modelo de embeddings y reabrir
    ChromaDB en cada interacción del usuario — es lo que hace usable la app.
    """
    return SintetizadorRAG()


def main() -> None:
    st.set_page_config(page_title="Analizador — Escritor Gordo", page_icon="📚")

    st.title("📚 Analizador de Obra Literaria de Escritor Gordo")
    st.caption("Preguntá sobre tu obra: el sistema busca en tus textos y "
               "sintetiza una respuesta citando las fuentes.")

    # Cargamos el motor (cacheado). Si falla la inicialización (ej. falta la
    # API key o la base ChromaDB), lo mostramos sin romper la app.
    try:
        sintetizador = cargar_sintetizador()
    except Exception as e:  # noqa: BLE001
        st.error(f"No se pudo inicializar el sistema: {e}")
        st.stop()

    # ----------------------------------------------------------- sidebar
    with st.sidebar:
        st.header("Filtros")

        categoria_sel = st.selectbox("Categoría", CATEGORIAS, index=0)

        st.subheader("Período")
        anios = list(range(ANIO_MIN, ANIO_MAX + 1))
        col_d, col_h = st.columns(2)
        with col_d:
            anio_desde = st.selectbox("Desde", anios, index=0)
        with col_h:
            anio_hasta = st.selectbox("Hasta", anios, index=len(anios) - 1)

        if anio_desde > anio_hasta:
            st.warning("El año 'Desde' es posterior al 'Hasta'. Ajustá el rango.")

        top_k = st.slider("Fragmentos a recuperar (top_k)", 3, 10, 5)

    # ----------------------------------------------------------- principal
    pregunta = st.text_area(
        "Tu pregunta",
        placeholder="Ej.: ¿Qué temas recurrentes aparecen en estos textos?",
        height=100,
    )

    if st.button("Analizar", type="primary"):
        if not pregunta.strip():
            st.info("Escribí una pregunta antes de analizar. 🙂")
            return

        # "Todas" => sin filtro de categoría.
        categoria = None if categoria_sel == "Todas" else categoria_sel
        # Año -> rango de fechas YYYY-MM-DD que entiende responder().
        fecha_desde = f"{anio_desde}-01-01"
        fecha_hasta = f"{anio_hasta}-12-31"

        try:
            with st.spinner("Buscando fragmentos y sintetizando la respuesta..."):
                resultado = sintetizador.responder(
                    pregunta.strip(),
                    categoria=categoria,
                    fecha_desde=fecha_desde,
                    fecha_hasta=fecha_hasta,
                    top_k=top_k,
                )
        except Exception as e:  # noqa: BLE001
            st.error(f"Ocurrió un error al generar la respuesta: {e}")
            return

        st.subheader("Respuesta")
        st.markdown(resultado["respuesta"])

        st.subheader("Textos citados")
        citados = resultado.get("citados") or []
        if not citados:
            st.write("_(ninguno)_")
        else:
            for c in citados:
                st.markdown(f"- «{c['titulo']}» ({c['fecha']})")


if __name__ == "__main__":
    main()
