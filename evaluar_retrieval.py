"""
Evaluación de retrieval del Analizador de Obra Literaria de Escritor Gordo.

Mide qué tan bien el retrieval ACTUAL recupera los textos que un eval set
(definido por el autor) considera relevantes para cada consulta. Sirve para
comparar objetivamente distintos modelos de embeddings o estrategias de
chunking (ver ROADMAP.md, frente 1).

Cada corrida, además de imprimir en pantalla, se APENDEA a `resultados_eval.md`
(registro acumulativo, no se sobrescribe), etiquetada con el modelo de
embeddings vigente —leído automáticamente de la constante MODELO_EMBEDDING de
src/embedding.py, para que no haya forma de confundir con qué modelo se midió.

NO re-indexa nada: solo consulta la colección ya persistida vía BuscadorRAG.

EJECUCIÓN:
    python evaluar_retrieval.py
"""

import logging
import os
import re
import sys
import unicodedata
from datetime import datetime
from typing import List

# evaluar_retrieval.py vive en la raíz; el código fuente está en src/.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from retrieval import BuscadorRAG       # noqa: E402  (import tras ajustar path)
# El nombre del modelo se toma de la MISMA constante que usa el indexado, así
# el rótulo del reporte no puede quedar desincronizado de la base real.
from embedding import MODELO_EMBEDDING  # noqa: E402


# Cuántos chunks pedir por consulta. Amplio a propósito: buscamos cobertura
# (¿aparece el texto esperado en algún lado?), no precisión en el top-3.
TOP_K = 20

# Registro acumulativo de corridas (junto a este script, en la raíz).
ARCHIVO_RESULTADOS = os.path.join(os.path.dirname(__file__), "resultados_eval.md")


# --------------------------------------------------------------------------
# Eval set: cada caso es (consulta, [títulos esperados]). Definido por el
# autor a partir de su conocimiento del corpus. Los títulos se comparan de
# forma tolerante (ver _normalizar), así que no hace falta que coincidan
# carácter por carácter con la forma almacenada.
# --------------------------------------------------------------------------
EVAL_SET = [
    ("nostalgia de la infancia",
     ["Mañana sin hechizo", "Pasado", "Historia de una niña"]),
    ("resistencia a las dictaduras",
     ["La flor de Jinotepe", "Tu voz seguirá viviendo", "Claveles de Abril",
      "Las trece rosas"]),
    ("posibles alegorías",
     ["Las voces", "Fragmentos de un diario de viaje", "Polvo eres"]),
    ("anécdotas juveniles",
     ["Córdoba, 1993", "Una breve carrera", "Demagogo serial"]),
    ("soledad y desencuentro",
     ["Última noticia", "Caminos separados", "Pasado", "La noche de Lucía",
      "Historia de una niña"]),
    ("individuos notables",
     ["Un olvido feliz de Galeano", "El León del desierto",
      "Bestie, el de los laberintos invisibles", "La flor de Jinotepe",
      "El díptico revelador de Bart"]),
    ("humor e ironía",
     ["Las marchas escolares y la crisis del sentir patriótico",
      "Una breve carrera", "Córdoba, 1993",
      "Manual Instructivo Misceláneo de Escritor Gordo (selección)",
      "La balanza de la injusticia (contrapunto de sonetos)",
      "Un paseo por el cielo"]),
    ("absurdo y exageración",
     ["Tomás y nosotros", "Así funciona este mundo",
      "La herencia del señor Skoglund", "La casa 314", "Un paseo por el cielo",
      "Foto con Cartucho", "Teoría de Rasmussen", "Aviones en Borneo"]),
    ("base histórica o mitológica",
     ["Héroes de Haymarket", "De diosas, planetas, oscuridades y más...",
      "Las trece rosas", "Un olvido feliz de Galeano",
      "Tu voz seguirá viviendo"]),
    ("angustia y desesperación",
     ["El rostro revelado", "Big Bang", "Fragmentos de un diario de viaje",
      "Las voces", "El recorrido"]),
    ("ubicación geográfica explícita o sugerida",
     ["Córdoba, 1993", "Una breve carrera", "Un paseo por el cielo",
      "Claveles de Abril", "Héroes de Haymarket", "Las trece rosas"]),
    ("juegos de palabras o doble sentido",
     ["Así funciona este mundo"]),
    ("referencias al deporte, real o ficticio",
     ["Un olvido feliz de Galeano", "Bestie, el de los laberintos invisibles",
      "Foto con Cartucho", "Una breve carrera"]),
    ("menciones de países o nacionalidades",
     ["Pasado", "Las marchas escolares y la crisis del sentir patriótico",
      "Claveles de Abril", "Bestie, el de los laberintos invisibles",
      "Tu voz seguirá viviendo", "La herencia del señor Skoglund"]),
    ("pérdida de ser querido o muerte en general",
     ["El rostro revelado", "Foto con Cartucho", "Un olvido feliz de Galeano",
      "Pasado", "La herencia del señor Skoglund", "Última noticia"]),
]


def _normalizar(titulo: str) -> str:
    """Normaliza un título para comparación tolerante.

    Minúsculas, sin tildes, sin puntuación (comas, puntos, paréntesis,
    puntos suspensivos, etc.) y espacios colapsados. Absorbe diferencias
    cosméticas de escritura entre el eval set y lo almacenado en la base.
    """
    if not titulo:
        return ""
    # Descompone y descarta las marcas diacríticas (tildes, diéresis).
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFKD", titulo)
        if not unicodedata.combining(c)
    )
    sin_tildes = sin_tildes.lower()
    # Todo lo que no sea alfanumérico o espacio -> espacio.
    limpio = re.sub(r"[^\w\s]", " ", sin_tildes, flags=re.UNICODE)
    # Colapsa espacios.
    return re.sub(r"\s+", " ", limpio).strip()


def _coincide(esperado: str, recuperado: str) -> bool:
    """True si dos títulos normalizados se consideran el mismo texto.

    Acierto si uno contiene al otro (en cualquier dirección): absorbe
    truncamientos o sufijos de la forma almacenada.
    """
    e = _normalizar(esperado)
    r = _normalizar(recuperado)
    if not e or not r:
        return False
    return e in r or r in e


def _titulos_unicos_en_orden(resultados: List[dict]) -> List[str]:
    """Títulos de los chunks recuperados, únicos y en orden de aparición."""
    vistos = set()
    orden: List[str] = []
    for r in resultados:
        t = r.get("titulo")
        if not t:
            continue
        clave = _normalizar(t)
        if clave in vistos:
            continue
        vistos.add(clave)
        orden.append(t)
    return orden


def _evaluar_consulta(buscador: BuscadorRAG, consulta: str,
                      esperados: List[str]) -> dict:
    """Evalúa UNA consulta y devuelve su fila de resultados.

    La fila es la única fuente de verdad: de acá salen tanto el desglose
    impreso/escrito como los agregados. `aciertos` son (titulo, posicion).
    """
    resultados = buscador.buscar(consulta, top_k=TOP_K)
    recuperados = _titulos_unicos_en_orden(resultados)

    aciertos = []   # [(titulo_esperado, posicion_1based)]
    faltantes = []
    for esp in esperados:
        posicion = None
        for i, rec in enumerate(recuperados, start=1):
            if _coincide(esp, rec):
                posicion = i
                break
        if posicion is not None:
            aciertos.append((esp, posicion))
        else:
            faltantes.append(esp)

    return {
        "consulta": consulta,
        "esperados": esperados,
        "aciertos": aciertos,
        "faltantes": faltantes,
        "n_ok": len(aciertos),        # = len(aciertos) por construcción
        "n_total": len(esperados),
    }


def _resumir(filas: List[dict]) -> dict:
    """Calcula los agregados a partir EXCLUSIVAMENTE de `filas`.

    - micro = (suma de encontrados) / (suma de esperados) sobre las mismas
      filas del desglose.
    - macro = promedio de los porcentajes individuales de cada fila.
    """
    total_ok = sum(f["n_ok"] for f in filas)
    total_esp = sum(f["n_total"] for f in filas)
    micro = total_ok / total_esp if total_esp else 0.0
    porcentajes = [
        (f["n_ok"] / f["n_total"] if f["n_total"] else 0.0) for f in filas
    ]
    macro = sum(porcentajes) / len(filas) if filas else 0.0
    return {
        "total_ok": total_ok,
        "total_esp": total_esp,
        "micro": micro,
        "macro": macro,
    }


def _verificar(filas: List[dict], resumen: dict) -> List[str]:
    """Auto-chequeo: el resumen DEBE cuadrar con el desglose impreso.

    Recalcula el numerador del micro de forma independiente (contando los
    aciertos realmente listados en cada fila) y lo compara contra `n_ok` y
    contra el total del resumen. Cualquier divergencia es un bug de cálculo.
    Devuelve la lista de problemas (vacía = todo consistente).
    """
    problemas = []

    # 1) Por fila: la cuenta n_ok debe igualar los aciertos efectivamente
    #    listados, y n_ok no puede exceder n_total.
    for f in filas:
        if f["n_ok"] != len(f["aciertos"]):
            problemas.append(
                f"{f['consulta']!r}: n_ok={f['n_ok']} != aciertos listados="
                f"{len(f['aciertos'])}"
            )
        if f["n_ok"] > f["n_total"]:
            problemas.append(
                f"{f['consulta']!r}: n_ok={f['n_ok']} > esperados={f['n_total']}"
            )

    # 2) Numerador del micro reconstruido contando aciertos, en vez de sumar
    #    n_ok: dos caminos independientes hacia el mismo número.
    ok_recontado = sum(len(f["aciertos"]) for f in filas)
    if ok_recontado != resumen["total_ok"]:
        problemas.append(
            f"total encontrados recontado={ok_recontado} != "
            f"resumen.total_ok={resumen['total_ok']}"
        )

    # 3) El denominador debe ser la suma de esperados del desglose.
    esp_recontado = sum(f["n_total"] for f in filas)
    if esp_recontado != resumen["total_esp"]:
        problemas.append(
            f"total esperados recontado={esp_recontado} != "
            f"resumen.total_esp={resumen['total_esp']}"
        )

    return problemas


def _formatear(modelo: str, filas: List[dict], resumen: dict,
               problemas: List[str], momento: str) -> str:
    """Arma el bloque de texto (markdown) de UNA corrida.

    El MISMO string se imprime en pantalla y se apendea al archivo, así no
    hay chance de que consola y registro difieran.
    """
    L = []
    L.append(f"## Corrida {momento}")
    L.append("")
    L.append(f"- **Modelo de embeddings:** `{modelo}`")
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
             f"{resumen['total_ok']}/{resumen['total_esp']} = "
             f"{resumen['micro']:.1%}")
    L.append(f"- **Recall macro** (promedio de los {len(filas)} porcentajes): "
             f"{resumen['macro']:.1%}")
    if problemas:
        L.append(f"- **⚠️ VERIFICACIÓN FALLÓ (bug de cálculo):**")
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

    # Silenciamos el logging de INFO del buscador para no tapar el reporte.
    logging.getLogger().setLevel(logging.WARNING)

    buscador = BuscadorRAG()

    # Una única fuente de verdad: la lista de filas.
    filas = [
        _evaluar_consulta(buscador, consulta, esperados)
        for consulta, esperados in EVAL_SET
    ]
    resumen = _resumir(filas)
    problemas = _verificar(filas, resumen)

    momento = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    bloque = _formatear(MODELO_EMBEDDING, filas, resumen, problemas, momento)

    # Pantalla.
    print(bloque)

    # Registro acumulativo (append). Si el archivo no existe, encabezado.
    nuevo = not os.path.exists(ARCHIVO_RESULTADOS)
    with open(ARCHIVO_RESULTADOS, "a", encoding="utf-8") as fh:
        if nuevo:
            fh.write("# Resultados de evaluación de retrieval\n\n")
            fh.write("Registro acumulativo. Cada corrida se apendea abajo.\n\n")
        fh.write(bloque)

    print(f"[registro acumulado en {ARCHIVO_RESULTADOS}]")
    if problemas:
        print("[⚠️ la verificación detectó inconsistencias; ver arriba]")


if __name__ == "__main__":
    main()
