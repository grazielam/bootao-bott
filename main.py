import discord
from discord.ext import commands
from discord import app_commands
import os
import threading
import http.server
import socketserver
import sys
import re
import sqlite3
import asyncio

# ==========================================
# ⚙️ CONFIGURAÇÕES DA LOJA
# ==========================================
ID_CANAL_TERMOS = 1457188949364707421  
ID_CANAL_REGRAS = 1457183013807853764  
ID_CATEGORIA_TICKETS = 1468070452655034499  
ID_CARGO_ATENDENTES = 1422264212817838132

# [MANTIVE O SERVIDOR WEB E BANCO DE DADOS IGUAIS...]
# (Ocultados aqui para brevidade, mantenha os seus originais)

# ==========================================
# 🤖 CONFIGURAÇÃO DO BOT E VIEWS GLOBAIS
# ==========================================
CHAVE_PIX_PADRAO = os.getenv("CHAVE_PIX", "bootaoservices01@gmail.com")
SETUP_TEMPORARIO_PARAMETROS = {}

# [MANTIVE AS VIEWS E MODAIS IGUAIS...]
# (Mantenha o restante das suas classes de View e Modal exatamente como estavam)

class HuTaoBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # ESTA LINHA É A CHAVE: Ela limpa os comandos antigos antes de registrar os novos
        self.tree.clear_commands(guild=None)
        
        self.add_view(ViewAbreTicketDinamico())
        self.add_view(ViewPainelLogin())
        self.add_view(ViewBotaoDinamicoGlobal())
        
        # Sincroniza a nova lista limpa com o Discord
        await self.tree.sync()

bot = HuTaoBot()

# ==========================================
# 👑 COMANDOS DE BARRA ADMINISTRATIVOS
# ==========================================

@bot.tree.command(name="fechar_ticket", description="Fecha o canal de atendimento atual")
@app_commands.default_permissions(manage_channels=True)
async def fechar_ticket(interaction: discord.Interaction):
    await interaction.response.send_message("⏳ Deletando este canal de atendimento em 5 segundos...")
    await asyncio.sleep(5)
    await interaction.channel.delete()

@bot.tree.command(name="setup_panel", description="Cria e envia um painel de tickets 100% customizável")
@app_commands.describe(canal="Selecione o canal onde o painel de tickets será enviado")
@app_commands.default_permissions(administrator=True)
async def setup_panel_slash(interaction: discord.Interaction, canal: discord.TextChannel):
    await interaction.response.send_modal(ModalCriarSetupCompleto(canal))

@bot.tree.command(name="criar_embed", description="Cria uma embed totalmente customizada com imagem e botão informativo")
@app_commands.describe(canal="Canal de destino", cor_hex="Cor lateral em Hex", url_imagem_principal="Link do banner")
@app_commands.default_permissions(administrator=True)
async def criar_embed_slash(interaction: discord.Interaction, canal: discord.TextChannel, cor_hex: str = None, url_imagem_principal: str = None):
    token_id = str(interaction.id)
    SETUP_TEMPORARIO_PARAMETROS[token_id] = {"canal": canal, "cor_hex": cor_hex, "url_imagem_principal": url_imagem_principal}
    await interaction.response.send_modal(ModalCriarEmbedCompleto(token_id))

@bot.tree.command(name="reiniciar", description="Reinicia o bot")
@app_commands.default_permissions(administrator=True)
async def reiniciar_slash(interaction: discord.Interaction):
    await interaction.response.send_message("🔄 Reiniciando...", ephemeral=True)
    await bot.close()
    sys.exit(0)

@bot.tree.command(name="pix", description="Gera cobrança PIX")
async def pix(interaction: discord.Interaction):
    await interaction.response.send_modal(ModalGerarPix())

@bot.tree.command(name="login", description="Solicita os dados de acesso")
async def login(interaction: discord.Interaction):
    # [Mantido conforme seu código]
    ...

@bot.tree.command(name="diferenca", description="Diferença entre Manual e Script")
async def diferenca(interaction: discord.Interaction):
    # [Mantido conforme seu código]
    ...

@bot.tree.command(name="termos", description="Links dos termos")
async def termos(interaction: discord.Interaction):
    # [Mantido conforme seu código]
    ...

# --- COMANDOS builds, feedback e genshin REMOVIDOS AQUI ---

@bot.event
async def on_ready():
    print(f"👻 Bot {bot.user.name} online e comandos limpos!")

bot.run(os.getenv("DISCORD_TOKEN"))
