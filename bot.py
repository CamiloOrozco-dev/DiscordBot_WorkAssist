"""
Bot de Discord para Registro de Horas en Odoo
Funcionalidades:
- Registro de horas de trabajo
- Control de entrada/salida (clock in/out)
- Consulta de horas trabajadas
- Reportes diarios/semanales
- Integración con API de Odoo
"""

import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta
from typing import Optional
import json
import os

from src import JibbleAPI, WorkSession, DISCORD_BOT_TOKEN, USER_MAPPING_FILE, JIBBLE_PROJECT_ID, ROLE_ACTIVE_ID, ROLE_BREAK_ID, ROLE_INACTIVE_ID


# ============================================
# BOT DE DISCORD
# ============================================

class TimeTrackingBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.presences = True

        super().__init__(command_prefix="!", intents=intents)

        # Inicializar componentes
        self.jibble = JibbleAPI()
        self.work_sessions = WorkSession()
        self.user_mapping = {}  # discord_id -> jibble_person_id
        self.load_user_mapping()

    def load_user_mapping(self):
        """Cargar mapeo de usuarios Discord -> Jibble"""
        try:
            with open(USER_MAPPING_FILE, "r") as f:
                self.user_mapping = json.load(f)
        except FileNotFoundError:
            self.user_mapping = {}

    def save_user_mapping(self):
        """Guardar mapeo de usuarios"""
        with open(USER_MAPPING_FILE, "w") as f:
            json.dump(self.user_mapping, f, indent=2)

    async def setup_hook(self):
        """Sincronizar comandos slash"""
        # Sincronizar solo si hay cambios significativos o en desarrollo
        # await self.tree.sync() 
        print("Bot en proceso de configuración...")

    async def on_ready(self):
        """Evento cuando el bot está listo"""
        print(f"Bot conectado como {self.user}")
        print("--- Versión: 2.1.1 (Jibble Interaction Fix) ---")
        print("Bot listo para registrar en Jibble")

        # Iniciar tareas programadas
        if not self.daily_reminder.is_running():
            self.daily_reminder.start()

    async def close(self):
        """Cerrar el bot y las sesiones abiertas"""
        await self.jibble.close()
        await super().close()

    @tasks.loop(hours=24)
    async def daily_reminder(self):
        """Recordatorio diario para registrar horas"""
        now = datetime.now()
        if now.hour == 18:  # 6 PM
            # Enviar recordatorio a usuarios que no han registrado horas
            pass

    async def update_user_role(self, member: discord.Member, status: str):
        """Actualizar roles del usuario según su estado (Active, Break, Inactive)"""
        if not member.guild_permissions.manage_roles:
            # Si el bot no tiene permisos, no hacemos nada (pero el bot mismo debe tenerlos)
            pass

        role_map = {
            "Active": ROLE_ACTIVE_ID,
            "Break": ROLE_BREAK_ID,
            "Inactive": ROLE_INACTIVE_ID
        }

        target_role_id = role_map.get(status)
        if not target_role_id:
            return

        try:
            # Obtener objetos de rol
            roles_to_remove = [int(rid) for rid in role_map.values() if rid and int(rid) != int(target_role_id)]
            role_to_add = member.guild.get_role(int(target_role_id))

            # Remover roles de otros estados
            for r_id in roles_to_remove:
                r = member.guild.get_role(r_id)
                if r in member.roles:
                    await member.remove_roles(r)

            # Añadir el nuevo rol si no lo tiene
            if role_to_add and role_to_add not in member.roles:
                await member.add_roles(role_to_add)
                
        except Exception as e:
            print(f"⚠️ Error al actualizar roles para {member.name}: {str(e)}")


# ============================================
# COMANDOS SLASH
# ============================================

bot = TimeTrackingBot()

@bot.tree.command(name="clockin", description="Registrar entrada en Jibble")
@app_commands.describe(
    project="Nombre o ID del proyecto (Obligatorio)"
)
async def clock_in(
    interaction: discord.Interaction,
    project: str
):
    """Comando para registrar entrada"""
    # DEFER PRIMERO para evitar expiración
    try:
        await interaction.response.defer(ephemeral=True)
    except Exception as e:
        print(f"⚠️ Error al hacer defer en clockin: {str(e)}")
        return

    user_id = interaction.user.id
    jibble_person_id = bot.user_mapping.get(str(user_id))

    if not jibble_person_id:
        await interaction.followup.send(
            "⚠️ No estás vinculado a Jibble. Usa `/link_email` primero.",
            ephemeral=True
        )
        return

    # Verificar si ya hay una sesión activa
    if bot.work_sessions.get_session(user_id):
        await interaction.followup.send(
            "⚠️ Ya tienes una sesión activa en Discord. Usa `/clockout` primero.",
            ephemeral=True
        )
        return

    try:
        actual_project_id = await bot.jibble.get_project_by_name(project)
        
        if not actual_project_id:
            # Fallback al ID por defecto si el nombre no se encuentra
            actual_project_id = JIBBLE_PROJECT_ID or project

        result = await bot.jibble.create_time_entry(
            person_id=jibble_person_id,
            project_id=actual_project_id,
            activity_id=None,
            note=f"Clock-in desde Discord: {project}",
            type="In"
        )
        
        # Sincronización robusta: Si Jibble falla porque ya estás "In"
        # Actualizamos el estado local para que coincida.
        if not result and "invalid_interval_in_in" in str(bot.jibble.last_error_code if hasattr(bot.jibble, 'last_error_code') else ""):
             print(f"🔄 Auto-sync: El usuario {interaction.user.name} ya estaba In en Jibble.")
             bot.work_sessions.clock_in(user_id, project, None)
             await interaction.followup.send("ℹ️ Tu sesión de Jibble ya estaba activa. Sincronizando estado local...", ephemeral=True)
             await bot.update_user_role(interaction.user, "Active")
             return
        
        if result:
            session = bot.work_sessions.clock_in(user_id, project, None)
            session["project_id"] = actual_project_id
            
            embed = discord.Embed(
                title="✅ Entrada Registrada en Jibble",
                description=f"**Proyecto:** {project}",
                color=discord.Color.green(),
                timestamp=session["start_time"]
            )
            embed.set_footer(text=f"Usuario: {interaction.user.name}")
            await interaction.followup.send(embed=embed)
            
            # Actualizar rol a Activo
            await bot.update_user_role(interaction.user, "Active")
        else:
            error_status = getattr(bot.jibble, 'last_status', 0)
            if error_status >= 500:
                await interaction.followup.send("🔥 Jibble está teniendo problemas técnicos (Error 5xx). Por favor, intenta de nuevo en unos minutos.", ephemeral=True)
            else:
                await interaction.followup.send(
                    f"❌ Error al registrar entrada en Jibble. "
                    f"Código: {getattr(bot.jibble, 'last_error_code', 'DESCONOCIDO')}", 
                    ephemeral=True
                )
            
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)


@bot.tree.command(name="clockout", description="Registrar salida en Jibble")
@app_commands.describe(description="Descripción del trabajo realizado")
async def clock_out(
    interaction: discord.Interaction,
    description: str
):
    """Comando para registrar salida"""
    # DEFER PRIMERO
    try:
        await interaction.response.defer(ephemeral=True)
    except Exception as e:
        print(f"⚠️ Error al hacer defer en clockout: {str(e)}")
        return

    user_id = interaction.user.id
    jibble_person_id = bot.user_mapping.get(str(user_id))

    if not jibble_person_id:
        await interaction.followup.send(
            "⚠️ No estás vinculado a Jibble.",
            ephemeral=True
        )
        return

    # Verificar sesión activa localmente
    session = bot.work_sessions.get_session(user_id)
    if not session:
        await interaction.followup.send(
            "⚠️ No tienes ninguna sesión activa en Discord. Usa `/clockin` primero.",
            ephemeral=True
        )
        return

    # Registrar salida en Jibble
    try:
        # Usar el ID del proyecto guardado en la sesión
        project_id = session.get("project_id")
        
        # Si no hay ID (sesión antigua) o es un nombre, intentar resolverlo
        if not project_id or "-" not in str(project_id):
            project_name = project_id or session.get("project", "")
            resolved_id = await bot.jibble.get_project_by_name(project_name)
            # Si no se puede resolver, usar el ID por defecto (nunca usar el nombre como ID)
            if resolved_id:
                project_id = resolved_id
            elif JIBBLE_PROJECT_ID:
                project_id = JIBBLE_PROJECT_ID
            else:
                # Si no hay ID por defecto, no podemos continuar
                await interaction.followup.send(
                    "❌ No se pudo determinar el proyecto. Verifica tu configuración.",
                    ephemeral=True
                )
                return
        
        result_jibble = await bot.jibble.create_time_entry(
            person_id=jibble_person_id,
            project_id=project_id,
            activity_id=session["task"],
            note=description,
            type="Out"
        )

        # Sincronización robusta: Si ya habías salido en Jibble
        if not result_jibble:
            error_code = getattr(bot.jibble, 'last_error_code', "")
            if "invalid_interval_out_out" in str(error_code):
                print(f"🔄 Auto-sync: El usuario {interaction.user.name} ya había salido en Jibble.")
                bot.work_sessions.clock_out(user_id, "Sincronización automática de salida")
                await interaction.followup.send("ℹ️ Ya habías registrado tu salida en Jibble. Sincronizando estado local...", ephemeral=True)
                await bot.update_user_role(interaction.user, "Inactive")
                return

        if result_jibble:
            # Finalizar sesión local
            result_local = bot.work_sessions.clock_out(user_id, description)
            
            embed = discord.Embed(
                title="🏁 Salida Registrada en Jibble",
                description=f"**Horas calculadas (Discord):** {result_local['total_hours']:.2f}h\n"
                           f"**Proyecto:** {result_local['project']}\n"
                           f"**Descripción:** {description}\n\n"
                           f"✅ Sincronizado con Jibble",
                color=discord.Color.blue(),
                timestamp=result_local["end_time"]
            )
            embed.add_field(
                name="Inicio",
                value=result_local["start_time"].strftime("%H:%M:%S"),
                inline=True
            )
            embed.add_field(
                name="Fin",
                value=result_local["end_time"].strftime("%H:%M:%S"),
                inline=True
            )
            await interaction.followup.send(embed=embed)
            
            # Actualizar rol a Inactivo
            await bot.update_user_role(interaction.user, "Inactive")
        else:
            error_status = getattr(bot.jibble, 'last_status', 0)
            if error_status >= 500:
                await interaction.followup.send("🔥 Jibble está teniendo problemas técnicos (Error 5xx). Por favor, intenta de nuevo en unos minutos.", ephemeral=True)
            else:
                error_code = getattr(bot.jibble, 'last_error_code', 'DESCONOCIDO')
                await interaction.followup.send(f"❌ Error al registrar salida en Jibble (Código: {error_code}). Revisa los logs.", ephemeral=True)

    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)


@bot.tree.command(name="break", description="Iniciar/finalizar pausa en Jibble")
async def toggle_break(interaction: discord.Interaction):
    """Toggle de pausa sincronizado con Jibble"""
    try:
        await interaction.response.defer(ephemeral=True)
    except Exception as e:
        print(f"⚠️ Error al hacer defer en break: {str(e)}")
        return

    user_id = interaction.user.id
    jibble_person_id = bot.user_mapping.get(str(user_id))
    session = bot.work_sessions.get_session(user_id)

    if not session:
        await interaction.followup.send(
            "⚠️ No tienes ninguna sesión activa.",
            ephemeral=True
        )
        return

    if not jibble_person_id:
        await interaction.followup.send(
            "⚠️ No estás vinculado a Jibble.",
            ephemeral=True
        )
        return

    # Obtener ID del proyecto
    project_id = session.get("project_id")
    if not project_id or "-" not in str(project_id):
        project_name = project_id or session.get("project", "")
        resolved_id = await bot.jibble.get_project_by_name(project_name)
        # Si no se puede resolver, usar el ID por defecto (nunca usar el nombre como ID)
        if resolved_id:
            project_id = resolved_id
        elif JIBBLE_PROJECT_ID:
            project_id = JIBBLE_PROJECT_ID
        else:
            # Si no hay ID por defecto, no podemos continuar
            await interaction.followup.send(
                "❌ No se pudo determinar el proyecto. Asegúrate de haber hecho clockin primero.",
                ephemeral=True
            )
            return

    # Verificar si hay una pausa activa localmente
    breaks = session.get("breaks", [])
    is_on_break = breaks and "end" not in breaks[-1]

    try:
        if is_on_break:
            # Finalizar pausa -> EndBreak (Mapeado a 4 en la API)
            result = await bot.jibble.create_time_entry(
                person_id=jibble_person_id,
                project_id=project_id,
                activity_id=None,
                note="Fin de pausa (Discord)",
                type="EndBreak"
            )
            if result:
                bot.work_sessions.end_break(user_id)
                await interaction.followup.send("☕ Pausa finalizada y sincronizada con Jibble")
                # Volver a rol Activo
                await bot.update_user_role(interaction.user, "Active")
            else:
                await interaction.followup.send("❌ Error al finalizar pausa en Jibble. Revisa la consola.", ephemeral=True)
        else:
            # Iniciar pausa -> StartBreak (Mapeado a 3 en la API)
            result = await bot.jibble.create_time_entry(
                person_id=jibble_person_id,
                project_id=project_id,
                activity_id=None,
                note="Inicio de pausa (Discord)",
                type="StartBreak"
            )
            if result:
                bot.work_sessions.start_break(user_id)
                await interaction.followup.send("⏸️ Pausa iniciada y sincronizada con Jibble")
                # Cambiar a rol Break
                await bot.update_user_role(interaction.user, "Break")
            else:
                await interaction.followup.send("❌ Error al iniciar pausa en Jibble. Revisa la consola.", ephemeral=True)
                
    except Exception as e:
        error_status = getattr(bot.jibble, 'last_status', 0)
        error_code = getattr(bot.jibble, 'last_error_code', "")
        
        if error_status >= 500:
            await interaction.followup.send("🔥 Jibble está teniendo problemas técnicos (Error 5xx). Por favor, intenta de nuevo en unos minutos.", ephemeral=True)
            return

        # Sincronización robusta para fallos de estado en pausas
        if "validation_failed" in str(error_code) or "invalid_interval" in str(error_code):
             print(f"🔄 Auto-sync (Break): Error de validación detectado. Jibble y Discord están desincronizados.")
             await interaction.followup.send(
                 "⚠️ Jibble rechazó el cambio de estado (posible desincronización). "
                 "Usa `/jibble_status` para verificar tu estado real en Jibble.", 
                 ephemeral=True
             )
             return

        await interaction.followup.send(f"❌ Error en pausa: {str(e)}", ephemeral=True)


@bot.tree.command(name="status", description="Ver tu estado actual sincronizado con Jibble")
async def status(interaction: discord.Interaction):
    """Ver estado de la sesión actual consultando Jibble"""
    try:
        await interaction.response.defer(ephemeral=True)
    except Exception as e:
        print(f"⚠️ Error al hacer defer en status: {str(e)}")
        return

    user_id = interaction.user.id
    jibble_person_id = bot.user_mapping.get(str(user_id))
    local_session = bot.work_sessions.get_session(user_id)

    # Si no está vinculado a Jibble, mostrar solo estado local
    if not jibble_person_id:
        if not local_session:
            await interaction.followup.send(
                "❌ No tienes ninguna sesión activa.\n"
                "💡 Usa `/link_email` para vincular con Jibble y ver tu estado real.",
                ephemeral=True
            )
            return
        
        # Mostrar solo estado local (sin Jibble)
        elapsed = datetime.now() - local_session["start_time"]
        hours = elapsed.total_seconds() / 3600
        total_break_time = sum(
            ((b.get("end", datetime.now()) - b["start"]).total_seconds())
            for b in local_session["breaks"]
        )
        break_hours = total_break_time / 3600
        in_break = local_session["breaks"] and "end" not in local_session["breaks"][-1]

        embed = discord.Embed(
            title="📊 Estado Local (Discord solamente)",
            description="⚠️ No vinculado a Jibble - mostrando solo datos locales",
            color=discord.Color.orange() if in_break else discord.Color.green()
        )
        embed.add_field(name="Proyecto", value=local_session["project"], inline=True)
        embed.add_field(name="Tiempo transcurrido", value=f"{hours:.2f}h", inline=True)
        embed.add_field(name="Tiempo en pausas", value=f"{break_hours:.2f}h", inline=True)
        embed.add_field(name="Tiempo efectivo", value=f"{(hours - break_hours):.2f}h", inline=True)
        embed.add_field(name="Estado", value="⏸️ En pausa" if in_break else "▶️ Trabajando", inline=True)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    # Consultar estado en Jibble
    try:
        entries = await bot.jibble.get_time_entries(jibble_person_id, limit=10)
        if not entries:
            await interaction.followup.send(
                "⚠️ No se pudieron obtener tus entradas de Jibble.\n"
                f"Estado local: {'Activo' if local_session else 'Inactivo'}",
                ephemeral=True
            )
            return

        # Analizar entradas para determinar estado actual en Jibble
        jibble_state = "Inactive"  # Por defecto
        last_in_time = None
        last_break_start_time = None
        project_name = "Desconocido"

        for entry in entries:
            entry_type = str(entry.get("type", ""))
            entry_time = entry.get("time", "")
            
            # Type "In" = In (Entrada) - probando con string
            if entry_type == "In" or entry_type.lower() == "in":
                if not last_in_time:  # Primera entrada "In" encontrada (más reciente)
                    last_in_time = entry_time
                    project_name = entry.get("projectName", "Desconocido")
                    jibble_state = "Active"
                break  # Ya encontramos la última entrada In
            
            # Type "1" = Out (Salida) - si aparece primero, significa que está inactivo
            elif entry_type == "1":
                jibble_state = "Inactive"
                break
            
            # Type "2" = StartBreak (Inicio de pausa)
            elif entry_type == "2":
                if not last_break_start_time:
                    last_break_start_time = entry_time
                    jibble_state = "Break"
                break
            
            # Type "0" = EndBreak (Fin de pausa) - continuar buscando
            elif entry_type == "0":
                continue

        # Auto-sincronizar si Jibble muestra activo/break pero Discord no tiene sesión
        sync_message = ""
        if jibble_state in ["Active", "Break"] and not local_session:
            # Crear sesión local automáticamente
            try:
                dt_in = datetime.fromisoformat(last_in_time.replace("Z", "+00:00"))
                local_start = dt_in.astimezone().replace(tzinfo=None)
            except:
                local_start = datetime.now()
            
            bot.work_sessions.clock_in(user_id, project_name, None)
            local_session = bot.work_sessions.get_session(user_id)
            local_session["start_time"] = local_start
            
            if jibble_state == "Break":
                bot.work_sessions.start_break(user_id)
            
            sync_message = "\n🔄 **Sesión sincronizada automáticamente desde Jibble**"
            await bot.update_user_role(interaction.user, jibble_state.replace("Active", "Active").replace("Break", "Break").replace("Inactive", "Inactive"))

        # Preparar embed con información
        if jibble_state == "Inactive":
            embed = discord.Embed(
                title="📊 Estado Actual",
                description="❌ No tienes ninguna sesión activa en Jibble" + sync_message,
                color=discord.Color.red()
            )
            embed.add_field(name="Estado en Jibble", value="🔴 Inactivo", inline=True)
            if local_session:
                embed.add_field(name="Estado Local", value="⚠️ Desincronizado (limpiando...)", inline=True)
                bot.work_sessions.sessions.pop(user_id, None)  # Limpiar sesión local
        else:
            # Calcular tiempos si hay sesión local
            if local_session:
                elapsed = datetime.now() - local_session["start_time"]
                hours = elapsed.total_seconds() / 3600
                total_break_time = sum(
                    ((b.get("end", datetime.now()) - b["start"]).total_seconds())
                    for b in local_session["breaks"]
                )
                break_hours = total_break_time / 3600
                in_break = local_session["breaks"] and "end" not in local_session["breaks"][-1]
            else:
                hours = 0
                break_hours = 0
                in_break = False

            status_icon = "⏸️ En pausa" if jibble_state == "Break" else "▶️ Trabajando"
            embed_color = discord.Color.orange() if jibble_state == "Break" else discord.Color.green()

            embed = discord.Embed(
                title="📊 Estado Actual (Sincronizado con Jibble)",
                description=sync_message if sync_message else "✅ Sincronizado con Jibble",
                color=embed_color
            )
            embed.add_field(name="Estado en Jibble", value=status_icon, inline=True)
            embed.add_field(name="Proyecto", value=project_name, inline=True)
            
            if local_session:
                embed.add_field(name="Tiempo transcurrido", value=f"{hours:.2f}h", inline=True)
                embed.add_field(name="Tiempo en pausas", value=f"{break_hours:.2f}h", inline=True)
                embed.add_field(name="Tiempo efectivo", value=f"{(hours - break_hours):.2f}h", inline=True)

        await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        await interaction.followup.send(
            f"❌ Error al consultar estado: {str(e)}\n"
            f"Estado local: {'Activo' if local_session else 'Inactivo'}",
            ephemeral=True
        )


@bot.tree.command(name="jibble_status", description="Ver tus últimas entradas registradas en Jibble")
async def jibble_status(interaction: discord.Interaction):
    """Ver el historial reciente de Jibble para diagnóstico"""
    try:
        await interaction.response.defer(ephemeral=True)
    except Exception:
        return

    user_id = interaction.user.id
    jibble_person_id = bot.user_mapping.get(str(user_id))

    if not jibble_person_id:
        await interaction.followup.send("⚠️ No estás vinculado a Jibble. Usa `/link_email` primero.", ephemeral=True)
        return

    try:
        entries = await bot.jibble.get_time_entries(jibble_person_id)
        if not entries:
            await interaction.followup.send("❌ No se encontraron entradas recientes en Jibble.", ephemeral=True)
            return

        # Mapeo inverso corregido para coincidir con jibble_api.py
        # "0": EndBreak, "1": Out, "2": StartBreak, "In": string
        type_names = {
            "0": "☕ Fin de Pausa (EndBreak)",
            "1": "🏁 Salida (Out)",
            "2": "⏸️ Inicio de Pausa (StartBreak)",
            "In": "▶️ Entrada (In)",
            "Out": "🏁 Salida (Out)"
        }

        description = "Últimas 5 entradas en Jibble:\n\n"
        for e in entries:
            t = e.get("type", "N/A")
            t_name = type_names.get(str(t), f"Tipo {t}")
            dt_str = e.get("time", "N/A")
            try:
                dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                dt_fmt = dt.strftime("%d/%m %H:%M:%S")
            except:
                dt_fmt = dt_str

            description += f"**{dt_fmt}** - {t_name}\n"

        embed = discord.Embed(
            title="📊 Historial Reciente de Jibble",
            description=description,
            color=discord.Color.blue()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Error al obtener historial: {str(e)}", ephemeral=True)


@bot.tree.command(name="link_email", description="Vincular tu cuenta con Jibble usando tu email")
@app_commands.describe(email="Tu email en Jibble")
async def link_email(interaction: discord.Interaction, email: str):
    """Vincular cuenta de Discord con Jibble buscando el email"""
    try:
        await interaction.response.defer(ephemeral=True)
    except discord.errors.NotFound:
        print("⚠️ La interacción expiró antes de poder responder (defer)")
        return
    except Exception as e:
        print(f"⚠️ Error al hacer defer: {str(e)}")
        return
    
    user_id = str(interaction.user.id)
    
    try:
        person_id = await bot.jibble.get_person_by_email(email)
        
        if person_id:
            bot.user_mapping[user_id] = person_id
            bot.save_user_mapping()
            await interaction.followup.send(
                f"✅ Cuenta vinculada exitosamente con Jibble (ID: {person_id})",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"❌ No se encontró ningún usuario con el email `{email}` en Jibble. "
                "Asegúrate de que el email es exactamente el mismo que usas en Jibble.",
                ephemeral=True
            )
    except Exception as e:
        print(f"❌ Error en link_email: {str(e)}")
        await interaction.followup.send(
            f"❌ Ocurrió un error al intentar vincular la cuenta: {str(e)}", 
            ephemeral=True
        )


@bot.tree.command(name="find_id", description="Buscar tu Jibble Person ID usando tu email")
@app_commands.describe(email="Tu email en Jibble")
async def find_id(interaction: discord.Interaction, email: str):
    """Buscar Person ID por email sin vincular automáticamente"""
    try:
        await interaction.response.defer(ephemeral=True)
    except Exception:
        return

    try:
        person_id = await bot.jibble.get_person_by_email(email)
        if person_id:
            await interaction.followup.send(
                f"🔍 Tu Person ID para el correo `{email}` es: `{person_id}`\n"
                f"Puedes usarlo con `/link person_id:{person_id}` para vincular tu cuenta.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"❌ No se encontró ningún usuario con el correo `{email}` en Jibble.",
                ephemeral=True
            )
    except Exception as e:
        await interaction.followup.send(f"❌ Error al buscar ID: {str(e)}", ephemeral=True)


@bot.tree.command(name="jibble_users", description="[Admin] Listar todos los usuarios de Jibble y sus IDs")
async def list_jibble_users(interaction: discord.Interaction):
    """Listar todos los usuarios de la organización en Jibble"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ No tienes permisos para ejecutar este comando.",
            ephemeral=True
        )
        return

    try:
        await interaction.response.defer(ephemeral=True)
    except Exception:
        return

    try:
        people = await bot.jibble.get_people()
        if not people:
            await interaction.followup.send("❌ No se pudieron obtener los usuarios de Jibble.", ephemeral=True)
            return

        # Crear un embed o mensaje formateado (Discord tiene límite de 2000 caracteres)
        description = "Lista de usuarios encontrados en Jibble:\n\n"
        for p in people[:25]: # Limitar a los primeros 25 para no exceder límites de embed
            name = p.get("fullName", "N/A")
            email = p.get("email", "N/A")
            pid = p.get("id", "N/A")
            description += f"👤 **{name}**\n📧 {email}\n🆔 `{pid}`\n\n"

        embed = discord.Embed(
            title="👥 Usuarios de Jibble",
            description=description,
            color=discord.Color.blue()
        )
        if len(people) > 25:
            embed.set_footer(text=f"Mostrando 25 de {len(people)} usuarios.")

        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Error al listar usuarios: {str(e)}", ephemeral=True)


@bot.tree.command(name="jibble_projects", description="[Admin] Listar todos los proyectos de Jibble y sus IDs")
async def list_jibble_projects(interaction: discord.Interaction):
    """Listar todos los proyectos de la organización en Jibble"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ No tienes permisos para ejecutar este comando.",
            ephemeral=True
        )
        return

    try:
        await interaction.response.defer(ephemeral=True)
    except Exception:
        return

    try:
        projects = await bot.jibble.get_projects()
        if not projects:
            await interaction.followup.send("❌ No se pudieron obtener los proyectos de Jibble.", ephemeral=True)
            return

        description = "Lista de proyectos encontrados en Jibble:\n\n"
        for p in projects[:25]:
            name = p.get("name", "N/A")
            pid = p.get("id", "N/A")
            description += f"📁 **{name}**\n🆔 `{pid}`\n\n"

        embed = discord.Embed(
            title="📂 Proyectos de Jibble",
            description=description,
            color=discord.Color.green()
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Error al listar proyectos: {str(e)}", ephemeral=True)


@bot.tree.command(name="jibble_activities", description="[Admin] Listar todas las actividades de Jibble y sus IDs")
async def list_jibble_activities(interaction: discord.Interaction):
    """Listar todas las actividades de la organización usando v1 Activities"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ No tienes permisos para ejecutar este comando.",
            ephemeral=True
        )
        return

    try:
        await interaction.response.defer(ephemeral=True)
    except Exception:
        return

    try:
        activities = await bot.jibble.get_activities()
        if not activities:
            await interaction.followup.send("❌ No se pudieron obtener las actividades de Jibble.", ephemeral=True)
            return

        description = "Lista de actividades encontradas en Jibble:\n\n"
        for a in activities[:25]:
            name = a.get("name", "N/A")
            aid = a.get("id", "N/A")
            description += f"📝 **{name}**\n🆔 `{aid}`\n\n"

        embed = discord.Embed(
            title="📝 Actividades de Jibble",
            description=description,
            color=discord.Color.blue()
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Error al listar actividades: {str(e)}", ephemeral=True)


@bot.tree.command(name="link", description="Vincular tu cuenta con Jibble usando tu Person ID")
@app_commands.describe(person_id="Tu Person ID de Jibble")
async def link_account(interaction: discord.Interaction, person_id: str):
    """Vincular cuenta de Discord con Jibble mediante ID directo"""
    user_id = str(interaction.user.id)

    bot.user_mapping[user_id] = person_id
    bot.save_user_mapping()

    await interaction.response.send_message(
        f"✅ Cuenta vinculada exitosamente con Jibble ID: {person_id}",
        ephemeral=True
    )


@bot.tree.command(name="help", description="Mostrar ayuda y lista de comandos")
async def help_command(interaction: discord.Interaction):
    """Mostrar lista de comandos disponibles"""
    embed = discord.Embed(
        title="❓ Ayuda de ZoroBot (Jibble Version)",
        description="Aquí tienes la lista de comandos disponibles para gestionar tu tiempo en Jibble:",
        color=discord.Color.gold()
    )
    
    embed.add_field(
        name="🔗 Configuración",
        value=(
            "`/link_email` - Vincula tu Discord con Jibble usando tu email.\n"
            "`/link` - Vincula usando tu Person ID de Jibble directamente.\n"
            "`/find_id` - Busca tu Person ID de Jibble con tu correo."
        ),
        inline=False
    )
    
    embed.add_field(
        name="⏱️ Registro de Tiempo",
        value=(
            "`/clockin` - Registrar entrada (In) en Jibble.\n"
            "`/clockout` - Registrar salida (Out) en Jibble.\n"
            "`/break` - Iniciar o finalizar una pausa (Local)."
        ),
        inline=False
    )
    
    embed.add_field(
        name="📊 Información",
        value=(
            "`/status` - Ver tu estado actual y tiempo transcurrido.\n"
            "`/help` - Muestra este mensaje de ayuda."
        ),
        inline=False
    )
    
    embed.add_field(
        name="👤 Admin",
        value=(
            "`/report` - Información sobre reportes.\n"
            "`/jibble_users` - Listar todos los usuarios y sus IDs.\n"
            "`/jibble_projects` - Listar todos los proyectos y sus IDs."
        ),
        inline=False
    )
    
    embed.set_footer(text="Usa / para ver la lista completa de comandos de Discord.")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ============================================
# COMANDOS DE ADMINISTRADOR
# ============================================

@bot.tree.command(name="report", description="[Admin] Generar reporte de horas")
@app_commands.describe(
    user="Usuario del reporte",
    period="Período del reporte"
)
@app_commands.choices(period=[
    app_commands.Choice(name="Hoy", value="today"),
    app_commands.Choice(name="Esta semana", value="week"),
    app_commands.Choice(name="Este mes", value="month")
])
async def admin_report(
    interaction: discord.Interaction,
    user: discord.Member,
    period: str
):
    """Generar reporte de horas de un usuario (Actualizar para API Jibble si es necesario)"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ No tienes permisos para ejecutar este comando.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        f"📊 Reportes administrativos se deben consultar directamente en el panel de Jibble para mayor detalle.",
        ephemeral=True
    )


# ============================================
# EVENTOS DE PRESENCIA
# ============================================

@bot.event
async def on_presence_update(before: discord.Member, after: discord.Member):
    """Detectar cambios de estado online/offline (opcional)"""
    pass


# ============================================
# EJECUTAR BOT
# ============================================

if __name__ == "__main__":
    if not DISCORD_BOT_TOKEN:
        print("Error: DISCORD_BOT_TOKEN no configurado")
    else:
        bot.run(DISCORD_BOT_TOKEN)
