"""
Ingesta de documentos literarios para el RAG del Escritor Gordo (PASO 1).

Lee los archivos .md de `data/textos/`, extrae el frontmatter YAML como
metadata, separa el contenido y lo divide en chunks listos para vectorizar.

Salida: lista de objetos `Document` de LangChain, cada uno con su metadata
(titulo, categoria, fecha, tema, chunk_numero, fuente).
"""

import logging
import os
import re
from typing import List

import yaml

# Imports de LangChain compatibles con versiones nuevas y antiguas.
try:  # langchain >= 0.1 (paquetes separados)
    from langchain_core.documents import Document
except ImportError:  # langchain antiguo
    from langchain.schema import Document

try:  # paquete moderno
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:  # fallback a langchain clásico
    from langchain.text_splitter import RecursiveCharacterTextSplitter


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# Defaults usados cuando el YAML está ausente o malformado.
METADATA_DEFAULT = {
    "titulo": "Sin título",
    "categoria": "Desconocida",
    "fecha": "",
    "tema": [],
}

# Separa el frontmatter YAML del contenido: ---\n ... \n---
_FRONTMATTER_RE = re.compile(r"^\s*---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


# --- Configuración de chunking (externalizada a config.yaml) --------------
# Valores de respaldo si config.yaml falta, no se puede leer o le falta la
# sección `chunking`. Son los mismos que estaban hardcodeados históricamente,
# así el comportamiento por defecto no cambia si el config no está.
CHUNK_TAMANO_DEFAULT = 800
CHUNK_OVERLAP_DEFAULT = 100

# config.yaml vive en la raíz del proyecto; este módulo está en src/.
_RUTA_CONFIG = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.yaml"
)


def cargar_config_chunking(ruta_config: str = _RUTA_CONFIG) -> dict:
    """Lee los parámetros de chunking desde config.yaml.

    Devuelve siempre un dict {'tamano_chunk': int, 'overlap': int}. Si el
    archivo no existe, no se puede leer/parsear, o le falta la sección
    `chunking` (o alguno de sus valores es inválido), cae a los defaults
    (CHUNK_TAMANO_DEFAULT / CHUNK_OVERLAP_DEFAULT) con un warning claro, en
    vez de romper la ingesta.
    """
    fallback = {
        "tamano_chunk": CHUNK_TAMANO_DEFAULT,
        "overlap": CHUNK_OVERLAP_DEFAULT,
    }

    if not os.path.exists(ruta_config):
        logger.warning(
            "config.yaml no encontrado en %s; uso defaults de chunking (%d/%d)",
            ruta_config, fallback["tamano_chunk"], fallback["overlap"])
        return fallback

    try:
        with open(ruta_config, "r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh) or {}
    except (OSError, yaml.YAMLError) as exc:
        logger.warning(
            "No se pudo leer/parsear config.yaml (%s); uso defaults (%d/%d)",
            exc, fallback["tamano_chunk"], fallback["overlap"])
        return fallback

    seccion = cfg.get("chunking") if isinstance(cfg, dict) else None
    if not isinstance(seccion, dict):
        logger.warning(
            "config.yaml sin sección 'chunking' válida; uso defaults (%d/%d)",
            fallback["tamano_chunk"], fallback["overlap"])
        return fallback

    resultado = dict(fallback)
    for clave in ("tamano_chunk", "overlap"):
        valor = seccion.get(clave)
        # bool es subclase de int en Python; lo excluimos explícitamente.
        if isinstance(valor, int) and not isinstance(valor, bool) and valor >= 0:
            resultado[clave] = valor
        else:
            logger.warning(
                "config.yaml: 'chunking.%s' ausente o inválido (%r); uso default %d",
                clave, valor, fallback[clave])
    return resultado


class CargadorTextos:
    """Carga y prepara los textos .md para el pipeline RAG."""

    def __init__(self, ruta_datos: str = "data/textos",
                 tamano_chunk: int = None, overlap: int = None):
        self.ruta_datos = ruta_datos

        # Precedencia: argumentos explícitos > config.yaml > fallback
        # hardcodeado. Un futuro pipeline de barrido puede pasar los valores
        # directo al constructor sin tocar el YAML; si no se pasan, mandan los
        # del config (y si el config falla, cargar_config_chunking ya cayó a
        # los defaults 800/100).
        if tamano_chunk is None or overlap is None:
            cfg = cargar_config_chunking()
            if tamano_chunk is None:
                tamano_chunk = cfg["tamano_chunk"]
            if overlap is None:
                overlap = cfg["overlap"]

        self.tamano_chunk = tamano_chunk
        self.overlap = overlap
        logger.info("Chunking: tamano_chunk=%d, overlap=%d",
                    tamano_chunk, overlap)

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=tamano_chunk,
            chunk_overlap=overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    # ----------------------------------------------------------------- público
    def cargar_todos(self) -> List[Document]:
        """Carga todos los .md de `ruta_datos` y retorna sus chunks."""
        if not os.path.isdir(self.ruta_datos):
            logger.error("No existe el directorio de datos: %s", self.ruta_datos)
            return []

        archivos = sorted(
            f for f in os.listdir(self.ruta_datos) if f.lower().endswith(".md")
        )
        logger.info("Encontrados %d archivos .md en %s",
                    len(archivos), self.ruta_datos)

        documentos: List[Document] = []
        for nombre in archivos:
            ruta = os.path.join(self.ruta_datos, nombre)
            chunks = self._cargar_archivo(ruta)
            documentos.extend(chunks)

        logger.info("Ingesta completa: %d archivos → %d chunks",
                    len(archivos), len(documentos))
        return documentos

    # ----------------------------------------------------------------- privado
    def _cargar_archivo(self, ruta: str) -> List[Document]:
        """Lee UN archivo .md y retorna sus chunks como Documents."""
        nombre = os.path.basename(ruta)
        try:
            with open(ruta, "r", encoding="utf-8") as fh:
                bruto = fh.read()
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning("No se pudo leer %s: %s", nombre, exc)
            return []

        if not bruto.strip():
            logger.warning("Archivo vacío, se omite: %s", nombre)
            return []

        metadata = self._extraer_metadata(bruto)
        metadata["fuente"] = nombre

        contenido = self._extraer_contenido(bruto)
        if not contenido.strip():
            logger.warning("Sin contenido tras el YAML, se omite: %s", nombre)
            return []

        chunks = self._chunkear(contenido, metadata)
        logger.info("  %s → %d chunks", nombre, len(chunks))
        return chunks

    def _extraer_metadata(self, contenido: str) -> dict:
        """Parsea el frontmatter YAML. Usa defaults si falta o falla."""
        metadata = dict(METADATA_DEFAULT)
        match = _FRONTMATTER_RE.match(contenido)
        if not match:
            logger.warning("Sin frontmatter YAML, se usan defaults")
            return metadata

        try:
            datos = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError as exc:
            logger.warning("YAML malformado, se usan defaults: %s", exc)
            return metadata

        if not isinstance(datos, dict):
            logger.warning("Frontmatter no es un mapa YAML, se usan defaults")
            return metadata

        for clave in METADATA_DEFAULT:
            if clave in datos and datos[clave] is not None:
                metadata[clave] = datos[clave]

        # ChromaDB no acepta listas en metadata: serializamos `tema`.
        if isinstance(metadata.get("tema"), list):
            metadata["tema"] = ", ".join(str(t) for t in metadata["tema"])

        return metadata

    def _extraer_contenido(self, contenido: str) -> str:
        """Retorna el cuerpo del documento sin el frontmatter YAML."""
        sin_yaml = _FRONTMATTER_RE.sub("", contenido, count=1)
        return sin_yaml.strip()

    def _chunkear(self, texto: str, metadata: dict) -> List[Document]:
        """Divide el texto en chunks preservando metadata + chunk_numero."""
        fragmentos = self._splitter.split_text(texto)
        documentos = []
        for i, fragmento in enumerate(fragmentos):
            if not fragmento.strip():
                continue
            meta = dict(metadata)
            meta["chunk_numero"] = i
            documentos.append(Document(page_content=fragmento, metadata=meta))
        return documentos


def cargar_documentos(ruta_datos: str = "data/textos") -> List[Document]:
    """Helper: carga todos los documentos desde `ruta_datos`."""
    return CargadorTextos(ruta_datos).cargar_todos()


if __name__ == "__main__":
    import sys

    # La consola de Windows usa cp1252 y no puede imprimir emojis (✅).
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    docs = cargar_documentos()

    print("\n" + "=" * 50)
    print(f"Total chunks: {len(docs)}")

    if docs:
        primero = docs[0]
        print("\nPrimer chunk:")
        print(f"  Título:    {primero.metadata.get('titulo')}")
        print(f"  Categoría: {primero.metadata.get('categoria')}")
        print(f"  Fecha:     {primero.metadata.get('fecha')}")
        print(f"  Tema:      {primero.metadata.get('tema')}")
        print(f"  Chunk #:   {primero.metadata.get('chunk_numero')}")
        print(f"  Fuente:    {primero.metadata.get('fuente')}")
        preview = primero.page_content[:100].replace("\n", " ")
        print(f"  Contenido: {preview}...")
        print("\n✅ Ingesta funcionando correctamente")
    else:
        print("\n❌ No se cargó ningún documento")
