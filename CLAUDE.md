# CLAUDE.md - Analizador de Obra Literaria de Escritor Gordo

## Proyecto: Fase 1 - MVP RAG

**Objetivo:** Sistema de Retrieval-Augmented Generation para analizar obra literaria personal  
**Autor:** Rodro (Escritor Gordo, Córdoba, Argentina)  
**Stack:** Python + LangChain + ChromaDB + Claude API  

---

## Contexto

El usuario tiene:
- **40 documentos literarios** en `data/textos/` (30 blog + 10 locales)
- **Categorías:** Cuento / Fruta de Estación (textos sobre hechos reales/históricos)
- **Período:** 2012-2025 (13 años de escritura)
- **Formato:** Markdown con YAML frontmatter

Estructura de cada archivo:
```markdown
---
titulo: "El Pozo de Estrellas"
categoria: "Cuento"
fecha: "2015-03-20"
tema: []
---

[contenido del documento]
```

---

## Arquitectura Fase 1

```
Paso 1: INGESTA
  ↓ Carga 40 .md → extrae metadata → chunea contenido
  ↓ Output: LangChain Document objects

Paso 2: EMBEDDING + ChromaDB
  ↓ Vectoriza chunks (sentence-transformers, modelo multilingüe
  ↓   open source, corre local, sin costo ni API key) → almacena en BD local
  ↓ Output: ChromaDB con 572 chunks indexados

Paso 3: RETRIEVAL + Tests
  ↓ Búsqueda con filtros → valida funcionamiento
  ↓ Output: Chunks relevantes por similitud
```

---

## Requisitos Instalados

```
langchain==0.1.10
langchain-community==0.0.11
chromadb==0.4.17
sentence-transformers       # embeddings locales (Paso 2)
anthropic==0.25.0           # solo LLM en Paso 3, NO para embeddings
python-dateutil==2.8.2
pyyaml==6.0
```

Instalar con: `pip install -r requirements.txt`

---

## Estructura de Directorios

```
escritor-gordo-rag/
├── data/
│   ├── textos/              # 40 archivos .md (inputs)
│   └── chroma.db/           # ChromaDB (se crea en Paso 2)
├── src/
│   ├── ingestion.py         # Cargador (PASO 1)
│   ├── embedding.py         # Vectorización (PASO 2)
│   └── retrieval.py         # Búsqueda (PASO 3)
├── test_ingestion.py        # Tests PASO 1
├── test_embedding.py        # Tests PASO 2
├── test_retrieval.py        # Tests PASO 3
├── requirements.txt
└── CLAUDE.md                # Este archivo
```

---

## Estado Actual

**PASO 1 - INGESTA:** ✅ src/ingestion.py completo — 40 archivos → 572 chunks.
test_ingestion.py ✅ hecho.

**PASO 2 - EMBEDDING + ChromaDB:** ✅ src/embedding.py creado — 572 chunks
indexados en data/chroma.db/ con el modelo
paraphrase-multilingual-MiniLM-L12-v2 (384 dims), colección "escritor_gordo".

**PASO 3 - RETRIEVAL:** ✅ src/retrieval.py creado — clase BuscadorRAG con
buscar(query, categoria, fecha_desde, fecha_hasta, top_k) sobre la base
existente, sin re-indexar. Filtros validados: categoría y período funcionando.

**PASO 4 - SÍNTESIS LLM:** Pendiente — conectar Claude para que arme respuestas
en prosa a partir de los chunks recuperados.

---

## Notas / deuda técnica

- **Filtro de fechas (Paso 3):** el rango de fechas se resuelve en Python
  post-query, no en el motor, porque ChromaDB 1.5.9 no acepta `$gte`/`$lte`
  sobre strings (solo int/float). Funciona porque `YYYY-MM-DD` ordena
  lexicográficamente = cronológicamente. Solución canónica futura, si hiciera
  falta: re-indexar agregando un campo `fecha_num` (int `YYYYMMDD`) a la
  metadata y usar `$gte`/`$lte` sobre ese campo. Irrelevante a 572 chunks.

---

## Notas de Desarrollo

- **Lenguaje:** Python 3.8+
- **Logging:** nivel INFO
- **Encoding:** UTF-8 obligatorio
- **Errors:** graceful degradation (skip problema → continúa)

---

**Versión:** 1.0 Fase 1  
**Estado:** En desarrollo  
**Última actualización:** Junio 2025
