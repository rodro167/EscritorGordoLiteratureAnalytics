# Resultados de evaluación de retrieval

Registro acumulativo. Cada corrida se apendea abajo.

## Corrida 2026-08-02 21:05:03

- **Modelo de embeddings:** `paraphrase-multilingual-MiniLM-L12-v2`
- **top_k:** 20
- **Consultas:** 15

### Desglose por consulta

| # | Consulta | Enc./Esp. | Faltaron |
|---|---|---|---|
| 1 | nostalgia de la infancia | 1/3 | Pasado, Historia de una niña |
| 2 | resistencia a las dictaduras | 3/4 | La flor de Jinotepe |
| 3 | posibles alegorías | 1/3 | Las voces, Fragmentos de un diario de viaje |
| 4 | anécdotas juveniles | 1/3 | Córdoba, 1993, Una breve carrera |
| 5 | soledad y desencuentro | 3/5 | Caminos separados, La noche de Lucía |
| 6 | individuos notables | 2/5 | El León del desierto, Bestie, el de los laberintos invisibles, La flor de Jinotepe |
| 7 | humor e ironía | 2/6 | Las marchas escolares y la crisis del sentir patriótico, Una breve carrera, Manual Instructivo Misceláneo de Escritor Gordo (selección), Un paseo por el cielo |
| 8 | absurdo y exageración | 2/8 | Así funciona este mundo, La herencia del señor Skoglund, La casa 314, Un paseo por el cielo, Foto con Cartucho, Teoría de Rasmussen |
| 9 | base histórica o mitológica | 3/5 | Un olvido feliz de Galeano, Tu voz seguirá viviendo |
| 10 | angustia y desesperación | 3/5 | Las voces, El recorrido |
| 11 | ubicación geográfica explícita o sugerida | 2/6 | Una breve carrera, Un paseo por el cielo, Héroes de Haymarket, Las trece rosas |
| 12 | juegos de palabras o doble sentido | 1/1 | — |
| 13 | referencias al deporte, real o ficticio | 3/4 | Una breve carrera |
| 14 | menciones de países o nacionalidades | 4/6 | Pasado, Bestie, el de los laberintos invisibles |
| 15 | pérdida de ser querido o muerte en general | 4/6 | Pasado, Última noticia |

### Resumen (calculado desde el desglose de arriba)

- **Total encontrados:** 1 + 3 + 1 + 1 + 3 + 2 + 2 + 2 + 3 + 3 + 2 + 1 + 3 + 4 + 4 = 35 / 70
- **Recall micro** (Σ encontrados / Σ esperados): 35/70 = 50.0%
- **Recall macro** (promedio de los 15 porcentajes): 53.0%
- **Verificación:** OK — la suma del desglose (35) coincide con el micro reportado.

---
## Corrida 2026-08-02 21:09:33

- **Modelo de embeddings:** `paraphrase-multilingual-mpnet-base-v2`
- **top_k:** 20
- **Consultas:** 15

### Desglose por consulta

| # | Consulta | Enc./Esp. | Faltaron |
|---|---|---|---|
| 1 | nostalgia de la infancia | 2/3 | Historia de una niña |
| 2 | resistencia a las dictaduras | 3/4 | La flor de Jinotepe |
| 3 | posibles alegorías | 1/3 | Las voces, Fragmentos de un diario de viaje |
| 4 | anécdotas juveniles | 1/3 | Una breve carrera, Demagogo serial |
| 5 | soledad y desencuentro | 2/5 | Última noticia, Caminos separados, Pasado |
| 6 | individuos notables | 2/5 | El León del desierto, Bestie, el de los laberintos invisibles, La flor de Jinotepe |
| 7 | humor e ironía | 2/6 | Una breve carrera, Manual Instructivo Misceláneo de Escritor Gordo (selección), La balanza de la injusticia (contrapunto de sonetos), Un paseo por el cielo |
| 8 | absurdo y exageración | 2/8 | Así funciona este mundo, La casa 314, Un paseo por el cielo, Foto con Cartucho, Teoría de Rasmussen, Aviones en Borneo |
| 9 | base histórica o mitológica | 2/5 | Las trece rosas, Un olvido feliz de Galeano, Tu voz seguirá viviendo |
| 10 | angustia y desesperación | 3/5 | Las voces, El recorrido |
| 11 | ubicación geográfica explícita o sugerida | 3/6 | Una breve carrera, Héroes de Haymarket, Las trece rosas |
| 12 | juegos de palabras o doble sentido | 0/1 | Así funciona este mundo |
| 13 | referencias al deporte, real o ficticio | 4/4 | — |
| 14 | menciones de países o nacionalidades | 3/6 | Pasado, Bestie, el de los laberintos invisibles, La herencia del señor Skoglund |
| 15 | pérdida de ser querido o muerte en general | 4/6 | Pasado, Última noticia |

### Resumen (calculado desde el desglose de arriba)

- **Total encontrados:** 2 + 3 + 1 + 1 + 2 + 2 + 2 + 2 + 2 + 3 + 3 + 0 + 4 + 3 + 4 = 34 / 70
- **Recall micro** (Σ encontrados / Σ esperados): 34/70 = 48.6%
- **Recall macro** (promedio de los 15 porcentajes): 47.6%
- **Verificación:** OK — la suma del desglose (34) coincide con el micro reportado.

---
## Corrida 2026-08-02 21:25:29

- **Modelo de embeddings:** `BAAI/bge-m3`
- **top_k:** 20
- **Consultas:** 15

### Desglose por consulta

| # | Consulta | Enc./Esp. | Faltaron |
|---|---|---|---|
| 1 | nostalgia de la infancia | 2/3 | Historia de una niña |
| 2 | resistencia a las dictaduras | 3/4 | La flor de Jinotepe |
| 3 | posibles alegorías | 0/3 | Las voces, Fragmentos de un diario de viaje, Polvo eres |
| 4 | anécdotas juveniles | 1/3 | Córdoba, 1993, Una breve carrera |
| 5 | soledad y desencuentro | 3/5 | Pasado, La noche de Lucía |
| 6 | individuos notables | 1/5 | Un olvido feliz de Galeano, El León del desierto, Bestie, el de los laberintos invisibles, La flor de Jinotepe |
| 7 | humor e ironía | 2/6 | Córdoba, 1993, Manual Instructivo Misceláneo de Escritor Gordo (selección), La balanza de la injusticia (contrapunto de sonetos), Un paseo por el cielo |
| 8 | absurdo y exageración | 4/8 | Así funciona este mundo, La casa 314, Un paseo por el cielo, Teoría de Rasmussen |
| 9 | base histórica o mitológica | 2/5 | Héroes de Haymarket, Las trece rosas, Tu voz seguirá viviendo |
| 10 | angustia y desesperación | 5/5 | — |
| 11 | ubicación geográfica explícita o sugerida | 2/6 | Una breve carrera, Un paseo por el cielo, Héroes de Haymarket, Las trece rosas |
| 12 | juegos de palabras o doble sentido | 1/1 | — |
| 13 | referencias al deporte, real o ficticio | 4/4 | — |
| 14 | menciones de países o nacionalidades | 2/6 | Pasado, Bestie, el de los laberintos invisibles, Tu voz seguirá viviendo, La herencia del señor Skoglund |
| 15 | pérdida de ser querido o muerte en general | 5/6 | La herencia del señor Skoglund |

### Resumen (calculado desde el desglose de arriba)

- **Total encontrados:** 2 + 3 + 0 + 1 + 3 + 1 + 2 + 4 + 2 + 5 + 2 + 1 + 4 + 2 + 5 = 37 / 70
- **Recall micro** (Σ encontrados / Σ esperados): 37/70 = 52.9%
- **Recall macro** (promedio de los 15 porcentajes): 55.2%
- **Verificación:** OK — la suma del desglose (37) coincide con el micro reportado.

---
