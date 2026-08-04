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
python-dotenv               # carga ANTHROPIC_API_KEY desde .env (Paso 4)
streamlit                   # interfaz web (Paso 5): streamlit run app.py
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
│   ├── retrieval.py         # Búsqueda (PASO 3)
│   └── sintesis.py          # Síntesis con LLM (PASO 4)
├── app.py                   # Interfaz web Streamlit (PASO 5)
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

**PASO 2 - EMBEDDING + ChromaDB:** ✅ src/embedding.py creado — 577 chunks
indexados en data/chroma.db/ con el modelo `BAAI/bge-m3` (1024 dims),
colección "escritor_gordo". El modelo se elige vía la constante
`MODELO_EMBEDDING`. Inicialmente se usó `paraphrase-multilingual-MiniLM-L12-v2`
(384 dims); tras el experimento comparativo del frente 1 (ver ROADMAP.md) se
adoptó bge-m3, reemplazando al MiniLM inicial.

**PASO 3 - RETRIEVAL:** ✅ src/retrieval.py creado — clase BuscadorRAG con
buscar(query, categoria, fecha_desde, fecha_hasta, top_k) sobre la base
existente, sin re-indexar. Filtros validados: categoría y período funcionando.

**PASO 4 - SÍNTESIS LLM:** ✅ src/sintesis.py creado — clase SintetizadorRAG
con responder(pregunta, categoria, fecha_desde, fecha_hasta, top_k) que recupera
los chunks (vía BuscadorRAG) y arma una respuesta en prosa con Claude Sonnet
(claude-sonnet-4-6), citando los textos de origen. La API key se lee de .env
(ANTHROPIC_API_KEY) con python-dotenv, nunca hardcodeada. Pipeline RAG completo
y validado end-to-end contra la API real.

**PASO 5 - INTERFAZ STREAMLIT:** ✅ app.py creado y probado — UI web en
Streamlit sobre SintetizadorRAG para consultar la obra de forma interactiva.
Filtros de categoría, período (año desde/hasta) y top_k en la barra lateral;
muestra la respuesta en prosa y los textos citados. El motor RAG se instancia
una sola vez con @st.cache_resource (no recarga embeddings ni reabre ChromaDB
en cada interacción). Se ejecuta con `streamlit run app.py`. Fase 1 (MVP RAG)
cerrada.

---

## Notas / deuda técnica

- **Filtro de fechas (Paso 3):** el rango de fechas se resuelve en Python
  post-query, no en el motor, porque ChromaDB 1.5.9 no acepta `$gte`/`$lte`
  sobre strings (solo int/float). Funciona porque `YYYY-MM-DD` ordena
  lexicográficamente = cronológicamente. Solución canónica futura, si hiciera
  falta: re-indexar agregando un campo `fecha_num` (int `YYYYMMDD`) a la
  metadata y usar `$gte`/`$lte` sobre ese campo. Irrelevante a 572 chunks.

- **Ruido de tracebacks al levantar Streamlit (Paso 5):** al arrancar con
  `streamlit run app.py` aparecen muchos tracebacks
  `ModuleNotFoundError: No module named 'torchvision'`. Son ruido del
  file-watcher de Streamlit inspeccionando `transformers`, NO afectan el
  funcionamiento de la app. Pendiente: silenciarlos, sea desactivando el
  watcher (`server.fileWatcherType = "none"`) o instalando `torchvision`.

- **Calidad de retrieval (frente 1, en curso):** se comparó el modelo de
  embeddings (MiniLM → mpnet → bge-m3) con el eval set de 15 consultas
  (`evaluar_retrieval.py`, registro en `resultados_eval.md`). Hallazgo: el
  recall global casi no se mueve (~48–53% micro en los tres); cambiar el
  modelo reparte distinto pero no sube el total. Se adoptó `BAAI/bge-m3` por
  afinidad con el análisis literario (gana en consultas emocionales/abstractas),
  no por recall. Hipótesis viva: el cuello de botella es el CHUNKING (o
  consultas intrínsecamente difíciles como "humor e ironía", que ningún modelo
  movió). Detalle y próximos pasos en ROADMAP.md, frente 1.

---

## Notas de Desarrollo

- **Lenguaje:** Python 3.8+
- **Logging:** nivel INFO
- **Encoding:** UTF-8 obligatorio
- **Errors:** graceful degradation (skip problema → continúa)

---

**Versión:** 1.0 Fase 1  
**Estado:** Fase 1 (MVP RAG) cerrada  
**Última actualización:** Agosto 2025
