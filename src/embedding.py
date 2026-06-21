"""
Vectorización y persistencia en ChromaDB para el RAG del Escritor Gordo (PASO 2).

Toma los chunks producidos por `ingestion.cargar_documentos()`, los vectoriza
con un modelo de sentence-transformers multilingüe (corre local, sin API key)
y los persiste en una colección de ChromaDB en `data/chroma.db/`.

La vectorización la maneja ChromaDB vía su `SentenceTransformerEmbeddingFunction`:
acá NO calculamos los vectores a mano, solo le pasamos los textos y la metadata.
"""

import logging
import os
import sys

import chromadb
from chromadb.utils import embedding_functions

# Permite correr el módulo tanto como script (python src/embedding.py) como
# importado en un paquete (from src.embedding import ...).
try:
    from .ingestion import cargar_documentos
except ImportError:
    from ingestion import cargar_documentos


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# Configuración del almacén vectorial.
RUTA_CHROMA = "data/chroma.db"
NOMBRE_COLECCION = "escritor_gordo"
MODELO_EMBEDDING = "paraphrase-multilingual-MiniLM-L12-v2"
TAMANO_BATCH = 100


def _embedding_function():
    """Función de embeddings de ChromaDB con el modelo multilingüe local."""
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=MODELO_EMBEDDING
    )


def _cliente():
    """Cliente persistente de ChromaDB apuntando a `data/chroma.db/`."""
    os.makedirs(RUTA_CHROMA, exist_ok=True)
    return chromadb.PersistentClient(path=RUTA_CHROMA)


def crear_vectordb(recrear: bool = False):
    """Indexa todos los chunks de la ingesta en ChromaDB y retorna la colección.

    Si `recrear=True` y la colección ya existe, se borra y se vuelve a crear
    desde cero para re-indexar limpio.
    """
    client = _cliente()
    ef = _embedding_function()

    if recrear:
        existentes = {c.name for c in client.list_collections()}
        if NOMBRE_COLECCION in existentes:
            logger.info("recrear=True: borrando colección '%s' existente",
                        NOMBRE_COLECCION)
            client.delete_collection(NOMBRE_COLECCION)

    collection = client.get_or_create_collection(
        name=NOMBRE_COLECCION,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )

    logger.info("Cargando chunks desde la ingesta...")
    documentos = cargar_documentos()
    if not documentos:
        logger.error("La ingesta no devolvió chunks; nada para indexar.")
        return collection

    total = len(documentos)
    logger.info("Indexando %d chunks en batches de %d (modelo: %s)",
                total, TAMANO_BATCH, MODELO_EMBEDDING)

    for inicio in range(0, total, TAMANO_BATCH):
        lote = documentos[inicio:inicio + TAMANO_BATCH]
        ids = []
        textos = []
        metadatas = []
        for offset, doc in enumerate(lote):
            indice = inicio + offset
            meta = doc.metadata
            # Id único y legible: titulo + chunk + índice global (evita choques
            # si dos documentos comparten título).
            titulo = str(meta.get("titulo", "sin_titulo"))
            chunk_n = meta.get("chunk_numero", 0)
            ids.append(f"{titulo}__chunk{chunk_n}__{indice}")
            textos.append(doc.page_content)
            metadatas.append(meta)

        # ChromaDB vectoriza `textos` internamente con la embedding_function.
        collection.add(ids=ids, documents=textos, metadatas=metadatas)
        logger.info("  indexados %d/%d chunks", min(inicio + len(lote), total), total)

    logger.info("Indexación completa: %d chunks en '%s'",
                collection.count(), NOMBRE_COLECCION)
    return collection


def obtener_vectordb():
    """Abre la colección ya indexada sin re-vectorizar nada.

    Lanza RuntimeError con instrucciones si la colección todavía no existe.
    """
    client = _cliente()
    ef = _embedding_function()
    existentes = {c.name for c in client.list_collections()}
    if NOMBRE_COLECCION not in existentes:
        raise RuntimeError(
            f"La colección '{NOMBRE_COLECCION}' no existe en {RUTA_CHROMA}. "
            "Corré primero crear_vectordb(recrear=True) para indexar los chunks."
        )
    return client.get_collection(name=NOMBRE_COLECCION, embedding_function=ef)


if __name__ == "__main__":
    # La consola de Windows usa cp1252 y no puede imprimir emojis (✅).
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    coleccion = crear_vectordb(recrear=True)

    print("\n" + "=" * 50)
    print(f"Chunks indexados: {coleccion.count()}")

    consulta = "Terror en la ciudad"
    print(f"\nQuery de prueba: \"{consulta}\"")
    print("Top 3 chunks más cercanos:\n")

    resultados = coleccion.query(query_texts=[consulta], n_results=3)
    metadatas = resultados.get("metadatas", [[]])[0]
    documentos = resultados.get("documents", [[]])[0]

    for i, (meta, texto) in enumerate(zip(metadatas, documentos), start=1):
        preview = texto[:100].replace("\n", " ")
        print(f"[{i}]")
        print(f"  Título:    {meta.get('titulo')}")
        print(f"  Categoría: {meta.get('categoria')}")
        print(f"  Fecha:     {meta.get('fecha')}")
        print(f"  Contenido: {preview}...")
        print()

    print("✅ Embedding + ChromaDB funcionando")
