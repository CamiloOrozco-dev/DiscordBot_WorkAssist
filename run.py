#!/usr/bin/env python3
"""
Script principal para ejecutar el bot ZoroBot
"""

from src import DISCORD_BOT_TOKEN
from bot import bot

if __name__ == "__main__":
    if not DISCORD_BOT_TOKEN:
        print("Error: DISCORD_BOT_TOKEN no configurado en .env")
        exit(1)

    print("Iniciando ZoroBot...")
    bot.run(DISCORD_BOT_TOKEN)