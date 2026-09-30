# Evaluación de modelos VT7: UDef-ARP 2.11 vs TerraCover

**Alcance:** el *proceso de evaluación* del VT7 (VT0007 §5.4) — la comparación entre deforestación predicha y observada sobre una malla de polígonos de Thiessen, y las métricas que de ahí salen (R², OLS, Theil-Sen, MedAE). No cubre el resto del código (asignación, mapas de vulnerabilidad, razón de ajuste).

**Las dos versiones comparadas:**

| Etiqueta | Ruta | Archivo del proceso |
|---|---|---|
| **v2.11** | `verra_code/UDef-ARP-main 2.11/` | `model_evaluation.py` + pantallas `MCT_*` de `UDef-ARP.py` |
| **TerraCover** | `standalone/vt7_udef_arp/` | `terracover/modules/vt7/evaluation.py` |

v2.11 es la versión vigente publicada por Verra y es la única línea base considerada aquí. Las versiones anteriores de UDef-ARP quedan fuera del documento.

**Método:** todo lo afirmado aquí se verificó leyendo el código; los comandos de verificación están en el Apéndice B. Cuando un dato proviene de una corrida y no de una lectura de código, se dice explícitamente.

---

## Resumen ejecutivo

1. TerraCover conserva el **núcleo metodológico** de v2.11: malla sistemática, teselación de Voronoi, filtro de borde al 99,9 %, estadística zonal, y las mismas métricas (R², OLS, Theil-Sen, MedAE).
2. El cambio de fondo es el sistema de **doble máscara**: teselar contra la jurisdicción continua y aplicar las exclusiones **después** del filtro de borde. Resuelve un defecto real de v2.11 (§3.1).
3. El segundo cambio es la **automatización completa**: v2.11 depende de que un operador escoja los archivos correctos en un formulario; TerraCover los deriva del FCBM y de la estructura de carpetas (§3.2).
4. **Cinco cambios alteran las cifras reportadas** (MedAE, R², nº de muestras). Están en la §4 y ninguno es cosmético.
5. **Dos de ellos son decisiones metodológicas, no correcciones**, y siguen abiertas: el filtro de celdas vacías antes de la regresión y el denominador del `MedAE%`. Ver §5.
6. TerraCover **dejó de emitir** el ráster de residuales y el mapa combinado de revisión de deforestación. Ver §7.

---

## 1. La secuencia, común a las dos versiones

Ambas hacen, en el fondo, lo mismo:

1. **Poligonizar la máscara** de la jurisdicción (`gdal.Polygonize`).
2. **Muestreo sistemático:** rejilla regular de puntos con lado `grid_size = int(√(area·10.000)) // tamaño_píxel`, desbordando el ráster una celda por cada lado.
3. **Teselación de Voronoi** sobre esos puntos (`scipy.spatial.Voronoi`); se poligonizan solo las aristas finitas. Con puntos en rejilla, las celdas resultantes son cuadrados.
4. **Filtro de borde:** intersectar con la máscara y quedarse con las celdas cuya área supere el **99,9 % del área de la celda mayor** (`remove_edge_cells`, umbral 0.999).
5. **Estadística zonal:** suma de píxeles deforestados × resolución areal → `Actual Deforestation(ha)`; suma del mapa de densidad → `Predicted Deforestation(ha)` (la densidad ya viene en ha, no se multiplica).
6. **Residuales** = predicha − actual, y exportación tabular + geométrica.
7. **Gráfico y métricas:** dispersión, recta OLS, recta Theil-Sen, línea 1:1, R² = `corrcoef²`, `MedAE = mediana(|X−Y|)`, `MedAE% = MedAE / grid_area · 100`.

Lo que cambia es *cómo* se ejecuta cada paso, quién decide las entradas y qué se hace con las exclusiones.

---

## 2. Tabla comparativa

| Aspecto | v2.11 | TerraCover |
|---|---|---|
| **Disparo** | Manual, GUI (`MCT_FIT_CAL`, `MCT_PRE_CNF`) | Automático desde el pipeline, BCM y ALT × CAL y CNF |
| **Mapas de deforestación** | Los prepara el usuario | Derivados del FCBM al vuelo: clases 6 y 7 → CAL, clase 8 → CNF |
| **Rutas y nombres** | Los teclea el usuario | Derivados de la estructura de carpetas VT7 |
| **Máscara(s)** | Una | **Dos**: teselado sin exclusiones + estadística con exclusiones |
| **Momento de las exclusiones** | Antes del filtro 0.999 | **Después** del filtro, con disolución de fragmentos |
| **Identidad de la celda** | Ninguna; cada fragmento es una fila | `_voronoi_id` preservado y fragmentos disueltos |
| **`remove_edge_cells`** | Sin endurecer | `keep_geom_type=False` + filtro de tipo de geometría |
| **Tamaño de píxel** | `int(gt[1])` (trunca) | Float real + **rechaza CRS en grados** |
| **`zonal_stats`: nodata** | Solo el valor pasado (0) | También el **nodata nativo** del ráster |
| **`zonal_stats`: SRS** | Capa en memoria sin SRS | SRS heredado de la capa vectorial |
| **Precisión de la regresión** | `float32` | `float64` |
| **Celdas que entran a la regresión** | Todas | Solo con Actual o Pred **> 0,01 ha** |
| **Trazado de las rectas** | Sobre `0…xmax` (`X_extended`) | Sobre el rango de los datos |
| **Casos degenerados (0 o <2 celdas)** | Traceback | PNG con mensaje y continúa |
| **Salida tabular** | CSV | **XLSX** formateado + `_statistics.txt` |
| **Residuales** | **Ráster** del atributo `Residuals` | **Shapefile** (sin ráster) |
| **Mapa combinado de revisión** | Sí, en CNF | Método portado pero **sin llamador** |
| **Progreso / cancelación** | Señales Qt a barra de progreso | Log por consola + `cancel_flag` |
| **Soporte `.rst` (Idrisi)** | Sí, y `.tif` en `replace_ref_system` | Vestigial (el pipeline es GeoTIFF) |
| **Bug `fmask == 1`** | Presente (`model_evaluation.py:477`) | Corregido (`arr_fmask`) |

---

## 3. Los cambios de TerraCover

### 3.1 Sistema de doble máscara (el cambio de fondo)

**El problema en v2.11:** hay una sola máscara y las exclusiones ya vienen aplicadas en ella. La máscara llega agujereada a la teselación, y el filtro de borde compara cada celda contra **el área de la celda mayor del propio conjunto**, no contra el área nominal. Consecuencia: el conteo de muestras depende del patrón de exclusiones de una forma difícil de anticipar.

- Si las exclusiones son dispersas y alguna celda queda intacta, el máximo es una celda completa y **toda celda tocada por una exclusión se descarta**.
- Si las exclusiones son omnipresentes y ninguna celda queda intacta, el máximo baja, el umbral absoluto baja con él y **pasan más celdas**, incluidas algunas bastante recortadas.

En ninguno de los dos regímenes la muestra representa lo que la metodología pretende: una malla sistemática de celdas de área conocida. Además, como en v2.11 cada intersección con un fragmento distinto de la máscara produce una fila propia, una misma celda partida en islas puede contarse varias veces o desaparecer entera.

**La solución en TerraCover** (`evaluation.py:274`):

1. `create_voronoi_mask` construye una máscara binaria de la jurisdicción **completa, sin exclusiones** (`evaluation.py:817`).
2. La teselación de Voronoi **y** el filtro 0.999 se aplican contra esa máscara continua → el umbral se calcula sobre el área verdadera de la celda y solo se descartan celdas de borde reales.
3. Cada celda superviviente recibe un `_voronoi_id` (`evaluation.py:375`).
4. **Después**, se intersecta con la máscara **con exclusiones**; los fragmentos (islas) que la exclusión genera se vuelven a unir con `dissolve(by='_voronoi_id')` (`evaluation.py:402`), de modo que una celda recortada sigue contando como **una** muestra.
5. `Area_ha` se recalcula ya con las exclusiones descontadas.

Resultado: la estructura de la malla la decide la geometría de la jurisdicción, y las exclusiones afectan solo a las cifras dentro de cada celda.

### 3.2 Automatización del flujo

`evaluate_testing_stage()` (`evaluation.py:944`) sustituye al operador humano:

- Localiza los mapas de densidad por convención de nombres (`07_BCM_Fitting_Density_Map_CAL.tif`, `04_BCM_Adjusted_Prediction_Density_Map_CNF.tif`, o los equivalentes `ALT`).
- **Genera los mapas de deforestación desde el FCBM** en un directorio temporal: primero enmascara el FCBM a la jurisdicción con exclusiones, luego `clases 6 y 7 → T1T2` (CAL) y `clase 8 → T2T3` (CNF) (`evaluation.py:1033` y `:1043`).
- Corre las cuatro combinaciones (BCM/ALT × CAL/CNF) según las banderas del pipeline, con `cancel_flag` para abortar y log por consola.

Esto elimina toda una clase de error de operación que en v2.11 depende enteramente del cuidado del usuario: mapas de deforestación mal recortados, densidad de la fase equivocada, máscara sin exclusiones donde debía llevarlas.

### 3.3 Correcciones técnicas

| Corrección | Dónde | Por qué importa |
|---|---|---|
| Tamaño de píxel en float y rechazo de CRS en grados | `evaluation.py:318` | Con un ráster de 29,97 m, `int()` daba 29 y la celda salía ≈6,7 % más grande que la nominal |
| Nodata nativo del ráster en `zonal_stats` | `evaluation.py:151` | v2.11 solo excluye el valor que se le pasa (0); si el ráster trae su propio nodata (−1, 255), lo **suma** |
| SRS en la capa en memoria de `zonal_stats` | `evaluation.py` (`zonal_stats`) | Evita ambigüedad al rasterizar cada polígono |
| `keep_geom_type=False` + filtro de tipo en `remove_edge_cells` | `evaluation.py:248` | Las intersecciones pueden producir líneas y puntos degenerados que no son celdas |
| Manejo de casos degenerados | `evaluation.py:274` y `:561` | Con 0 o <2 celdas, v2.11 lanza un traceback; TerraCover emite un PNG explicativo y sigue |
| `float32` → `float64` en la regresión | `evaluation.py` (`create_plot`) | v2.11 arma `X`/`Y` en `float32`; con sumas de decenas de miles de hectáreas se pierde precisión en el último dígito |
| `arr_fmask` en vez de `fmask` | `evaluation.py:535` | En v2.11, `create_deforestation_map` compara `fmask == 1` donde `fmask` es la **ruta del archivo**, no el array (`model_evaluation.py:477`). En la práctica es inocuo — el array de salida ya se inicializa como copia de la máscara de bosque — pero está mal escrito |
| Cierre explícito de datasets GDAL y `tempfile` | varios | Evita bloqueos de archivo en Windows y colisiones con archivos previos del directorio |

---

## 4. Los cinco cambios que alteran las cifras

Estos son los que hay que tener a mano al comparar un MedAE de TerraCover con uno de v2.11. **No son comparables sin más.**

| # | Cambio | Efecto sobre las métricas |
|---|---|---|
| 1 | **Filtro `> 0,01 ha` antes de la regresión** (`evaluation.py:578-579`) | Quita las celdas sin deforestación observada **ni** predicha. Como el MedAE es una mediana y ese bloque de ceros suele ser el más numeroso, quitarlo **sube el MedAE** y normalmente también el R². Cambia además el `Samples` que aparece en el gráfico. |
| 2 | **Momento de las exclusiones** (§3.1) | Cambia qué celdas entran y cuánta área tiene cada una. La dirección del cambio en el nº de muestras **depende de los datos** (ver §5.3). |
| 3 | **Tamaño de píxel en float** | Cambia el lado real de la celda y, por tanto, todas las sumas zonales y el denominador del `MedAE%`. |
| 4 | **Nodata nativo en `zonal_stats`** | Cambia directamente `ActualDef` y `PredDef` si los rásteres declaran nodata. |
| 5 | **`float32` → `float64`** | Efecto pequeño, en el último dígito significativo. |

---

## 5. Decisiones metodológicas abiertas

Se listan aparte porque **no son correcciones técnicas**: son criterios que alguien eligió y que VT0007 no fija. Conviene resolverlas o documentarlas antes de que las cifras lleguen a un VVB.

### 5.1 El filtro de celdas vacías (`> 0,01 ha`)

No tiene base en VT0007 §5.4 y no existe en v2.11. El argumento a favor es que una malla con muchas celdas sin deforestación en ninguna de las dos fuentes infla artificialmente el ajuste y hunde el MedAE hasta cero; el argumento en contra es que esas celdas son observaciones legítimas de la malla sistemática y que el criterio de calificación del modelo se define sobre el MedAE de todas ellas.

**Estado:** implementado, sin decisión documentada. Opciones: (a) retirarlo y reportar el MedAE sobre la malla completa, (b) conservarlo y declararlo explícitamente en el reporte, (c) reportar ambos.

### 5.2 El denominador del `MedAE%`

`MedAE% = MedAE / grid_area · 100` usa el área **nominal** de la celda, igual que en v2.11. Pero en v2.11 ese denominador era razonable porque toda celda superviviente era prácticamente completa. En TerraCover, las celdas recortadas por exclusiones tienen área real menor que la nominal, así que el porcentaje **queda subestimado** en proporción al recorte.

**Estado:** sin resolver. Opciones: (a) dividir por el `Area_ha` de cada celda, (b) mantener el área nominal y documentarlo, (c) reportar el MedAE en hectáreas y omitir el porcentaje.

### 5.3 El conteo de muestras

El documento `VT7_Evaluation_Improvements.md` reporta una medición de **~92 muestras en UDef-ARP contra ~60 en TerraCover** con una malla de 50.000 ha, y la atribuye al efecto de umbral relativo descrito en §3.1. Ese número proviene de una corrida concreta y **no se reprodujo en este documento**; el mecanismo sí está verificado en el código, pero la dirección del cambio depende del patrón de exclusiones del área concreta.

**Recomendación:** al reportar, incluir el nº de muestras junto al MedAE, y no interpretar un cambio de conteo entre versiones como un error sin mirar antes la geometría de las exclusiones.

---

## 6. Salidas por versión

| Salida | v2.11 | TerraCover |
|---|---|---|
| Gráfico de dispersión (PNG) | ✔ | ✔ |
| Tabla de la malla | CSV | XLSX formateado |
| Estadísticas en texto | ✘ | ✔ (`_statistics.txt`) |
| Shapefile de la malla | ✔ | ✔ (`ID, Area_ha, ActualDef, PredDef, Residuals`) |
| **Ráster de residuales** | ✔ | ✘ |
| **Mapa combinado de revisión** | ✔ (CNF) | ✘ |

---

## 7. Lo que TerraCover dejó de producir

1. **El ráster de residuales.** `vector_to_raster` se importa en `evaluation.py` pero nunca se llama; el parámetro `raster_fn` se reutiliza cambiándole la extensión a `.shp` (`evaluation.py:514`). La información está en el shapefile, pero no como ráster.
2. **El mapa combinado de revisión de deforestación** (1 = bosque al inicio del HRP, 2 = deforestación en CAL, 3 = en CNF). El método `create_deforestation_map` está portado y corregido (`evaluation.py:535`), pero ningún llamador lo usa.
3. **El soporte Idrisi `.rst`** queda vestigial: `replace_legend` y `replace_ref_system` siguen ahí, pero el pipeline trabaja en GeoTIFF.

Los tres son recuperables con poco trabajo si el entregable al VVB los requiere.

---

## Apéndice A · Nota sobre `VT7_Evaluation_Improvements.md`

Ese documento describe correctamente el sistema de doble máscara, pero **su línea base no es v2.11**: su "Detailed Code Comparison" rotula los fragmentos como "UDef-ARP Implementation" citando líneas de una versión anterior de UDef-ARP. Los rasgos que ahí se atribuyen a UDef-ARP —selección del polígono más grande, `unary_union` antes de filtrar— **no existen en v2.11**. Solo su apéndice "Status in UDef-ARP v2.11" trata la versión vigente.

Además cita código de TerraCover ya superado (`pixel_size = int(...)`, hoy `pixel_size_meters()` en float) y no cubre el filtro `> 0,01 ha`, el nodata nativo, el cambio `float32`/`float64`, el denominador del `MedAE%` ni la pérdida del ráster de residuales.

Para una comparación contra la versión vigente de Verra, este documento es el que aplica.

---

## Apéndice B · Cómo reproducir las verificaciones

```bash
cd "VT7_Verra"

# Estructura del proceso en cada versión
grep -n "def " "verra_code/UDef-ARP-main 2.11/model_evaluation.py"
grep -n "def " "standalone/vt7_udef_arp/terracover/modules/vt7/evaluation.py"

# Firma de create_thiessen_polygon: una máscara vs dos
grep -n "def create_thiessen_polygon" \
     "verra_code/UDef-ARP-main 2.11/model_evaluation.py" \
     "standalone/vt7_udef_arp/terracover/modules/vt7/evaluation.py"

# Los cambios que mueven las cifras
grep -n "dtype=np.float" "verra_code/UDef-ARP-main 2.11/model_evaluation.py"
grep -n "threshold = 0.01\|valid_mask = \|native_nodata = \|pixel_size = pixel_size_meters" \
     "standalone/vt7_udef_arp/terracover/modules/vt7/evaluation.py"

# Quién llama a la evaluación en TerraCover (y qué quedó sin llamador)
grep -rnE "evaluate_testing_stage|create_deforestation_map|vector_to_raster" \
     --include=*.py standalone/vt7_udef_arp/terracover/ | grep -v __pycache__
```

---

*Versión del documento: 1.0 · 2026-08-26 · Terra Global Capital*
