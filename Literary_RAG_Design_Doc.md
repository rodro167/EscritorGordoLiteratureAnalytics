# Design Document: Analizador de Obra Literaria de Escritor Gordo

## 1. Visión y Objetivos

### 1.1 Propósito
Crear un sistema RAG ("Analizador de Obra Literaria de Escritor Gordo") que analice tu obra literaria personal (blog + textos locales) para descubrir patrones de estilo, evolución temporal, temas recurrentes, y relaciones entre textos. El sistema responde preguntas específicas sobre tu escritura y proporciona insights que te ayuden a entender tu propia voz.

### 1.2 Scope
- **Alcance temporal:** 13 años (2012-2025)
- **Volumen:** ~40 documentos (30 blog + 10 locales)
- **Categorías:** Cuentos, Fruta de Estación (textos sobre hechos reales/históricos)
- **Granularidad:** análisis por post, período, tema, categoría
- **Interfaz:** Streamlit (responsador de preguntas, candidato a evolucionar a proactivo)

### 1.3 No es (límites claros)
- No es un generador de textos automáticos
- No es un clasificador de género literario
- No compara tu obra con otros autores en la BD (futura extensión)
- No hace sugerencias de escritura (Fase 2)

---

## 2. Casos de Uso Esperados

### 2.1 Análisis de Estilo
```
Usuario: "¿Cuál es mi recurso literario más recurrente?"
Respuesta esperada: 
"En tus últimos 5 años, predomina la [X técnica]. 
Aparece en estos posts: [lista]. 
Evolucionó desde [forma antigua] a [forma actual]."
```

### 2.2 Evolución Temporal
```
Usuario: "¿Cómo cambió mi tono entre 2012-2015 y 2020-2025?"
Respuesta esperada:
"En 2012-2015: más narrativa autobiográfica, finales abiertos.
En 2020-2025: más distancia irónica, cierre de círculos temáticos."
```

### 2.3 Análisis Temático
```
Usuario: "¿Qué textos abordan [tema: memoria/infancia/ficción]?"
Respuesta esperada:
"Encontré 7 posts relacionados. En Cuentos: [posts], 
En Fruta de Estación: [posts]. Las similitudes son [...]."
```

### 2.4 Comparación Intertextual
```
Usuario: "¿Hay textos que sean 'ecos' unos de otros?"
Respuesta esperada:
"El cuento X (2018) y el post de Fruta Y (2022) comparten 
[estructura/tema/resolución]. Diferencias clave: [...]."
```

### 2.5 Análisis de Categoría
```
Usuario: "Analiza solo mis Cuentos. ¿Hay un patrón en los finales?"
Respuesta esperada:
"De tus 15 cuentos, X% terminan con [patrón A], Y% con [patrón B].
Evolución: de 2012 a 2025, pasaste de [A] a [B]."
```

---

## 3. Arquitectura Técnica

### 3.1 Flujo General

```
┌──────────────────────────────────────┐
│  Ingesta de Textos (Blog + Local)    │
│  .md files con metadata               │
└────────────────┬─────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────┐
│  Parsing y Metadata Extraction        │
│  (categoría, fecha, tema, autor)      │
└────────────────┬─────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────┐
│  Chunking (respeta límites de post)   │
│  Chunks = párrafos o secciones        │
└────────────────┬─────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────┐
│  Embedding (Claude Embeddings API)   │
│  Vector dimension: 1536               │
└────────────────┬─────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────┐
│  ChromaDB Local (persiste embeddings) │
│  + metadata (categoría, fecha, post)  │
└────────────────┬─────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────┐
│  Streamlit UI                        │
│  (filtros + preguntas + respuestas)   │
└────────────────┬─────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────┐
│  Claude API (sonnet-4-6)             │
│  (sintetiza chunks, responde)         │
└──────────────────────────────────────┘
```

### 3.2 Componentes Principales

#### 3.2.1 Ingesta & Parsing
- **Input:** Archivos .md con estructura simple
- **Metadata requerida (en el archivo o en el nombre):**
  ```
  titulo: El Pozo de Estrellas
  categoria: Cuento | Fruta de Estacion
  fecha: 2015-03-20
  tema: [tags opcionales, ej: memoria, infancia, ficción]
  ```
- **Output:** Lista de documents con metadata embebida

#### 3.2.2 Chunking
- **Estrategia:** respetar límites de post (no fragmentar entre posts)
- **Tamaño de chunk:** 500-800 tokens (aproximadamente 1-2 párrafos)
- **Overlap:** 100 tokens (para continuidad)
- **Herramienta:** RecursiveCharacterTextSplitter (LangChain)

#### 3.2.3 Embedding
- **Modelo:** Claude Embeddings API (via Anthropic SDK)
- **Dimensión:** 1536
- **Por qué Claude:** ya usás la API, un solo auth, integración natural

#### 3.2.4 Vector Database
- **ChromaDB:** local, sin servidor, Python-friendly
- **Metadata filtrable:**
  - `post_id` (identificador único)
  - `titulo`
  - `categoria` (Cuento / Fruta de Estacion)
  - `fecha` (ISO 8601)
  - `tema` (lista de tags)
- **Persistencia:** archivo local `chroma.db`

#### 3.2.5 Retrieval
- **Query embedding:** pregunta del usuario → embedding
- **Search:** cosine similarity en ChromaDB
- **Filtros:** antes del embedding, para respetar categoría/período/tema
- **Top-k:** 10-15 chunks relevantes (configurable)

#### 3.2.6 LLM Integration
- **Modelo:** Claude Sonnet 4.6
- **Prompt pattern:**
  ```
  Sistema: Eres un crítico literario experto analizando la obra de [autor].
  Contexto (fragmentos relevantes):
  [chunks recuperados]
  
  Pregunta del usuario:
  [pregunta]
  
  Responde basándote en los fragmentos anteriores. Cita con [post: título, fecha].
  ```
- **Por qué Sonnet:** velocidad + calidad + costo balance

#### 3.2.7 Interfaz Streamlit
**Layout propuesto:**

```
┌─────────────────────────────────────────────┐
│  Analizador de Obra Literaria Personal      │
└─────────────────────────────────────────────┘

[Sidebar]
├─ Filtro de Categoría (multiselect)
├─ Rango de fechas (slider)
├─ Filtro de Tema (tags)
└─ Top-K results (slider)

[Main]
├─ Textarea: "¿Tu pregunta sobre tu escritura?"
├─ Botón: [Analizar]
└─ Respuesta + chunks fuente con links
```

---

## 4. Flujo de Datos: Ejemplo Concreto

### Escenario: "¿Qué temas traté en mis Cuentos entre 2018 y 2022?"

1. **Usuario:** escribe pregunta, selecciona categoría=Cuento, rango 2018-2022
2. **Filtrado:** ChromaDB retorna solo chunks de esa categoría y período (~80 chunks)
3. **Embedding:** pregunta se convierte a vector
4. **Retrieval:** top-10 chunks más similares
5. **Prompt Assembly:**
   ```
   Sistema: Eres crítico de la obra de Rodro...
   
   Fragmentos de Cuentos (2018-2022):
   [chunk 1 - cuento A, 2018]
   [chunk 2 - cuento B, 2020]
   ...
   
   Pregunta: ¿Qué temas traté en mis Cuentos entre 2018 y 2022?
   ```
6. **Claude responde:** sintetiza, lista temas, da ejemplos
7. **Output:** respuesta + tabla de posts citados

---

## 5. Plan de Implementación

### Fase 1: MVP (2-3 semanas)

#### 1.1 Preparación de datos
- [ ] Extrae 30 posts del blog (HTML → MD)
- [ ] Convierte 10 textos locales a MD
- [ ] Estructura con metadata:
  ```markdown
  ---
  titulo: "El Pozo de Estrellas"
  categoria: "Cuento"
  fecha: "2015-03-20"
  tema: ["memoria", "infancia"]
  ---
  
  [contenido del texto]
  ```
- [ ] Valida que no haya posts duplicados
- [ ] Suma total de tokens (~estimación)

#### 1.2 Ingesta & ChromaDB
- [ ] Script Python: lee .md, extrae metadata, crea documents
- [ ] Chunking: RecursiveCharacterTextSplitter
- [ ] Test: verifica que cada chunk tiene metadata intacta
- [ ] Embedding & almacenamiento en ChromaDB
- [ ] Prueba de persistencia (cierra, reabre DB)

#### 1.3 Retrieval + Claude Integration
- [ ] Función: `retrieve_with_filters(query, categoria=None, fecha_desde=None, tema=None)`
- [ ] Test queries manuales contra ChromaDB
- [ ] Integración Claude API
- [ ] Prompt template robusto (con citas)

#### 1.4 Streamlit MVP
- [ ] Sidebar: filtro categoría, rango fechas
- [ ] Main: textarea + botón analizar
- [ ] Output: respuesta + tabla de posts citados
- [ ] Error handling (query vacía, sin resultados)

#### 1.5 Validación
- [ ] 10 preguntas tipo = respuestas correctas
- [ ] Chunks recuperados = relevantes visualmente
- [ ] Citas = correctas (post existe, fecha OK)

**Deliverable:** repo con estructura clara, app Streamlit funcional, 40 posts indexados.

---

### Fase 2: Análisis Comparativo (3-4 semanas post-MVP)

- [ ] Función: `analyze_intertextual_echoes()` (encuentra textos similares)
- [ ] Función: `analyze_evolution(tema, period_from, period_to)` (cambio temporal)
- [ ] UI: "Modo Análisis Comparativo" (preguntas guiadas)
- [ ] Visualizaciones: timeline de temas, heatmap de similitud

---

### Fase 3: Insights Proactivos (Opcional, futura)

- [ ] Clustering: agrupa posts por tema automáticamente
- [ ] Sugerencias: "Encontré estos 3 temas recurrentes..."
- [ ] Recomendaciones: "Podrías conectar estos dos posts..."

---

## 6. Stack Técnico & Dependencias

```
Python 3.10+

Core:
- langchain==0.1.x (manejo RAG, splitters, prompts)
- chromadb==0.4.x (vector DB local)
- anthropic==0.25.x (Claude API)

UI:
- streamlit==1.31.x (interfaz web)
- pandas==2.1.x (tables, metadata)

Utilities:
- python-dateutil (parsing de fechas)
- pathlib (lectura de archivos)
```

**Archivo de requirements.txt:**
```
langchain==0.1.10
chromadb==0.4.17
anthropic==0.25.0
streamlit==1.31.0
pandas==2.1.0
python-dateutil==2.8.2
```

---

## 7. Estructura del Proyecto

```
literary-rag/
├── README.md
├── requirements.txt
├── .env (Claude API key)
├── config.yaml (parámetros)
├── data/
│   ├── textos/ (40 archivos .md)
│   └── chroma.db/ (ChromaDB persisted)
├── src/
│   ├── __init__.py
│   ├── ingestion.py (lectura, parsing, metadata)
│   ├── embedding.py (vectorización)
│   ├── retrieval.py (búsqueda con filtros)
│   ├── llm.py (integración Claude)
│   └── analysis.py (análisis comparativo, futuro)
├── app.py (Streamlit main)
├── tests/ (validación unitaria)
└── notebooks/ (experimentación)
```

---

## 8. Decisiones Técnicas Justificadas

| Decisión | Alternativa | Por qué elegimos esto |
|----------|-------------|----------------------|
| **ChromaDB** | Pinecone, Weaviate, Qdrant | Local, sin costo, sin auth extra, fácil dev |
| **Claude Embeddings** | OpenAI, HuggingFace | Ya usás API Anthropic, integración limpia |
| **Claude Sonnet** | GPT-4, GPT-3.5 | Equilibrio velocidad/costo, análisis literario necesita nuance |
| **LangChain** | LlamaIndex, raw API | Abstracciones limpias para RAG, comunidad activa |
| **Streamlit** | Flask, Django, FastAPI | Prototipado rápido, UI sin HTML custom |
| **Chunking respeta posts** | Chunking global | Preserva coherencia narrativa, metadata intacta |

---

## 9. Métricas de Éxito

### 9.1 Técnicas

1. **Relevancia de retrieval:**
   - Haces 10 preguntas → chequeas si top-3 chunks son relevantes
   - Meta: 80%+ precisión en que el chunk responda la pregunta

2. **Calidad de respuesta:**
   - Pregunta: "¿Dónde aparece el tema X?"
   - Validación: respuesta cita posts reales con ese tema
   - Meta: 100% de citas correctas

3. **Latencia:**
   - Tiempo pregunta → respuesta < 5 segundos (sin caché)
   - Meta: sub-3 segundos después de caché

### 9.2 Semánticas

1. **¿El sistema entendió tu escritura?**
   - Pregunta: "¿Cuál es mi recurso más usado?"
   - Validas: ¿la respuesta coincide con lo que vos sabés de vos?
   - Meta: sí de primera, sin sorpresas desagradables

2. **¿Las relaciones intertextuales son reales?**
   - Sistema: "Los posts X e Y son similares"
   - Validas: leés ambos, ¿realmente lo son?
   - Meta: 70%+ de conexiones son intuitivas

3. **¿Descubriste algo nuevo sobre tu obra?**
   - Después de usar el sistema 1-2 semanas
   - "¿Encontré un patrón que no veía antes?"
   - Meta: sí (aunque sea pequeño)

---

## 10. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|--------|-----------|
| Chunks fragmentados entre posts | Media | Bajo | Chunking explícito por límite de post |
| Embeddings no capturan nuance literario | Baja | Medio | Test con queries específicas, ajustar prompt |
| ChromaDB crece y es lento | Baja | Bajo | Solo 40 docs, no hay problema escala |
| Metadata inconsistente | Media | Medio | Template YAML estricto, validación en ingestión |
| Claude no entiende contexto literario | Baja | Medio | Prompt system detallado, ejemplos en prompt |

---

## 11. Siguientes Pasos Inmediatos

### Para vos (Rodro):
1. Recopila los 30 posts en .md (estructura simple)
2. Convierte los 10 textos locales a .md
3. Agrega metadata a cada archivo (YAML frontmatter)
4. Valida consistencia de fechas y categorías

### Para nosotros (coding):
1. Armar script de ingesta & parsing
2. Setear ChromaDB + embedding pipeline
3. Build Streamlit MVP
4. Test end-to-end

---

## 12. Notas Finales

Este proyecto es **ideal como puente entre performance testing y análisis literario**. Aprendes RAG en profundidad, la validación es intuitiva (vos sabés si está bien), y luego escalás con MCP cuando entiendas dónde agregues valor.

La heterogeneidad de tus textos (Cuentos + Fruta de Estación) es una **ventaja**, no un problema — permite explorar cómo el mismo autor se mueve entre registros.

Adelante con la recopilación. Una vez tengas los .md, pasamos a código.

---

**Versión:** 1.0  
**Fecha:** Junio 2025  
**Autor del doc:** Claude (Haiku)  
**Autor del proyecto:** Escritor Gordo (Rodro, Córdoba, Argentina)  
**Anagrama:** Rodrigo Cortés → Escritor Gordo  
