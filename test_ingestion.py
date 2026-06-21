"""
Test automático del módulo src/ingestion.py (PASO 1).

No interactivo: pasa o falla solo. Carga los documentos con
cargar_documentos() y valida estructura, metadata y contenido.

Ejecutable con:  python test_ingestion.py
"""

import os
import re
import sys

# La consola de Windows usa cp1252 y no puede imprimir ✓/✗/emojis.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

# Permite ejecutar desde la raíz del proyecto importando src/.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ingestion import cargar_documentos


# --- Constantes esperadas -------------------------------------------------
TOTAL_TITULOS_ESPERADOS = 40
CAMPOS_METADATA = ["titulo", "categoria", "fecha", "tema", "chunk_numero"]
# Ortografía REAL en los .md: "Fruta de Estación" lleva tilde.
CATEGORIAS_VALIDAS = {"Cuento", "Fruta de Estación"}
_FECHA_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

OK = "✓"
FAIL = "✗"


def main() -> int:
    print("=" * 60)
    print("TEST DE INGESTA — src/ingestion.py")
    print("=" * 60)

    docs = cargar_documentos()
    print(f"\nChunks cargados: {len(docs)}\n")

    fallos = []  # lista de descripciones de tests fallidos

    # --- Test 1: 40 títulos únicos ---------------------------------------
    titulos = {d.metadata.get("titulo") for d in docs}
    if len(titulos) == TOTAL_TITULOS_ESPERADOS:
        print(f"{OK} Test 1: {len(titulos)} títulos únicos "
              f"(esperados {TOTAL_TITULOS_ESPERADOS})")
    else:
        print(f"{FAIL} Test 1: {len(titulos)} títulos únicos "
              f"(esperados {TOTAL_TITULOS_ESPERADOS})")
        fallos.append("Test 1: cantidad de títulos únicos incorrecta")

    # --- Test 2: campos de metadata presentes en cada chunk --------------
    chunks_incompletos = []
    for i, d in enumerate(docs):
        faltantes = [c for c in CAMPOS_METADATA if c not in d.metadata]
        if faltantes:
            chunks_incompletos.append((i, d.metadata.get("titulo"), faltantes))
    if not chunks_incompletos:
        print(f"{OK} Test 2: todos los chunks tienen los campos "
              f"{CAMPOS_METADATA}")
    else:
        print(f"{FAIL} Test 2: {len(chunks_incompletos)} chunks con campos "
              f"faltantes")
        for idx, tit, falt in chunks_incompletos[:5]:
            print(f"      - chunk #{idx} ('{tit}'): faltan {falt}")
        fallos.append("Test 2: chunks con metadata incompleta")

    # --- Test 3: fechas con formato YYYY-MM-DD ---------------------------
    fechas_invalidas = []
    for d in docs:
        fecha = str(d.metadata.get("fecha", ""))
        if not _FECHA_RE.match(fecha):
            fechas_invalidas.append((d.metadata.get("titulo"), fecha))
    fechas_invalidas = sorted(set(fechas_invalidas))
    if not fechas_invalidas:
        print(f"{OK} Test 3: todas las fechas tienen formato YYYY-MM-DD")
    else:
        print(f"{FAIL} Test 3: {len(fechas_invalidas)} fecha(s) con formato "
              f"inválido")
        for tit, fecha in fechas_invalidas[:5]:
            print(f"      - '{tit}': fecha='{fecha}'")
        fallos.append("Test 3: fechas con formato inválido")

    # --- Test 4: categorías válidas --------------------------------------
    categorias_invalidas = []
    for d in docs:
        cat = d.metadata.get("categoria")
        if cat not in CATEGORIAS_VALIDAS:
            categorias_invalidas.append((d.metadata.get("titulo"), cat))
    categorias_invalidas = sorted(set(categorias_invalidas))
    if not categorias_invalidas:
        cats_presentes = sorted({d.metadata.get("categoria") for d in docs})
        print(f"{OK} Test 4: todas las categorías son válidas "
              f"{cats_presentes}")
    else:
        print(f"{FAIL} Test 4: {len(categorias_invalidas)} categoría(s) "
              f"inválida(s) (válidas: {sorted(CATEGORIAS_VALIDAS)})")
        for tit, cat in categorias_invalidas[:10]:
            print(f"      - título '{tit}': categoría='{cat}'")
        fallos.append("Test 4: categorías inválidas")

    # --- Test 5: ningún page_content vacío -------------------------------
    vacios = [i for i, d in enumerate(docs) if not d.page_content.strip()]
    if not vacios:
        print(f"{OK} Test 5: ningún chunk tiene page_content vacío")
    else:
        print(f"{FAIL} Test 5: {len(vacios)} chunk(s) con page_content vacío")
        print(f"      - índices: {vacios[:10]}")
        fallos.append("Test 5: chunks con contenido vacío")

    # --- Resumen final ---------------------------------------------------
    print("\n" + "=" * 60)
    if not fallos:
        print("✅ TODOS LOS TESTS PASARON")
        print("=" * 60)
        return 0
    print(f"❌ FALLARON {len(fallos)} TESTS")
    for f in fallos:
        print(f"   - {f}")
    print("=" * 60)
    return 1


if __name__ == "__main__":
    sys.exit(main())
