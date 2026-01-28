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
- **Gestión de pausas**: `/break` (Local)
- **Consulta de estado**: `/status`
- **Vinculación de cuentas**: `/link_email` (fácil) o `/link` (Manual)
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