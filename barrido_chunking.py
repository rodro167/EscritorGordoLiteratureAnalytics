"""
Barrido de parámetros de chunking del Analizador de Obra Literaria (frente 1).

Prueba varias configuraciones de chunking de forma automática: para cada una
reindexa la base y la mide con el eval set de 15 consultas, apendeando el
resultado a `resultados_eval.md` con el modelo Y la config de chunking como
etiqueta. Al final imprime una tabla resumen (tamaño vs recall) para ver la
tendencia de un vistazo.

Este primer barrido usa el modelo RÁPIDO (MiniLM) para explorar sin esperar
los ~11 min por corrida de bge-m3. El modelo y las configuraciones están
arriba, como variables fáciles de editar para futuros barridos ("megatest").

NO modifica config.yaml ni el modelo fijado en src/embedding.py: el modelo y
el chunking se inyectan en memoria solo durante esta corrida. No toca el .env.

EJECUCIÓN:
    python barrido_chunking.py
"""

import logging
import os
import sys
from datetime import datetime

# La raíz tiene los scripts; el código fuente está en src/.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import embedding                          # noqa: E402  (para reindexar + override)
from ingestion import CargadorTextos      # noqa: E402
from retrieval import BuscadorRAG         # noqa: E402
# Reutilizamos el eval set y la lógica de medición/verificación tal cual, sin
# duplicar nada: mismos números y mismo método que evaluar_retrieval.py.
from evaluar_retrieval import (           # noqa: E402
    EVAL_SET, TOP_K, ARCHIVO_RESULTADOS,
    _evaluar_consulta, _resumir, _verificar,
)


# ==========================================================================
# CONFIGURACIÓN DEL BARRIDO — editar acá
# ==========================================================================
# Modelo de embeddings para este barrido. MiniLM = rápido (segundos por
# reindexado). Para el "megatest" futuro, cambiar a "BAAI/bge-m3" (lento).
MODELO = "paraphrase-multilingual-MiniLM-L12-v2"

# Configuraciones de chunking a probar, como (tamano_chunk, overlap).
# Este barrido: 4 tamaños con overlap fijo. Editable para más valores.
TAMANOS_CHUNK = [400, 600, 800, 1200]
OVERLAP = 100
CONFIGS = [(tamano, OVERLAP) for tamano in TAMANOS_CHUNK]
# ==========================================================================


logging.basicConfig(
    level=logging.WARNING,   # silenciamos el INFO ruidoso del reindexado
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def reindexar(tamano_chunk: int, overlap: int) -> None:
    """Reindexa la base con ESTA config de chunking, reutilizando crear_vectordb.

    crear_vectordb() toma los documentos de embedding.cargar_documentos() sin
    parámetros de chunking. Para inyectar el chunking sin duplicar su lógica de
    indexado, sobreescribimos temporalmente esa función por una que chunkea con
    (tamano_chunk, overlap) —aprovechando que CargadorTextos ya acepta esos
    argumentos (precedencia args > config.yaml)—. Se restaura al terminar.
    """
    original = embedding.cargar_documentos
    embedding.cargar_documentos = (
        lambda: CargadorTextos(
            tamano_chunk=tamano_chunk, overlap=overlap
        ).cargar_todos()
    )
    try:
        embedding.crear_vectordb(recrear=True)
    finally:
        embedding.cargar_documentos = original


def _formatear_corrida(modelo: str, tamano_chunk: int, overlap: int,
                       filas: list, resumen: dict, problemas: list,
                       momento: str) -> str:
    """Bloque markdown de UNA config del barrido, en el estilo de resultados_eval.md.

    Igual que el de evaluar_retrieval.py pero con una línea explícita de
    chunking, para que cada bloque sea inequívoco sobre con qué se midió.
    """
    L = []
    L.append(f"## Corrida (barrido chunking) {momento}")
    L.append("")
    L.append(f"- **Modelo de embeddings:** `{modelo}`")
    L.append(f"- **Chunking:** tamano_chunk={tamano_chunk}, overlap={overlap}")
    L.append(f"- **top_k:** {TOP_K}")
    L.append(f"- **Consultas:** {len(filas)}")
    L.append("")
    L.append("### Desglose por consulta")
    L.append("")
    L.append("| # | Consulta | Enc./Esp. | Faltaron |")
    L.append("|---|---|---|---|")
    for i, f in enumerate(filas, start=1):
        faltaron = ", ".join(f["faltantes"]) if f["faltantes"] else "—"
        L.append(
            f"| {i} | {f['consulta']} | {f['n_ok']}/{f['n_total']} | {faltaron} |"
        )
    L.append("")
    L.append("### Resumen (calculado desde el desglose de arriba)")
    L.append("")
    suma_filas = " + ".join(str(f["n_ok"]) for f in filas)
    L.append(f"- **Total encontrados:** {suma_filas} = "
             f"{resumen['total_ok']} / {resumen['total_esp']}")
    L.append(f"- **Recall micro** (Σ encontrados / Σ esperados): "
             f"{resumen['total_ok']}/{resumen['total_esp']} = {resumen['micro']:.1%}")
    L.append(f"- **Recall macro** (promedio de los {len(filas)} porcentajes): "
             f"{resumen['macro']:.1%}")
    if problemas:
        L.append("- **⚠️ VERIFICACIÓN FALLÓ (bug de cálculo):**")
        for p in problemas:
            L.append(f"    - {p}")
    else:
        L.append(f"- **Verificación:** OK — la suma del desglose "
                 f"({resumen['total_ok']}) coincide con el micro reportado.")
    L.append("")
    L.append("---")
    L.append("")
    return "\n".join(L)


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    # Forzamos el modelo de este barrido en memoria (afecta tanto al reindexado
    # como al BuscadorRAG, que leen embedding.MODELO_EMBEDDING al vuelo). No se
    # toca src/embedding.py en disco.
    embedding.MODELO_EMBEDDING = MODELO

    total = len(CONFIGS)
    print("=" * 70)
    print("BARRIDO DE CHUNKING")
    print(f"Modelo: {MODELO}  ·  top_k={TOP_K}  ·  {total} configuraciones")
    print("=" * 70)

    resumen_tabla = []   # [(tamano, overlap, macro, micro, total_ok, total_esp)]

    for idx, (tamano_chunk, overlap) in enumerate(CONFIGS, start=1):
        print(f"\n[config {idx} de {total}] "
              f"tamano_chunk={tamano_chunk}, overlap={overlap}")

        print("  · reindexando la base...")
        reindexar(tamano_chunk, overlap)

        print("  · evaluando el eval set...")
        buscador = BuscadorRAG()
        filas = [
            _evaluar_consulta(buscador, consulta, esperados)
            for consulta, esperados in EVAL_SET
        ]
        resumen = _resumir(filas)
        problemas = _verificar(filas, resumen)

        momento = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        bloque = _formatear_corrida(
            MODELO, tamano_chunk, overlap, filas, resumen, problemas, momento
        )
        with open(ARCHIVO_RESULTADOS, "a", encoding="utf-8") as fh:
            fh.write(bloque)

        estado = "OK" if not problemas else "⚠️ VERIFICACIÓN FALLÓ"
        print(f"  · macro={resumen['macro']:.1%}  micro="
              f"{resumen['total_ok']}/{resumen['total_esp']}="
              f"{resumen['micro']:.1%}  [{estado}]")

        resumen_tabla.append((
            tamano_chunk, overlap, resumen["macro"], resumen["micro"],
            resumen["total_ok"], resumen["total_esp"],
        ))

    # ---------------------------------------------------------------- resumen
    print("\n" + "=" * 70)
    print(f"RESUMEN DEL BARRIDO — modelo: {MODELO}")
    print("=" * 70)
    print(f"{'tamano_chunk':>12} | {'overlap':>7} | {'macro':>6} | {'micro':>10}")
    print("-" * 70)
    for tamano_chunk, overlap, macro, micro, ok, esp in resumen_tabla:
        print(f"{tamano_chunk:>12} | {overlap:>7} | {macro:>5.1%} | "
              f"{ok:>2}/{esp} = {micro:>4.1%}")
    print("=" * 70)
    print(f"[detalle por consulta apendeado en {ARCHIVO_RESULTADOS}]")


if __name__ == "__main__":
    main()
