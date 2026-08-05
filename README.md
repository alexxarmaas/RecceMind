# RecceMind

> Motor geométrico y copiloto digital para preparar borradores de notas de rally.

RecceMind analiza la geometría de una ruta, detecta curvas, estima su severidad y genera un primer borrador editable de pacenotes. La aplicación combina un backend FastAPI con un cliente Expo/React Native y permite trabajar con rutas de Google, archivos GPX, coordenadas GPS y telemetría CSV.

> [!WARNING]
> RecceMind es una herramienta experimental de apoyo. Sus notas, perfiles de velocidad y clasificaciones no deben utilizarse como única referencia para circular o competir. Todo resultado debe validarse mediante reconocimiento presencial por un equipo cualificado y conforme a la normativa aplicable.

## Estado

El proyecto se encuentra en fase MVP. La base funcional incluye:

- Generación de rutas mediante Google Routes API.
- Análisis geométrico de curvas y distancias.
- Clasificación configurable de curvas del 1 al 6.
- Importación GPX y detección experimental de rasantes.
- Importación de telemetría CSV.
- Editor de pacenotes y feedback por piloto.
- Exportación PDF/CSV y reproducción por voz.
- Grabación GPS desde la aplicación.

Las funciones de aprendizaje, rasantes, telemetría y velocidad teórica deben considerarse experimentales hasta disponer de un conjunto de validación con tramos reales etiquetados.

## Arquitectura

```text
frontend (Expo / React Native)
        |
        | HTTP/JSON
        v
backend (FastAPI)
        |
        +-- Google Routes API
        +-- Motor geométrico
        +-- Generador de pacenotes
        +-- SQLite / SQLAlchemy
        +-- Clasificador personalizado
```

## Requisitos

- Python 3.13
- Node.js 22
- Expo SDK 54
- FFmpeg, necesario para convertir el audio antes de la transcripción
- Una clave de Google Maps/Routes correctamente restringida

## Inicio rápido

### Backend

```bash
cd backend
python -m venv .venv

# Linux/macOS
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1

pip install -r requirements-dev.txt
cp .env.example .env
alembic upgrade head
uvicorn main:app --reload
```

Configura `GOOGLE_MAPS_API_KEY` dentro de `backend/.env`. La documentación de la API estará disponible en `http://127.0.0.1:8000/docs` y el health check en `http://127.0.0.1:8000/api/health`.

### Frontend

```bash
cd frontend
npm ci
cp .env.example .env
npm start
```

Para un teléfono físico, `EXPO_PUBLIC_API_URL` debe apuntar a una dirección accesible desde el dispositivo, por ejemplo:

```env
EXPO_PUBLIC_API_URL=http://192.168.1.50:8000/api
```

## Seguridad de las claves

La clave utilizada por el backend no debe enviarse al cliente. La clave del frontend será visible en la aplicación compilada, por lo que debe ser una clave independiente y estar restringida por:

- API habilitada.
- Dominio web autorizado.
- Package name y certificado de Android.
- Bundle identifier de iOS.
- Cuotas y alertas de consumo.

Una clave que haya sido publicada sin restricciones debe rotarse desde Google Cloud. Eliminarla del último commit no la borra del historial Git.

## Telemetría CSV

El formato mínimo es:

```csv
lat,lon,speed,brake,gear
28.1000,-15.4000,30.5,0.0,4
28.1001,-15.4002,27.0,0.7,3
```

`speed`, `brake` y `gear` son opcionales; `lat` y `lon` son obligatorios.

## Calidad y pruebas

```bash
cd backend
ruff check .
pytest

cd ../frontend
npm run typecheck
```

GitHub Actions ejecuta las validaciones del backend y del frontend en cada pull request.

## Roadmap técnico

1. Construir un dataset de tramos reales con notas verificadas.
2. Medir precisión de detección, dirección, distancia y clasificación.
3. Remuestrear las rutas a una separación métrica uniforme sin perder la correspondencia con el mapa.
4. Separar `MapScreen` en componentes y hooks especializados.
5. Persistir y versionar modelos personalizados por piloto.
6. Añadir autenticación antes de almacenar perfiles o datos de usuarios reales.

## Licencia

MIT. Consulta [LICENSE](LICENSE).
