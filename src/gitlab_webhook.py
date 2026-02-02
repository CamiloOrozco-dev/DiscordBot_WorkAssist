from aiohttp import web
import json
import asyncio
import discord
from datetime import datetime
from src import GITLAB_ALLOWED_PROJECTS

class GitLabWebhookReceiver:
    def __init__(self, bot, channel_id, secret=None):
        self.bot = bot
        self.channel_id = int(channel_id) if channel_id else None
        self.secret = secret

    async def handle_webhook(self, request):
        # Verificar secreto si está configurado
        if self.secret:
            token = request.headers.get("X-Gitlab-Token")
            if token != self.secret:
                return web.Response(status=403, text="Invalid token")

        try:
            data = await request.json()
            event_type = request.headers.get("X-Gitlab-Event")
            
            # Filtrar por proyectos permitidos
            project_path = data.get("project", {}).get("path_with_namespace")
            if GITLAB_ALLOWED_PROJECTS and project_path not in GITLAB_ALLOWED_PROJECTS:
                print(f"ℹ️ Evento de proyecto ignorado (no está en la lista blanca): {project_path}")
                return web.Response(status=200)

            if not self.channel_id:
                print("⚠️ GITLAB_CHANNEL_ID no configurado. Ignorando evento.")
                return web.Response(status=200)

            channel = self.bot.get_channel(self.channel_id)
            if not channel:
                # Si el bot acaba de iniciar, tal vez el canal no está en caché
                channel = await self.bot.fetch_channel(self.channel_id)
            
            if channel:
                embed = self.format_event(event_type, data)
                if embed:
                    await channel.send(embed=embed)
            else:
                print(f"⚠️ No se pudo encontrar el canal {self.channel_id}")

            return web.Response(status=200)
        except Exception as e:
            print(f"❌ Error procesando webhook de GitLab: {str(e)}")
            return web.Response(status=500)

    def format_event(self, event_type, data):
        """Formatea el evento de GitLab en un Discord Embed"""
        embed = None
        
        if event_type == "Push Hook":
            repo_name = data.get("project", {}).get("name")
            user_name = data.get("user_name")
            ref = data.get("ref", "").split("/")[-1]
            commits = data.get("commits", [])
            num_commits = len(commits)
            
            if num_commits == 0:
                return None # Ignorar pushes sin commits (ej. tags)

            embed = discord.Embed(
                title=f"🚀 Nuevo Push en {repo_name}",
                description=f"**Usuario:** {user_name}\n**Rama:** `{ref}`\n**Commits:** {num_commits}",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            commit_list = ""
            for commit in commits[:5]: # Mostrar solo los últimos 5
                msg = commit.get("message", "").split("\n")[0]
                url = commit.get("url")
                commit_list += f"• [`{commit.get('id')[:7]}`]({url}) {msg}\n"
            
            if num_commits > 5:
                commit_list += f"... y {num_commits - 5} más"
                
            embed.add_field(name="Últimos Commits", value=commit_list, inline=False)

        elif event_type == "Merge Request Hook":
            repo_name = data.get("project", {}).get("name")
            user_name = data.get("user", {}).get("name")
            obj = data.get("object_attributes", {})
            title = obj.get("title")
            url = obj.get("url")
            state = obj.get("state") # opened, merged, closed
            action = obj.get("action") # open, update, merge, close
            
            color_map = {
                "opened": discord.Color.green(),
                "merged": discord.Color.purple(),
                "closed": discord.Color.red(),
                "reopened": discord.Color.gold()
            }
            
            status_text = {
                "open": "Abierto",
                "merge": "Fusionado",
                "close": "Cerrado",
                "reopen": "Reabierto",
                "update": "Actualizado"
            }

            embed = discord.Embed(
                title=f"🔀 Merge Request en {repo_name}",
                description=f"**[{title}]({url})**",
                color=color_map.get(state, discord.Color.greyple()),
                timestamp=datetime.now()
            )
            embed.add_field(name="Estado", value=status_text.get(action, action.capitalize()), inline=True)
            embed.add_field(name="Autor", value=user_name, inline=True)
            embed.add_field(name="Origen -> Destino", value=f"`{obj.get('source_branch')}` -> `{obj.get('target_branch')}`", inline=False)

        return embed

async def start_webhook_server(bot, port, channel_id, secret=None):
    receiver = GitLabWebhookReceiver(bot, channel_id, secret)
    app = web.Application()
    app.router.add_post("/gitlab", receiver.handle_webhook)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Servidor Webhook de GitLab escuchando en el puerto {port}")
