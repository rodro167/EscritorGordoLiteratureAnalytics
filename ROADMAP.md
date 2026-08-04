# Roadmap — Analizador de Obra Literaria de Escritor Gordo

## Estado
Fase 1 (MVP RAG) COMPLETA y versionada: ingesta (577 chunks) → embeddings
locales (`BAAI/bge-m3`, multilingüe, 1024 dims) + ChromaDB → retrieval con
filtros → síntesis con Claude Sonnet → interfaz Streamlit.

## Diagnóstico pendiente (detectado al probar la Fase 1)
El retrieval con el modelo actual (paraphrase-multilingual-MiniLM-L12-v2)
prioriza coincidencia léxica sobre evocación sutil. Ejemplo concreto: la
consulta "nostalgia de la infancia" NO recupera "Mañana sin hechizo", que
es el texto más nostálgico del corpus, porque su carga emotiva es
metafórica e indirecta (no usa la palabra). Causas: (a) modelo de
embeddings pequeño; (b) dilución del chunk al mezclar el núcleo temático
con el contexto que lo rodea.

## Frentes de trabajo (en orden sugerido)

### 1. Mejoras de calidad del retrieval (PRIORITARIO)

**Hallazgo del experimento de modelos (hecho):** se compararon tres modelos
de embeddings (MiniLM → mpnet → bge-m3) con el eval set de 15 consultas
(`evaluar_retrieval.py`, registro en `resultados_eval.md`). Recall global de
los tres: ~48–53% micro — prácticamente empatados. **Conclusión: cambiar el
modelo de embeddings NO mueve el recall global.** Reparte distinto (bge-m3
gana en consultas emocionales/abstractas como "angustia" 5/5 y "absurdo"
4/8, pierde en referenciales como "países" 2/6 e "individuos notables" 1/5),
pero el total queda igual. Se eligió **bge-m3** por afinidad con el análisis
literario, **no por recall**. Hipótesis viva: el cuello de botella no es el
modelo sino probablemente el **chunking** (o consultas intrínsecamente
difíciles como "humor e ironía", que ningún modelo movió). Nota: la palanca
"modelo de embeddings" de abajo queda saldada; el foco pasa a chunking.

Palancas:
- Probar un modelo de embeddings más potente (multilingüe, más grande) y
  re-indexar. Experimento de control: repetir la query "nostalgia de la
  infancia" y ver si aparece "Mañana sin hechizo".
- Revisar la estrategia de chunking (tamaño, límites por unidad de sentido).
- Avanzado: búsqueda híbrida (semántica + palabras clave) y/o re-ranking.
- Armar un conjunto de evaluación (eval set): ~15-20 consultas con sus
  documentos esperados, para medir mejoras de retrieval con números y no
  con impresiones. Primer caso ya identificado por testing exploratorio:
  "nostalgia de la infancia" debe recuperar "Mañana sin hechizo" (hoy no
  lo hace). Métricas de referencia: recall y precisión (y orden: MRR/nDCG).
  Este set se corre antes/después de cada cambio (modelo de embeddings,
  chunking) para comparar objetivamente. La evaluación de la síntesis
  (fidelidad, relevancia, correctitud de citas) queda como capa posterior.

### 2. MCP (objetivo original del proyecto)
Envolver BuscadorRAG en un servidor MCP para exponer "preguntarle a la
obra" como herramienta invocable por clientes MCP (ej. Claude Desktop).
Decisión de diseño a tomar: exponer solo el retrieval (fragmentos crudos)
vs. la síntesis completa (pregunta→prosa). Conviene hacerlo DESPUÉS de las
mejoras de calidad, para exponer un buscador ya afinado.

### 3. Fase 2 del design original (análisis comparativo)
Detectar ecos entre textos, evolución temporal de temas, visualizaciones.
De "respondeme sobre mi obra" a "mostrame patrones que no veo".

## Retoques de comodidad (intercalar cuando molesten)
- Silenciar el ruido de torchvision al levantar Streamlit (desactivar el
  file-watcher o instalar torchvision).
- Barra de progreso / feedback visual durante la ingesta y el embedding.
- Acceso directo con el verde retro sin privilegios de administrador.
