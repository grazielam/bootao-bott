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

# [CONFIGURAÇÕES E FUNÇÕES DE BANCO DE DADOS MANTIDAS...]
ID_CANAL_TERMOS = 1457188949364707421  
ID_CANAL_REGRAS = 1457183013807853764  
ID_CATEGORIA_TICKETS = 1468070452655034499  
ID_CARGO_ATENDENTES = 1422264212817838132  

def rodar_servidor_web():
    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"Bot Online 24/7!")
    port = int(os.getenv("PORT", 8080))
    with socketserver.TCPServer(("", port), Handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=rodar_servidor_web, daemon=True).start()

def inicializar_banco():
    conn = sqlite3.connect("dados_loja.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS embeds_personalizados (
            titulo_chave TEXT PRIMARY KEY,
            titulo_resposta TEXT,
            texto_resposta TEXT,
            imagem_resposta TEXT,
            cor_int INTEGER
        )
    """)
    conn.commit()
    conn.close()

inicializar_banco()

def salvar_embed_no_banco(titulo_chave, titulo_resposta, texto_resposta, imagem_resposta, cor_int):
    conn = sqlite3.connect("dados_loja.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO embeds_personalizados VALUES (?, ?, ?, ?, ?)", 
                   (titulo_chave, titulo_resposta, texto_resposta, imagem_resposta, cor_int))
    conn.commit()
    conn.close()

def puxar_embed_do_banco(titulo_chave):
    conn = sqlite3.connect("dados_loja.db")
    cursor = conn.cursor()
    cursor.execute("SELECT titulo_resposta, texto_resposta, imagem_resposta, cor_int FROM embeds_personalizados WHERE titulo_chave = ?", (titulo_chave,))
    resultado = cursor.fetchone()
    conn.close()
    return {"titulo_resposta": resultado[0], "texto_resposta": resultado[1], "imagem_resposta": resultado[2], "cor_int": resultado[3]} if resultado else None

CHAVE_PIX_PADRAO = os.getenv("CHAVE_PIX", "bootaoservices01@gmail.com")
SETUP_TEMPORARIO_PARAMETROS = {}

# [VIEWS E MODAIS MANTIDOS IGUAIS AO SEU CÓDIGO...]
class ViewBotaoDinamicoGlobal(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Visualizar Informações", style=discord.ButtonStyle.primary, custom_id="btn_global_visualizar_info")
    async def responder_clique_dinamico(self, interaction: discord.Interaction, button: discord.ui.Button):
        titulo_painel = interaction.message.embeds[0].title
        dados = puxar_embed_do_banco(titulo_painel)
        if dados:
            embed = discord.Embed(title=dados["titulo_resposta"], description=dados["texto_resposta"], color=discord.Color(dados["cor_int"]))
            if dados["imagem_resposta"]: embed.set_image(url=dados["imagem_resposta"])
            await interaction.response.send_message(embed=embed, ephemeral=True)

class ModalFormularioTicket(discord.ui.Modal, title="🛒 Detalhes do Atendimento"):
    produto = discord.ui.TextInput(label="Produto", required=True)
    metodo = discord.ui.TextInput(label="Método", placeholder="Manual ou Script", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        categoria = discord.utils.get(guild.categories, id=ID_CATEGORIA_TICKETS)
        canal = await guild.create_text_channel(name=f"🛒-{interaction.user.name}", category=categoria)
        embed = discord.Embed(title="<:hutao:1467229432615010316> Detalhes", description=f"Produto: {self.produto.value}\nMétodo: {self.metodo.value}", color=0xc8131e)
        await canal.send(content=f"{interaction.user.mention} <@&{ID_CARGO_ATENDENTES}>", embed=embed)
        await interaction.response.send_message(f"✅ Ticket criado: {canal.mention}", ephemeral=True)

class ViewAbreTicketDinamico(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Abrir ticket", style=discord.ButtonStyle.success, custom_id="btn_abrir_ticket_dinamico")
    async def abrir_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalFormularioTicket())

# [BOT CLASS COM SINCRONIZAÇÃO CORRETA]
class HuTaoBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(ViewAbreTicketDinamico())
        self.add_view(ViewPainelLogin()) # Certifique-se de que essa classe esteja definida
        self.add_view(ViewBotaoDinamicoGlobal())
        await self.tree.sync() # Sincroniza apenas os comandos definidos abaixo

bot = HuTaoBot()

# [COMANDOS DE BARRA]
@bot.tree.command(name="pix", description="Gera cobrança PIX")
async def pix(interaction: discord.Interaction): await interaction.response.send_modal(ModalGerarPix())

@bot.tree.command(name="login", description="Solicita dados de acesso")
async def login(interaction: discord.Interaction): await interaction.response.send_message(view=ViewPainelLogin())

@bot.tree.command(name="diferenca", description="Diferença entre Manual e Script")
async def diferenca(interaction: discord.Interaction):
    await interaction.response.send_message("• **Manual:** Seguro.\n• **Script:** Rápido, mas com risco.")

@bot.tree.command(name="termos", description="Links dos termos")
async def termos(interaction: discord.Interaction):
    await interaction.response.send_message(embed=gerar_embed_termos(), view=ViewLinksTermos(interaction.guild_id, ID_CANAL_TERMOS, ID_CANAL_REGRAS))

@bot.event
async def on_ready():
    print(f"👻 Bot {bot.user.name} online!")

bot.run(os.getenv("DISCORD_TOKEN"))
