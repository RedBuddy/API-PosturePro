## 3.1 Análisis

- Propósito

  - Permitir subir un video de un ejercicio, procesarlo con visión por computadora (MediaPipe + OpenCV) para evaluar la postura y devolver un MP4 con overlays y métricas, consumido por una SPA.

- Actores

  - Usuario final: sube el video, elige el ejercicio y visualiza resultados.
  - Backend de análisis: procesa el video, genera overlay y estadísticas.
  - Autenticación: gestiona usuarios, sesiones y recuperación (MySQL).
  - Entrenador (futuro): consulta reportes históricos compartidos.

- Alcance

  - Frontend: React + Vite + TypeScript + Tailwind + shadcn/ui.
  - Backend: Flask (API REST con Blueprints), MediaPipe/OpenCV para análisis, CORS.
  - Persistencia: MySQL (usuarios, sesiones, reset tokens). Análisis no persistidos aún (plan futuro).

- Requisitos funcionales (principales)

  - Subir video (hasta ~100MB) y seleccionar tipo de ejercicio.
  - Analizar y recibir: video procesado + estadísticas en una única respuesta (ZIP; no se persiste en el servidor).
  - Visualizar resultados: puntaje, métricas, errores y recomendaciones.
  - Autenticación básica: registro, login, sesión actual, recuperación y reseteo.

- Requisitos no funcionales

  - Compatibilidad de video web: MP4 reproducible en navegadores (mp4v por defecto; H.264 opcional).
  - Rendimiento: manejo de archivos grandes, feedback de progreso en FE.
  - Seguridad: CORS FE/BE; token Bearer; hash de contraseñas.
  - Config: URL del backend vía VITE_API_URL; DB por DATABASE_URL.

- Entradas/Salidas

  - Input: archivo de video (multipart/form-data) + exercise_type.
  - Output: cuerpo binario application/zip con:
    - analyzed_<ejercicio>_<ts>.<ext>: video procesado (mp4/avi según códec disponible)
    - stats.json: métricas del análisis (reps, score_promedio, errores, etc.)

- Supuestos
  - El navegador reproduce MP4 con códecs comunes; backend usa mp4v y puede habilitar H.264 si está disponible.
  - MediaPipe Pose requiere frames RGB; OpenCV convierte desde BGR.

## 3.2 Diseño

### 3.2.1 Arquitectura

- Vista general

  - SPA React consume API REST Flask.
  - Blueprints: /api (análisis, salud, catálogo), /api/auth (auth), /media (videos).
  - Capa de servicios: app/services/analyzer.py encapsula MediaPipe + OpenCV.
  - Persistencia: SQLAlchemy + MySQL (usuarios, sesiones, reset tokens).
  - CORS habilitado para FE/BE.

- Estructura del backend

  - run/main: crea la app y levanta el servidor.
  - app/**init**.py o app/init.py: factory, CORS, registro de blueprints, db.create_all().
  - app/routes/api.py: /api/analyze, /api/exercise-types, /api/health.
  - app/routes/auth.py: /api/auth/\* (register, login, me, forgot, reset).
  - app/routes/media.py: servir MP4 en /media/<file>.
  - app/services/analyzer.py: AnalizadorEjercicios (detección, métricas, overlay y export).
  - app/extensions.py: SQLAlchemy.
  - app/models.py: User, SessionToken, PasswordResetToken.
  - app/utils/auth.py: helpers de auth (hash, tokens, consultas).

- Estructura del frontend (relevante)

  - src/services/api.ts:
    - VideoAnalysisAPI.uploadAndAnalyze(file, exerciseType)
    - getExerciseTypes(), healthCheck()
    - AuthAPI: register/login/forgot/reset/me
  - Contexto AnalysisContext para manejar blob + stats.
  - Páginas: VideoUpload, Results, Index, NotFound.

- Configuración y entorno
  - BACKEND:
    - DATABASE_URL = mysql+pymysql://user:password@host:port/dbname
    - ENABLE_H264 = 1 (opcional; requiere DLL OpenH264 válida)
    - SECRET_KEY, MAX_CONTENT_LENGTH, MEDIA_DIR
  - FRONTEND:
    - VITE_API_URL = http://localhost:5000

### 3.2.2 Casos de uso

- UC1: Subir y analizar video

  1. Usuario selecciona archivo y tipo de ejercicio.
  2. FE hace POST /api/analyze (multipart/form-data).
  3. BE procesa y devuelve { video_path, stats }.
  4. FE hace GET a video_path, recibe MP4 y lo reproduce.

- UC2: Consultar tipos de ejercicio

  - FE hace GET /api/exercise-types y muestra catálogo.

- UC3: Health check

  - FE/DevOps hace GET /api/health para monitoreo.

- UC4: Autenticación

  - Registro: POST /api/auth/register → token + user.
  - Login: POST /api/auth/login → token + user.
  - Sesión actual: GET /api/auth/me → user (si token válido).
  - Recuperar contraseña: POST /api/auth/forgot-password → reset_token (simulado).
  - Resetear contraseña: POST /api/auth/reset-password (token + new_password).

- UC5 (futuro): Persistencia de análisis
  - Guardar resultados, errores y scores por frame para histórico y compartir.

### 3.2.3 Diagramas de secuencia

Secuencia principal: análisis de video

```mermaid
sequenceDiagram
  participant U as Usuario
  participant FE as Frontend (React)
  participant API as Backend (Flask)
  participant AN as Servicio de Análisis
  participant FS as File System (/media)

  U->>FE: Selecciona video y ejercicio
  FE->>API: POST /api/analyze (FormData: video, exercise_type) [Bearer?]
  API->>AN: procesar(video_temp_path, exercise_type)
  AN-->>API: { output_path, stats }
  API->>API: Leer output y borrar temporales
  API-->>FE: ZIP (video + stats.json)
  FE-->>U: Desempaquetar, reproducir video y mostrar métricas
```

Secuencia: autenticación

```mermaid
sequenceDiagram
  participant FE as Frontend
  participant API as Backend
  participant DB as MySQL

  FE->>API: POST /api/auth/register {email, password, name}
  API->>DB: INSERT users, INSERT sessions
  API-->>FE: {access_token, user}

  FE->>API: POST /api/auth/login {email, password}
  API->>DB: SELECT user, INSERT sessions
  API-->>FE: {access_token, user}

  FE->>API: GET /api/auth/me (Bearer)
  API->>DB: SELECT session JOIN user
  API-->>FE: user

  FE->>API: POST /api/auth/forgot-password {email}
  API->>DB: INSERT password_reset_tokens
  API-->>FE: {message, reset_token (dev)}

  FE->>API: POST /api/auth/reset-password {token, new_password}
  API->>DB: UPDATE user.password_hash, DELETE token, DELETE sessions
  API-->>FE: {message}
```

### 3.2.4 Diagrama entidad-relación (conceptual y actual)

Conceptual (incluye análisis futuro):

```mermaid
erDiagram
  User ||--o{ Analysis : has
  ExerciseType ||--o{ Analysis : categorizes
  Analysis ||--o{ ErrorDetected : records
  Analysis ||--o{ FrameScore : samples

  User {
    string id PK
    string email
    string name
  }
  ExerciseType {
    string id PK
    string name
    string description
  }
  Analysis {
    string id PK
    string user_id FK
    string exercise_type_id FK
    datetime created_at
    int reps
    float avg_score
    float duration
    string video_url
  }
  ErrorDetected {
    string id PK
    string analysis_id FK
    float timestamp
    string message
    string severity
  }
  FrameScore {
    string id PK
    string analysis_id FK
    int frame_index
    float score
  }
```

Actual (auth en MySQL):

```mermaid
erDiagram
  User ||--o{ SessionToken : has
  User ||--o{ PasswordResetToken : has

  User {
    string id PK
    string email UK
    string name
    string password_hash
    int created_at
  }

  SessionToken {
    string token PK
    string user_id FK
    int exp
  }

  PasswordResetToken {
    string token PK
    string user_id FK
    int created_at
  }
```

### 3.2.5 Algoritmos

- Detección y pose

  - MediaPipe Pose (model_complexity=2, smooth_landmarks=true).
  - Conversión BGR→RGB antes de process(); render de landmarks opcional.

- Cálculo de ángulos

  - calcular_angulo(a,b,c) vía producto punto.
  - Rodilla: cadera–rodilla–tobillo.
  - Espalda: hombro–cadera–vertical (respecto a vertical).

- Heurísticas por ejercicio

  - Sentadilla: umbrales mejorados (rodilla 80–110° óptimo), espalda <30° óptimo, simetría rodillas.
  - Peso muerto: espalda <15° óptimo, extensión de caderas al final.
  - Press banca: ángulo de codo, simetría entre brazos, trayectoria vertical muñeca-hombro.

- Conteo de repeticiones

  - Máquina de estados: preparando → bajando → preparando con umbrales de rodilla.

- Scoring y feedback

  - Penalizaciones graduales y bonificaciones por técnica óptima.
  - Registro de errores con timestamp si score < 80.

- Video y códec

  - Writer con fallback: mp4v por defecto; H.264 (avc1) opcional si ENABLE_H264=1 y DLL válida; último recurso AVI (XVID).
  - Overlay con panel (score, reps, tiempo, estado) y texto multi-línea.
  - Frame de resumen (3s) al final con agregados.

- Silenciamiento de warnings
  - Reducir verbosidad (GLOG_minloglevel/TF_CPP_MIN_LOG_LEVEL; OpenCV log level).

### 3.2.6 Interfaces

- Configuración

  - VITE_API_URL: URL del backend (default http://localhost:5000).
  - DATABASE_URL: mysql+pymysql://user:password@host:port/db
  - ENABLE_H264: 1/0 (opcional; habilita H.264 si está disponible).
  - SECRET_KEY, MAX_CONTENT_LENGTH, MEDIA_DIR.

- Endpoints Backend (REST)

  - POST /api/analyze

    - Auth: opcional (Bearer).
    - Content-Type: multipart/form-data
    - Form fields:
      - video: File (obligatorio)
      - exercise_type: 'sentadilla' | 'desplantes' | 'press_banca'
    - 200 OK: cuerpo binario `application/zip` con:
      - `analyzed_<tipo>_<ts>.<ext>` (video)
      - `stats.json` (JSON de métricas)
    - 400/500: { "message": string }

  - GET /media/<filename>

    - Obsoleto para el flujo actual sin persistencia (se conserva por compatibilidad futura).

  - GET /api/exercise-types

    - 200: [{ id, name, description }]

  - GET /api/health

    - 200: { status: "OK" }

  - Auth
    - POST /api/auth/register { email, password, name? }
      - 200: { access_token, user:{ id, email, name? } }
      - 400/409: { message }
    - POST /api/auth/login { email, password }
      - 200: { access_token, user }
      - 401: { message }
    - GET /api/auth/me (Bearer)
      - 200: user
      - 401: { message }
    - POST /api/auth/forgot-password { email }
      - 200: { message, reset_token? (solo dev) }
    - POST /api/auth/reset-password { token, new_password }
      - 200: { message }
      - 400/404: { message }

- Contratos Frontend (TypeScript)

  - VideoAnalysisAPI.uploadAndAnalyze(file, exerciseType)
    - Devuelve: { videoBlob: Blob; stats: AnalysisResult }
    - Implementación: consumir `application/zip` y desempaquetar en el navegador (p. ej. JSZip) para extraer MP4/AVI y `stats.json`.
  - getExerciseTypes(): ExerciseType[]
  - healthCheck(): boolean
  - AuthAPI: register/login/forgotPassword/resetPassword/getCurrentUser/logout/isAuthenticated

- Errores y límites

  - Tamaño máx: 100MB (MAX_CONTENT_LENGTH).
  - Mensajes consistentes en "message".
  - CORS habilitado para origen del FE.

- Seguridad
  - Contraseñas con hash (werkzeug.security).
  - Tokens Bearer almacenados en MySQL (expiración por timestamp).
  - Invalidación de sesiones al resetear contraseña.

Notas y siguientes pasos

- Persistir análisis (Analysis, ErrorDetected, FrameScore) según ER conceptual.
- Añadir cola de procesamiento (RQ/Celery) para videos largos.
- Streaming progresivo del MP4 y cabeceras de cache.
- Validación avanzada de formato/fps y sanitización de filename.
