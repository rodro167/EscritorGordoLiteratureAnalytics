"""
Síntesis de respuestas con LLM sobre los chunks recuperados (PASO 4).

Cierra el pipeline RAG: toma los fragmentos que devuelve el retrieval
(BuscadorRAG, PASO 3) y le pide a Claude que arme una respuesta en prosa
basándose ÚNICAMENTE en esos fragmentos, citando de qué texto sale cada
observación. No re-indexa ni vuelve a embeddear nada: solo recupera +
sintetiza.

La API key se lee de un archivo `.env` (variable ANTHROPIC_API_KEY) vía
python-dotenv. NUNCA se hardcodea la key en el código.
"""

import logging
import os
import sys
from typing import List, Optional

import anthropic
from dotenv import load_dotenv

# Permite correr el módulo como script (python src/sintesis.py) o importado.
try:
    from .retrieval import BuscadorRAG
except ImportError:
    from retrieval import BuscadorRAG


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Modelo Claude Sonnet vigente (ver catálogo de modelos de Anthropic).
MODELO_LLM = "claude-sonnet-4-6"

# Instrucciones de rol para el LLM. Acotan al crítico a los fragmentos dados
# y le prohíben apoyarse en conocimiento literario general.
SYSTEM_PROMPT = """\
Sos un crítico literario analizando la obra de un autor concreto: el Escritor \
Gordo (Rodrigo Cortés), de Córdoba, Argentina.

Reglas que DEBÉS respetar al responder:
1. Basate ÚNICA Y EXCLUSIVAMENTE en los fragmentos de texto que te paso como \
contexto. NO uses tu conocimiento general de literatura, ni de otros autores, \
ni de teoría literaria: solo lo que está en los fragmentos.
2. Citá siempre de qué texto sacás cada observación, nombrándolo por su título \
entre comillas (por ejemplo: en «El Pozo de Estrellas» se ve que...).
3. Si los fragmentos no alcanzan para responder la pregunta, decilo con \
honestidad en vez de inventar o rellenar. Es preferible un "los fragmentos \
disponibles no permiten afirmar X" antes que una respuesta especulativa.
4. Respondé en español, en prosa clara y bien armada (no listas de bullets \
salvo que ayude de verdad).\
"""


class SintetizadorRAG:
    """Recupera chunks relevantes y sintetiza una respuesta en prosa con Claude."""

    def __init__(self):
        # 1) API key desde .env (no se hardcodea nunca).
        load_dotenv()
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Falta ANTHROPIC_API_KEY. Creá un archivo .env en la raíz del "
                "proyecto con la línea:\n\n    ANTHROPIC_API_KEY=tu-api-key-aca\n"
            )

        # 2) Cliente Anthropic + buscador sobre la base ya indexada.
        self.cliente = anthropic.Anthropic(api_key=api_key)
        self.buscador = BuscadorRAG()
        logger.info("Sintetizador listo (modelo=%s)", MODELO_LLM)

    # ------------------------------------------------------------- prompt
    @staticmethod
    def _formatear_contexto(chunks: List[dict]) -> str:
        """Arma el bloque de contexto que ve el LLM, un fragmento por sección."""
        partes = []
        for i, c in enumerate(chunks, start=1):
            cabecera = (
                f"[Fragmento {i}] "
                f"Título: {c.get('titulo')} · "
                f"Categoría: {c.get('categoria')} · "
                f"Fecha: {c.get('fecha')}"
            )
            partes.append(f"{cabecera}\n{c.get('contenido', '')}")
        return "\n\n---\n\n".join(partes)

    @staticmethod
    def _textos_citados(chunks: List[dict]) -> List[dict]:
        """Lista de textos de origen (título + fecha), sin duplicados, en orden."""
        vistos = set()
        citados = []
        for c in chunks:
            clave = (c.get("titulo"), c.get("fecha"))
            if clave in vistos:
                continue
            vistos.add(clave)
            citados.append({"titulo": c.get("titulo"), "fecha": c.get("fecha")})
        return citados

    # ------------------------------------------------------------- síntesis
    def responder(self, pregunta: str, categoria: Optional[str] = None,
                  fecha_desde: Optional[str] = None,
                  fecha_hasta: Optional[str] = None,
                  top_k: int = 5) -> dict:
        """Recupera fragmentos relevantes y devuelve respuesta en prosa + citas.

        Devuelve un dict con:
          - "respuesta":  texto en prosa generado por el LLM (str)
          - "citados":    lista de {titulo, fecha} de los textos usados
          - "chunks":     los chunks crudos que se le pasaron al LLM
        """
        chunks = self.buscador.buscar(
            pregunta, categoria=categoria,
            fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, top_k=top_k,
        )

        if not chunks:
            return {
                "respuesta": ("No se encontraron fragmentos relevantes para esa "
                              "consulta con los filtros aplicados, así que no hay "
                              "material sobre el que basar un análisis."),
                "citados": [],
                "chunks": [],
            }

        contexto = self._formatear_contexto(chunks)
        mensaje_usuario = (
            f"Pregunta: {pregunta}\n\n"
            f"Fragmentos de la obra del Escritor Gordo (úsalos como única fuente):"
            f"\n\n{contexto}"
        )

        logger.info("Sintetizando respuesta a partir de %d fragmentos...",
                    len(chunks))
        try:
            respuesta_api = self.cliente.messages.create(
                model=MODELO_LLM,
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": mensaje_usuario}],
            )
        except anthropic.AuthenticationError as e:
            raise RuntimeError(
                "La API key de Anthropic es inválida o fue revocada. Revisá "
                "ANTHROPIC_API_KEY en el archivo .env."
            ) from e
        except anthropic.APIConnectionError as e:
            raise RuntimeError(
                "No se pudo conectar con la API de Anthropic. Revisá tu conexión "
                "a internet e intentá de nuevo."
            ) from e
        except anthropic.RateLimitError as e:
            raise RuntimeError(
                "La API de Anthropic está limitando las solicitudes (rate limit). "
                "Esperá unos segundos y volvé a intentar."
            ) from e
        except anthropic.APIStatusError as e:
            raise RuntimeError(
                f"La API de Anthropic devolvió un error ({e.status_code}): "
                f"{e.message}"
            ) from e

        # La respuesta es una lista de bloques; juntamos solo el texto.
        texto = "".join(
            b.text for b in respuesta_api.content if b.type == "text"
        ).strip()

        return {
            "respuesta": texto,
            "citados": self._textos_citados(chunks),
            "chunks": chunks,
        }


def _imprimir(resultado: dict) -> None:
    """Imprime la respuesta del LLM y los textos citados de forma legible."""
    print("\nRespuesta:\n")
    print(resultado["respuesta"])
    print("\nTextos citados:")
    if not resultado["citados"]:
        print("  (ninguno)")
    for c in resultado["citados"]:
        print(f"  - «{c['titulo']}» ({c['fecha']})")


if __name__ == "__main__":
    # La consola de Windows usa cp1252 y no puede imprimir emojis (✅) ni «».
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    # Bajamos el ruido de logging durante el test para no tapar las respuestas.
    logging.getLogger().setLevel(logging.WARNING)

    sintetizador = SintetizadorRAG()

    print("=" * 70)
    print("1) Sin filtros: ¿Qué temas recurrentes aparecen en estos textos?")
    print("=" * 70)
    _imprimir(
        sintetizador.responder("¿Qué temas recurrentes aparecen en estos textos?")
    )

    print("\n" + "=" * 70)
    print("2) Filtrada por categoría='Cuento': ¿Cómo se aborda la muerte?")
    print("=" * 70)
    _imprimir(
        sintetizador.responder("¿Cómo se aborda la muerte?", categoria="Cuento")
    )

    print("\n✅ Síntesis LLM funcionando")
