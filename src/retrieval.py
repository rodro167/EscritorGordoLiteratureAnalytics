"""
Búsqueda semántica sobre la base vectorial del Escritor Gordo (PASO 3).

Consulta la colección "escritor_gordo" ya persistida en `data/chroma.db/`
(construida por embedding.py). Acá NO se re-indexa nada: solo se abre la
colección existente y se hacen queries con filtros opcionales de metadata.

El módulo devuelve chunks crudos (sin sintetizar). La generación de
respuestas con LLM corresponde al paso siguiente, no a este.
"""

import logging
import sys
from typing import List, Optional

# Permite correr el módulo como script (python src/retrieval.py) o importado.
try:
    from .embedding import obtener_vectordb
except ImportError:
    from embedding import obtener_vectordb


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


class BuscadorRAG:
    """Busca chunks relevantes en la colección ya indexada, con filtros."""

    def __init__(self):
        # obtener_vectordb() lanza RuntimeError claro si la colección no existe.
        self.coleccion = obtener_vectordb()
        logger.info("Colección abierta: %d chunks disponibles",
                    self.coleccion.count())

    # ------------------------------------------------------------- filtros
    @staticmethod
    def _construir_where(categoria: Optional[str]) -> Optional[dict]:
        """Arma el `where` de ChromaDB para los filtros que soporta nativo.

        Solo la igualdad de `categoria` va al motor: ChromaDB 1.x rechaza
        $gte/$lte sobre strings (solo int/float), así que el rango de fechas
        se resuelve en Python (ver `_en_rango_fecha`). La `fecha` está guardada
        como string YYYY-MM-DD, cuyo orden lexicográfico coincide con el
        cronológico, por lo que la comparación de strings es válida como rango.
        """
        if categoria:
            return {"categoria": {"$eq": categoria}}
        return None

    @staticmethod
    def _en_rango_fecha(fecha: Optional[str], desde: Optional[str],
                        hasta: Optional[str]) -> bool:
        """True si `fecha` (YYYY-MM-DD) cae dentro del rango [desde, hasta]."""
        if not desde and not hasta:
            return True
        if not fecha:  # sin fecha no puede satisfacer un filtro de rango
            return False
        if desde and fecha < desde:
            return False
        if hasta and fecha > hasta:
            return False
        return True

    # ------------------------------------------------------------- búsqueda
    def buscar(self, query: str, categoria: Optional[str] = None,
               fecha_desde: Optional[str] = None,
               fecha_hasta: Optional[str] = None,
               top_k: int = 5) -> List[dict]:
        """Query semántica + filtros de metadata. Devuelve chunks crudos."""
        where = self._construir_where(categoria)
        filtra_fecha = bool(fecha_desde or fecha_hasta)
        logger.info("Buscar: %r | where=%s | fecha=[%s..%s] | top_k=%d",
                    query, where, fecha_desde, fecha_hasta, top_k)

        # Si hay filtro de fecha (post-query), sobre-pedimos candidatos para no
        # quedarnos cortos tras descartar los que caen fuera del rango.
        n_results = self.coleccion.count() if filtra_fecha else top_k

        resultados = self.coleccion.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
        )

        # ChromaDB devuelve listas-de-listas (una sublista por query_text) y ya
        # ordenadas por distancia ascendente.
        documentos = resultados.get("documents") or [[]]
        metadatas = resultados.get("metadatas") or [[]]
        distancias = resultados.get("distances") or [[]]

        docs = documentos[0] if documentos else []
        metas = metadatas[0] if metadatas else []
        dists = distancias[0] if distancias else []

        salida: List[dict] = []
        for texto, meta, dist in zip(docs, metas, dists):
            if not self._en_rango_fecha(meta.get("fecha"), fecha_desde, fecha_hasta):
                continue
            salida.append({
                "titulo": meta.get("titulo"),
                "categoria": meta.get("categoria"),
                "fecha": meta.get("fecha"),
                "contenido": texto,        # chunk completo, sin truncar
                "score": dist,             # distancia coseno (menor = más cercano)
            })
            if len(salida) >= top_k:
                break
        return salida


def imprimir_resultados(resultados: List[dict], preview_chars: int = 150) -> None:
    """Imprime los resultados de forma legible (preview ~150 chars)."""
    if not resultados:
        print("  (sin resultados)")
        return
    for i, r in enumerate(resultados, start=1):
        preview = (r.get("contenido") or "")[:preview_chars].replace("\n", " ")
        score = r.get("score")
        score_txt = f"{score:.4f}" if isinstance(score, (int, float)) else "n/a"
        print(f"[{i}] {r.get('titulo')}  ·  {r.get('categoria')}  ·  {r.get('fecha')}")
        print(f"    score(dist): {score_txt}")
        print(f"    {preview}...")
        print()


if __name__ == "__main__":
    # La consola de Windows usa cp1252 y no puede imprimir emojis (✅).
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    # Bajamos el ruido de logging durante el test para no tapar los resultados.
    logging.getLogger().setLevel(logging.WARNING)

    buscador = BuscadorRAG()

    print("\n" + "=" * 60)
    print("1) Búsqueda simple (sin filtros): 'la soledad y el paso del tiempo'")
    print("=" * 60)
    imprimir_resultados(
        buscador.buscar("la soledad y el paso del tiempo", top_k=3)
    )

    print("=" * 60)
    print("2) Filtrada por categoría='Cuento': 'la infancia'")
    print("=" * 60)
    imprimir_resultados(
        buscador.buscar("la infancia", categoria="Cuento", top_k=3)
    )

    print("=" * 60)
    print("3) Filtrada por período [2012-01-01 .. 2015-12-31]: 'la política y el poder'")
    print("=" * 60)
    imprimir_resultados(
        buscador.buscar("la política y el poder",
                        fecha_desde="2012-01-01",
                        fecha_hasta="2015-12-31",
                        top_k=3)
    )

    print("✅ Retrieval funcionando")
