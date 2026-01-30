# PosturePro - API de Análisis de Postura en Ejercicios

**Autor**: Orlando Armando Apodaca Concha

## 📋 Descripción General

**PosturePro** es una aplicación web moderna que utiliza visión por computadora (MediaPipe y OpenCV) para analizar videos de ejercicios y evaluar la postura del usuario. La plataforma proporciona retroalimentación detallada, métricas de rendimiento y recomendaciones para mejorar la técnica de ejercicio.

La arquitectura consiste en:

- **Backend**: API REST construida con Flask que procesa videos y realiza análisis de pose
- **Frontend**: Aplicación web moderna construida con React, Vite y TypeScript
- **Base de Datos**: MySQL para gestión de usuarios, sesiones y autenticación

## 🎯 Características Principales

### Análisis de Ejercicios

- **Detección de Pose**: Utiliza MediaPipe Pose para detectar 33 puntos clave del cuerpo
- **Ejercicios Soportados**:
  - Sentadilla (Squat)
  - Desplantes (Lunges)
  - Press de Banca (Bench Press)
- **Video Procesado**: Genera videos MP4 con overlay de esqueleto y puntos articulares
- **Métricas Detalladas**: Análisis de repeticiones, ángulos articulares y errores comunes

### Autenticación y Seguridad

- Registro e inicio de sesión de usuarios
- Recuperación de contraseña con envío de emails
- Tokens JWT para sesiones seguras
- Contraseñas hasheadas con criptografía

### Interfaz de Usuario

- Carga intuitiva de videos
- Visualización de resultados en tiempo real
- Interfaz responsiva con Tailwind CSS y shadcn/ui
- Feedback de progreso de análisis

## 🛠️ Stack Tecnológico

### Backend

```
Flask               - Framework web
Flask-CORS          - Manejo de CORS
Flask-SQLAlchemy    - ORM para base de datos
MediaPipe           - Detección de pose y landmarks
OpenCV              - Procesamiento de video
NumPy               - Computación numérica
Werkzeug            - Utilidades para desarrollo web
python-dotenv       - Gestión de variables de entorno
gunicorn            - Servidor WSGI para producción
```

### Frontend

```
React               - Librería de interfaz
Vite                - Bundler y dev server
TypeScript          - Tipado estático
Tailwind CSS        - Framework de estilos
shadcn/ui          - Componentes de UI reutilizables
```

### Base de Datos

```
MySQL               - RDBMS
psycopg            - Adaptador de conexión
SQLAlchemy         - ORM
```

## 📦 Requisitos Previos

- **Python**: 3.12.5 o superior
- **Node.js**: 18 o superior (para desarrollo frontend)
- **MySQL**: 8.0 o superior
- **Docker y Docker Compose** (opcional, para containerización)
- **FFmpeg**: Para procesamiento de video
- Mínimo 100 MB de espacio disco libre para almacenamiento temporal

## 🚀 Instalación y Configuración

### 1. Clonar el Repositorio

```bash
git clone <repository-url>
cd API-PosturePro
```

### 2. Configurar Variables de Entorno

Crear archivo `.env` en la raíz del proyecto:

```env
# Base de Datos
DATABASE_URL=mysql+pymysql://usuario:contraseña@localhost:3306/posturepro

# Seguridad
SECRET_KEY=tu-clave-secreta-muy-segura

# CORS y Frontend
FRONTEND_URL=http://localhost:5173

# Email (para recuperación de contraseña)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASSWORD=tu-contraseña-app

# Video
MAX_CONTENT_LENGTH=104857600  # 100MB
ANALYSIS_CACHE_TTL=600        # 10 minutos

# Optional - H264 codec support
# ENABLE_H264=1
```

### 3. Instalación Local

#### Backend

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual (Windows)
venv\Scripts\activate

# Activar entorno virtual (macOS/Linux)
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

#### Frontend

```bash
# Navegar a directorio frontend
cd frontend

# Instalar dependencias
npm install

# Configurar .env.local
# VITE_API_URL=http://localhost:5000
```

### 4. Preparar la Base de Datos

```bash
# Crear base de datos
mysql -u root -p
> CREATE DATABASE posturepro;
> EXIT;

# Las tablas se crearán automáticamente al iniciar la aplicación
```

### 5. Iniciar la Aplicación

#### Backend

```bash
# Desde la raíz del proyecto
python main.py
```

El servidor estará disponible en `http://localhost:5000`

#### Frontend (en otra terminal)

```bash
cd frontend
npm run dev
```

La aplicación estará disponible en `http://localhost:5173`

## 🐳 Uso con Docker

### Construcción de Imagen

```bash
docker build -t posturepro:latest .
```

### Ejecución con Docker Compose

```bash
# Crear archivo .env con las variables necesarias

# Iniciar servicios
docker-compose up -d

# Ver logs
docker-compose logs -f api

# Detener servicios
docker-compose down
```

## 📚 Estructura del Proyecto

```
API-PosturePro/
├── main.py                 # Punto de entrada de la aplicación
├── requirements.txt        # Dependencias de Python
├── Dockerfile             # Configuración para Docker
├── docker-compose.yml     # Orquestación de contenedores
├── render.yaml            # Configuración para Render (deployment)
├── app/
│   ├── __init__.py        # Factory de aplicación Flask
│   ├── config.py          # Configuración de la aplicación
│   ├── extensions.py      # Extensiones (SQLAlchemy, etc.)
│   ├── models.py          # Modelos de base de datos
│   ├── routes/
│   │   ├── api.py         # Endpoints de análisis (/api/analyze, etc.)
│   │   ├── auth.py        # Endpoints de autenticación
│   │   └── media.py       # Servicio de archivos multimedia
│   ├── services/
│   │   └── analyzer.py    # Lógica de análisis con MediaPipe/OpenCV
│   └── utils/
│       ├── auth.py        # Funciones auxiliares de autenticación
│       └── mailer.py      # Servicio de envío de emails
└── docs/
    ├── arquitectura-front-back.md    # Documentación de arquitectura
    └── pesudocodigos.md              # Pseudocódigos de referencias
```

## 🔌 API REST - Endpoints Principales

### Análisis

#### Analizar Video

```
POST /api/analyze
Content-Type: multipart/form-data

Parámetros:
  - video: archivo de video (MP4, AVI)
  - exercise_type: tipo de ejercicio ['sentadilla', 'desplantes', 'press_banca']

Respuesta:
  - video_path: URL del video procesado
  - stats: objeto con métricas de análisis
  - message: mensaje de estado
```

#### Obtener Progreso

```
GET /api/progress

Respuesta:
  { "progress": 75 }  # Porcentaje (0-100)
```

#### Tipos de Ejercicio

```
GET /api/exercise-types

Respuesta:
  [
    { "id": "sentadilla", "name": "Sentadilla", "description": "..." },
    { "id": "desplantes", "name": "Desplantes", "description": "..." },
    { "id": "press_banca", "name": "Press de Banca", "description": "..." }
  ]
```

#### Health Check

```
GET /api/health

Respuesta:
  { "status": "ok", "timestamp": "2024-01-29T10:30:00Z" }
```

### Autenticación

#### Registro

```
POST /api/auth/register
Content-Type: application/json

Body:
  {
    "email": "usuario@example.com",
    "password": "miPassword123",
    "name": "Juan Pérez"
  }

Respuesta:
  {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "user": {
      "id": "uuid",
      "email": "usuario@example.com",
      "name": "Juan Pérez"
    }
  }
```

#### Inicio de Sesión

```
POST /api/auth/login
Content-Type: application/json

Body:
  {
    "email": "usuario@example.com",
    "password": "miPassword123"
  }

Respuesta:
  {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "user": { ... }
  }
```

#### Usuario Actual

```
GET /api/auth/me
Authorization: Bearer <token>

Respuesta:
  {
    "id": "uuid",
    "email": "usuario@example.com",
    "name": "Juan Pérez"
  }
```

#### Recuperar Contraseña

```
POST /api/auth/forgot-password
Content-Type: application/json

Body:
  { "email": "usuario@example.com" }

Respuesta:
  { "message": "Se envió enlace de recuperación al email" }
```

#### Resetear Contraseña

```
POST /api/auth/reset-password
Content-Type: application/json

Body:
  {
    "token": "token-de-recuperacion",
    "new_password": "nuevaPassword123"
  }

Respuesta:
  { "message": "Contraseña actualizada exitosamente" }
```

## 📊 Modelo de Base de Datos

### Tablas

**users**

```sql
CREATE TABLE users (
  id VARCHAR(36) PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  name VARCHAR(100),
  password_hash VARCHAR(255) NOT NULL,
  created_at INT NOT NULL,
  INDEX(email)
);
```

**sessions** (SessionToken)

```sql
CREATE TABLE sessions (
  token VARCHAR(255) PRIMARY KEY,
  user_id VARCHAR(36) NOT NULL,
  exp INT NOT NULL,
  FOREIGN KEY(user_id) REFERENCES users(id),
  INDEX(user_id)
);
```

**password_reset_tokens** (PasswordResetToken)

```sql
CREATE TABLE password_reset_tokens (
  token VARCHAR(255) PRIMARY KEY,
  user_id VARCHAR(36) NOT NULL,
  created_at INT NOT NULL,
  FOREIGN KEY(user_id) REFERENCES users(id),
  INDEX(user_id)
);
```

## 🔍 Detalles Técnicos

### Análisis de Pose con MediaPipe

- **Modelo**: MediaPipe Pose (33 landmarks corporales)
- **Confianza Mínima**: 50% para detección y seguimiento
- **Suavizado**: Habilitado para mayor estabilidad en videos
- **Complejidad**: 2 (máxima precisión)

### Procesamiento de Video

- **Formato de Salida**: MP4 (códec mp4v, fallback a H.264 u AVI)
- **Resolución**: Mantiene resolución original del video de entrada
- **Overlay**: Esqueleto de pose con ángulos articulares
- **Compresión**: Gunicorn gestiona múltiples procesos thread-based

### Almacenamiento Temporal

- **Ubicación**: Directorio temporal del sistema (`tempdir/analyzer_media`)
- **TTL**: 600 segundos (10 minutos) configurable
- **Limpieza**: Automática tras completar análisis o caducidad

## ⚙️ Configuración Avanzada

### Habilitar H.264

Para navegadores más antiguos, se puede habilitar códec H.264:

```env
ENABLE_H264=1
```

Requiere DLL de OpenH264 válida en el sistema.

### Ajustar Threads de Gunicorn

En `docker-compose.yml`:

```yaml
command: sh -c "gunicorn -k gthread --threads 8 -w 2 -t 300 -b 0.0.0.0:5000 main:app"
```

### Aumentar Tamaño Máximo de Carga

```env
MAX_CONTENT_LENGTH=209715200  # 200MB
```

## 🧪 Testing

### Backend

```bash
# Ejecutar test de salud
curl http://localhost:5000/api/health

# Analizar video de prueba
curl -X POST http://localhost:5000/api/analyze \
  -F "video=@test_video.mp4" \
  -F "exercise_type=sentadilla"
```

### Frontend

```bash
cd frontend
npm run test
npm run lint
```

## 📖 Documentación Adicional

Consulta los siguientes archivos para más detalles:

- [docs/arquitectura-front-back.md](docs/arquitectura-front-back.md) - Arquitectura detallada y casos de uso
- [docs/pesudocodigos.md](docs/pesudocodigos.md) - Pseudocódigos de referencia

## 🚀 Deployment

### Render.com

El proyecto incluye `render.yaml` para deployment automático:

```bash
git push origin main
```

Render detectará automáticamente los cambios y desplegará la aplicación.

### Heroku (Legacy)

```bash
heroku create posturepro
heroku addons:create jawsdb:kitefin
git push heroku main
```

### Servidor Linux Propio

```bash
# Instalación de dependencias del sistema
sudo apt-get update
sudo apt-get install -y python3.12 python3.12-venv mysql-server ffmpeg

# Clonar y configurar
git clone <repo> posturepro
cd posturepro
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Systemd service file
sudo vim /etc/systemd/system/posturepro.service
# [Copiar contenido de servicio]

# Iniciar servicio
sudo systemctl enable posturepro
sudo systemctl start posturepro
```

## 🐛 Troubleshooting

### Error: "No module named 'mediapipe'"

```bash
pip install --upgrade mediapipe
```

### Error de Conexión a Base de Datos

```bash
# Verificar conexión MySQL
mysql -h localhost -u usuario -p -e "SELECT 1"

# Verificar DATABASE_URL
echo $DATABASE_URL
```

### Video no se procesa

```bash
# Verificar FFmpeg instalado
ffmpeg -version

# Verificar permisos de escritura en /tmp
ls -la /tmp | grep analyzer_media
```

### High Memory Usage

Reducir tamaño de video de entrada o ajustar threads de Gunicorn:

```yaml
command: sh -c "gunicorn -k gthread --threads 2 -w 1 -t 300 -b 0.0.0.0:5000 main:app"
```

## 📝 Licencia

Este proyecto está disponible bajo licencia proprietaria.

## 👥 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📧 Soporte

Para reportar bugs o solicitar features, abre un issue en el repositorio.

**Contacto del Autor**: Orlando Armando Apodaca Concha

---

**Última actualización**: Enero 29, 2026
