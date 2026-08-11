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
- Backend preparado para despliegue en contenedor y consumo desde la consola administrativa de Tramassso.

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

tramassso.com/reccemind (Next.js, admin)
        |
        | proxy server-side + service token
        v
backend (FastAPI)
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

## Despliegue cloud del backend

`backend/Dockerfile` incluye Python 3.13, las dependencias del proyecto y FFmpeg. Puede utilizarse en Railway, Render, Fly.io, un VPS o cualquier plataforma capaz de ejecutar contenedores.

Ejemplo local:

```bash
cd backend
docker build -t reccemind-api .
docker run --rm -p 8000:8000 --env-file .env reccemind-api
```

Para un despliegue persistente usa preferiblemente PostgreSQL y migraciones Alembic:

```env
GOOGLE_MAPS_API_KEY=...
DATABASE_URL=postgresql://...
AUTO_CREATE_DB=false
RECCEMIND_SERVICE_TOKEN=un-secreto-largo-y-aleatorio
```

Cuando `RECCEMIND_SERVICE_TOKEN` tiene valor, todas las rutas bajo `/api/*` exigen la cabecera:

```text
X-RecceMind-Token: <secreto>
```

En desarrollo local puedes dejar la variable vacía. El token está pensado para comunicación servidor-a-servidor, por ejemplo desde el proxy de `tramassso.com/reccemind`; no debe compilarse dentro de Expo ni enviarse al navegador.

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
7. Evolucionar las pacenotes a un contrato estructurado y añadir modo reconocimiento/copiloto offline.

## Licencia

MIT. Consulta [LICENSE](LICENSE).
