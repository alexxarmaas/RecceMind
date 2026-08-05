# 🏁 RecceMind

> **The AI Copilot for Rally Reconnaissance**
>
> *Convierte carreteras en un primer borrador de notas de rally.*

---

## ¿Qué es RecceMind?

**RecceMind** es una plataforma diseñada para asistir a pilotos y copilotos durante la fase de reconocimiento de un tramo de rally.

El objetivo del proyecto es desarrollar un sistema capaz de analizar automáticamente la geometría de una carretera y generar un **primer borrador de pacenotes**, reduciendo significativamente el tiempo necesario para preparar un rally.

A diferencia de otros sistemas, **RecceMind no pretende sustituir al copiloto**, sino convertirse en una herramienta inteligente que automatice el trabajo repetitivo y permita que el equipo se centre en ajustar y personalizar las notas.

---

# Visión del proyecto

Actualmente, la creación de notas de rally es un proceso completamente manual.

El piloto y el copiloto recorren el tramo, interpretan cada curva y generan las notas que posteriormente utilizarán en competición.

RecceMind propone un enfoque diferente:

```
Carretera
        │
        ▼
 Análisis geométrico
        │
        ▼
 Generación automática
        │
        ▼
 Edición por piloto/copiloto
        │
        ▼
 Aprendizaje del sistema
```

La filosofía del proyecto consiste en que la tecnología realice el trabajo repetitivo mientras que la experiencia del piloto aporte el criterio final.

---

# Estado del proyecto

🚧 **Actualmente en fase MVP**

La primera versión del proyecto estará completamente basada en geometría.

**No utilizará Inteligencia Artificial.**

El objetivo inicial consiste en demostrar que es posible convertir el trazado de una carretera en un conjunto coherente de notas de rally utilizando únicamente información cartográfica.

Una vez validado este motor, se incorporarán progresivamente técnicas de Inteligencia Artificial y aprendizaje automático.

---

# Objetivos del MVP

La primera versión será capaz de:

* Seleccionar un tramo desde un mapa.
* Obtener la geometría de la carretera mediante Google Maps.
* Analizar automáticamente el recorrido.
* Detectar curvas y rectas.
* Calcular radios aproximados.
* Estimar la dificultad de cada curva.
* Calcular distancias entre elementos.
* Generar un primer borrador de pacenotes.

Ejemplo:

```
Salida

120

Derecha 4 larga

50

Izquierda 3

80

Derecha 5

40

Horquilla izquierda
```

Estas notas serán siempre un **borrador**, pensado para ser revisado y adaptado por el piloto o copiloto.

---

# Filosofía del proyecto

RecceMind no es un modelo de IA.

RecceMind es un **motor de análisis de carreteras**.

La Inteligencia Artificial llegará en fases posteriores para:

* Aprender el estilo de cada piloto.
* Ajustar automáticamente la escala de notas.
* Detectar patrones de corrección.
* Mejorar la generación de pacenotes con el uso continuado.

---

# Arquitectura prevista

```
                    Google Maps
                         │
                         ▼
                 Motor Geométrico
                         │
                         ▼
              Modelo interno del tramo
                         │
                         ▼
             Generador de Pacenotes
                         │
                         ▼
                Editor Inteligente
                         │
                         ▼
               IA de aprendizaje (v2)
```

La IA será un componente adicional, nunca el núcleo del sistema.

---

# Tecnologías

## Backend

* Python
* FastAPI

## Frontend

* React Native (Expo)

## Geometría

* NumPy
* SciPy
* Shapely

## Base de datos

* SQLite

## Servicios

* Google Maps Routes API
* Google Roads API
* Google Elevation API *(futuro)*

---

# Roadmap

## MVP

El MVP se desarrollará en 6 fases:

* **Fase 1:** Interfaz de usuario para seleccionar origen/destino o dibujar ruta.
* **Fase 2:** Consumo de Google Routes API (obtención de polyline, distancia, duración).
* **Fase 3:** Motor Geométrico (`geometry_engine.py`) para detectar curvas, agrupar segmentos y calcular radios y cambios de dirección.
* **Fase 4:** Motor de Clasificación (`classification_engine.py`) para clasificar curvas mediante radios (ej. >150m → 6).
* **Fase 5:** Generador de Pacenotes (`pacenote_generator.py`) para traducir las curvas a texto.
* **Fase 6:** Visualización interactiva en el mapa, mostrando notas generadas y parámetros geométricos al seleccionar cada curva.

---

## Versión 2

* [x] Editor avanzado
* [x] Importación GPX
* [x] Exportación de notas
* [x] Street View
* [x] Perfiles por piloto

---

## Versión 3

* [x] Aprendizaje automático
* [x] Reconocimiento por voz
* [x] Grabación de reconocimientos
* [x] Integración con GPS
* [x] Ajuste automático de notas

---

## Versión 4

* [ ] IA personalizada por piloto
* [ ] Detección de rasantes
* [ ] Detección de "se abre" / "se cierra"
* [ ] Simulación del tramo
* [ ] Análisis de telemetría

---

# Objetivo a largo plazo

Crear la primera plataforma capaz de generar, aprender y perfeccionar notas de rally de forma inteligente, convirtiéndose en una herramienta de apoyo para pilotos y copilotos durante los reconocimientos.

El objetivo no es reemplazar la experiencia humana, sino potenciarla mediante un motor geométrico sólido y, posteriormente, modelos de Inteligencia Artificial entrenados a partir de las correcciones y preferencias de cada equipo.
