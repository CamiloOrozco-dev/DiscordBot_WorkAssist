# ZoroBot - Bot de Discord para Registro de Horas en Jibble

Este bot permite a los usuarios registrar sus horas de trabajo directamente desde Discord, integrándose con **Jibble** (v2.0).

## Estructura del Proyecto

```
zoroBot/
├── src/
│   ├── __init__.py      # Paquete principal
│   ├── config.py        # Configuraciones y variables de entorno
│   ├── jibble_api.py    # Cliente para la API de Jibble [NUEVO]
│   └── work_session.py  # Gestión de sesiones de trabajo
├── bot.py               # Bot de Discord y comandos
├── run.py               # Script principal para ejecutar el bot
├── requirements.txt     # Dependencias de Python
├── .env                 # Variables de entorno (configurar)
├── user_mapping.json    # Mapeo de usuarios Discord -> Jibble (generado)
└── README.md           # Este archivo
```

## Funcionalidades

- **Registro de entrada/salida**: `/clockin` y `/clockout` (Sincronizado con Jibble)
- **Gestión de pausas**: `/break` (Sincronizado con Jibble)
- **Consulta de estado**: `/status` (Sincronizado con Jibble)
- **Vinculación de cuentas**: `/link_email` (fácil) o `/link` (Manual)
- **Notificaciones de GitLab**: Recibe eventos de Push y Merge Requests en Discord
- **Ayuda**: `/help`
- **Reportes administrativos**: `/report` (Solo visualización)

## Instalación

1. **Clona o descarga los archivos del proyecto**

2. **Instala las dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configura las variables de entorno:**
   Edita el archivo `.env` con tus credenciales de Jibble:
   - `DISCORD_BOT_TOKEN`: Token de tu bot de Discord
   - `JIBBLE_CLIENT_ID`: Client ID de Jibble
   - `JIBBLE_CLIENT_SECRET`: Client Secret de Jibble
   - `JIBBLE_ORG_ID`: Organization ID de Jibble

## Uso

1. **Ejecuta el bot:**
   En Windows (PowerShell/CMD):
   ```bash
   py run.py
   ```
   En Linux/Mac:
   ```bash
   python3 run.py
   ```

2. **Comandos principales:**
   - `/link_email email`: Vincula tu cuenta con Jibble
   - `/clockin proyecto [tarea]`: Iniciar jornada en Jibble
   - `/clockout descripción`: Finalizar jornada y añadir nota
   - `/break`: Pausar/Reanudar (Local)
   - `/status`: Ver tiempo trabajado hoy
   - `/help`: Ver todos los comandos

## Desarrollo

El bot utiliza el flujo de **OAuth2 Client Credentials** para comunicarse con la API de Jibble. Toda la lógica de la API está en `src/jibble_api.py`.

## GitLab Integration

El bot incluye un servidor webhook que recibe eventos de GitLab y los publica en un canal de Discord.

### Configuración:
1. Configura las variables de entorno en `.env`:
   - `GITLAB_WEBHOOK_PORT`: Puerto del servidor (default: 5000)
   - `GITLAB_CHANNEL_ID`: ID del canal de Discord para notificaciones
   - `GITLAB_WEBHOOK_SECRET`: Token secreto para validar requests
   - `GITLAB_ALLOWED_PROJECTS`: Lista de proyectos permitidos (separados por coma)

2. Configura el webhook en GitLab:
   - URL: `https://tu-dominio.com/gitlab`
   - Secret Token: El valor de `GITLAB_WEBHOOK_SECRET`
   - Triggers: Push events, Merge request events

## Deployment en Railway.app

Para desplegar en Railway (recomendado para exponer el servidor webhook):

1. Crea una cuenta en [railway.app](https://railway.app)
2. Conecta tu repositorio de GitHub
3. Configura las variables de entorno en Railway
4. Genera un dominio público en Settings → Networking
5. Usa ese dominio para configurar los webhooks de GitLab

Ver [railway_migration.md](railway_migration.md) para más detalles.