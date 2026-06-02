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
from datetime import datetime

# ==========================================
# ⚙️ CONFIGURAÇÕES DA LOJA
# ==========================================
ID_CANAL_TERMOS = 1457188949364707421  
ID_CANAL_REGRAS = 1457183013807853764  
ID_CATEGORIA_TICKETS = 1468070452655034499  
ID_CARGO_ATENDENTES = 1422264212817838132  
ID_CANAL_LOGS = 1457188949364707421 # Ajuste para o canal de logs

# ==========================================
# 🌐 SERVIDOR WEB (MANTER ONLINE)
# ==========================================
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

# ==========================================
# 🗄️ BANCO DE DADOS
# ==========================================
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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets_ativos (
            canal_id INTEGER PRIMARY KEY,
            usuario_id INTEGER,
            staff_id INTEGER,
            data_criacao TEXT,
            data_assumido TEXT,
            assunto TEXT
        )
    """)
    conn.commit()
    conn.close()

inicializar_banco()

def registrar_ticket(canal_id, usuario_id, assunto):
    conn = sqlite3.connect("dados_loja.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tickets_ativos (canal_id, usuario_id, data_criacao, assunto) VALUES (?, ?, ?, ?)",
                   (canal_id, usuario_id, datetime.now().isoformat(), assunto))
    conn.commit()
    conn.close()

def assumir_ticket_db(canal_id, staff_id):
    conn = sqlite3.connect("dados_loja.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tickets_ativos SET staff_id = ?, data_assumido = ? WHERE canal_id = ?",
                   (staff_id, datetime.now().isoformat(), canal_id))
    conn.commit()
    conn.close()

def obter_dados_ticket(canal_id):
    conn = sqlite3.connect("dados_loja.db")
    cursor = conn.cursor()
    cursor.execute("SELECT usuario_id, staff_id, data_criacao, data_assumido, assunto FROM tickets_ativos WHERE canal_id = ?", (canal_id,))
    res = cursor.fetchone()
    conn.close()
    return res

def puxar_embed_do_banco(titulo_chave):
    conn = sqlite3.connect("dados_loja.db")
    cursor = conn.cursor()
    cursor.execute("SELECT titulo_resposta, texto_resposta, imagem_resposta, cor_int FROM embeds_personalizados WHERE titulo_chave = ?", (titulo_chave,))
    resultado = cursor.fetchone()
    conn.close()
    if resultado:
        return {"titulo_resposta": resultado[0], "texto_resposta": resultado[1], "imagem_resposta": resultado[2], "cor_int": resultado[3]}
    return None

CHAVE_PIX_PADRAO = os.getenv("CHAVE_PIX", "bootaoservices01@gmail.com")

# ==========================================
# 🛠️ CLASSES DE INTERAÇÃO (VIEWS/MODAIS)
# ==========================================

class ViewControleTicket(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)

    @discord.ui.button(label="Assumir Ticket", style=discord.ButtonStyle.primary, custom_id="btn_assumir_ticket")
    async def assumir(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.get_role(ID_CARGO_ATENDENTES) and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Apenas atendentes podem assumir tickets.", ephemeral=True)
        assumir_ticket_db(interaction.channel_id, interaction.user.id)
        button.disabled = True
        button.label = f"Assumido por {interaction.user.name}"
        await interaction.response.edit_message(view=self)
        await interaction.channel.send(f"✅ Este ticket agora está sendo atendido por {interaction.user.mention}")

    @discord.ui.button(label="Finalizar Atendimento", style=discord.ButtonStyle.danger, custom_id="btn_finalizar_ticket")
    async def finalizar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.get_role(ID_CARGO_ATENDENTES) and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Apenas atendentes podem finalizar tickets.", ephemeral=True)
        dados = obter_dados_ticket(interaction.channel_id)
        if not dados: return await interaction.response.send_message("Erro ao recuperar dados.", ephemeral=True)
        
        usuario_id, staff_id, data_criacao, data_assumido, assunto = dados
        usuario = interaction.guild.get_member(usuario_id)
        finalizado_dt = datetime.now()
        criado_dt = datetime.fromisoformat(data_criacao)
        assumido_dt = datetime.fromisoformat(data_assumido) if data_assumido else criado_dt

        def format_delta(td):
            if td.days > 0: return f"há {td.days} dias"
            hours = td.seconds // 3600
            if hours > 0: return f"há {hours} horas"
            return f"há {td.seconds // 60} minutos"

        embed = discord.Embed(title="✅ Atendimento Finalizado", color=0x2ecc71)
        embed.description = "🔴 Ticket fechado e atendimento finalizado"
        embed.add_field(name="# Canal ID:", value=f"`{interaction.channel_id}`", inline=False)
        embed.add_field(name="👤 Usuário", value=f"**Nome:** {usuario.name if usuario else 'N/A'}\n**Usuário:** {usuario.mention if usuario else 'N/A'}\n**ID:** `{usuario_id}`", inline=True)
        embed.add_field(name="📜 Dados do Ticket", value=f"**ID:** `{interaction.channel_id}`\n**Modelo:** Ticket de Compra\n**Assunto:** {assunto}\n**Status:** 🔴 Finalizado", inline=True)
        embed.add_field(name="🕒 Timeline do Ticket", value=f"✅ **Criado:** {format_delta(finalizado_dt-criado_dt)} por {usuario.mention if usuario else 'N/A'}\n✅ **Assumido:** {format_delta(finalizado_dt-assumido_dt)} por Staff\n🔴 **Finalizado:** agora mesmo por {interaction.user.mention} ❤️", inline=False)
        embed.set_footer(text="Sistema de Tickets + IA Completo")
        
        view_transcricao = discord.ui.View()
        view_transcricao.add_item(discord.ui.Button(label="Ver Transcrição", style=discord.ButtonStyle.link, url="https://discord.com"))
        
        canal_logs = interaction.guild.get_channel(ID_CANAL_LOGS)
        if canal_logs: await canal_logs.send(embed=embed, view=view_transcricao)
        await interaction.response.send_message("O ticket será deletado em 5 segundos...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

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

class ModalFormularioTicket(discord.ui.Modal, title=" Detalhes do Atendimento"):
    produto = discord.ui.TextInput(label="Produto", required=True)
    metodo = discord.ui.TextInput(label="Método", placeholder="Manual ou Script", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        categoria = discord.utils.get(guild.categories, id=ID_CATEGORIA_TICKETS)
        canal = await guild.create_text_channel(name=f"-{interaction.user.name}", category=categoria)
        registrar_ticket(canal.id, interaction.user.id, self.produto.value)
        embed = discord.Embed(title="⚠️ Detalhes", description=f"Produto: {self.produto.value}\nMétodo: {self.metodo.value}", color=0xc8131e)
        await canal.send(content=f"{interaction.user.mention} <@&{ID_CARGO_ATENDENTES}>", embed=embed, view=ViewControleTicket())
        await interaction.response.send_message(f"✅ Ticket criado: {canal.mention}", ephemeral=True)

class ViewAbreTicketDinamico(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label=" Fazer Pedido", style=discord.ButtonStyle.success, custom_id="btn_abrir_ticket_dinamico")
    async def abrir_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalFormularioTicket())

class ViewLinksTermos(discord.ui.View):
    def __init__(self, guild_id, t_id, r_id):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="📜 Ler Termos", style=discord.ButtonStyle.link, url=f"https://discord.com/channels/{guild_id}/{t_id}"))
        self.add_item(discord.ui.Button(label="📋 Regras", style=discord.ButtonStyle.link, url=f"https://discord.com/channels/{guild_id}/{r_id}"))

def gerar_embed_termos():
    return discord.Embed(title="📜 Termos de Compra", description="Leia os termos antes de prosseguir.", color=0x783296)

class ModalDadosAcesso(discord.ui.Modal, title="🔑 Enviar Dados"):
    email = discord.ui.TextInput(label="Email", required=True)
    senha = discord.ui.TextInput(label="Senha", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("Dados enviados!", ephemeral=True)

class ViewPainelLogin(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="✍️ Preencher Dados", style=discord.ButtonStyle.success, custom_id="btn_preencher_dados")
    async def preencher(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalDadosAcesso())

class ModalGerarPix(discord.ui.Modal, title="👻 Gerar PIX"):
    valor = discord.ui.TextInput(label="Valor (R$)", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Pix de R${self.valor.value} gerado na chave {CHAVE_PIX_PADRAO}")

class ModalCriarSetupCompleto(discord.ui.Modal, title=" Configurar Painel de Tickets"):
    titulo = discord.ui.TextInput(label="Título do Painel", placeholder="Ex: Central de Pedidos", required=True)
    description = discord.ui.TextInput(label="Descrição", style=discord.TextStyle.paragraph, required=True)
    cor_hex = discord.ui.TextInput(label="Cor (Hex)", placeholder="#783296", required=False)
    url_imagem = discord.ui.TextInput(label="URL da Imagem", placeholder="Link da imagem...", required=False)
    def __init__(self, canal):
        super().__init__()
        self.canal = canal
    async def on_submit(self, interaction: discord.Interaction):
        cor = discord.Color(0x783296)
        if self.cor_hex.value:
            try: cor = discord.Color(int(self.cor_hex.value.lstrip('#'), 16))
            except: pass
        embed = discord.Embed(title=self.titulo.value, description=self.description.value, color=cor)
        if self.url_imagem.value: embed.set_image(url=self.url_imagem.value)
        await self.canal.send(embed=embed, view=ViewAbreTicketDinamico())
        await interaction.response.send_message(f"✅ Painel enviado em {self.canal.mention}!", ephemeral=True)

# ==========================================
# 🤖 BOT E COMANDOS
# ==========================================
class HuTaoBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(ViewAbreTicketDinamico())
        self.add_view(ViewBotaoDinamicoGlobal())
        self.add_view(ViewControleTicket())
        self.add_view(ViewPainelLogin())
        await self.tree.sync()

bot = HuTaoBot()

@bot.tree.command(name="setup_panel", description="Cria um painel de tickets")
@app_commands.default_permissions(administrator=True)
async def setup_panel_slash(interaction: discord.Interaction, canal: discord.TextChannel):
    await interaction.response.send_modal(ModalCriarSetupCompleto(canal))

@bot.tree.command(name="pix", description="Gera cobrança PIX")
async def pix(interaction: discord.Interaction): await interaction.response.send_modal(ModalGerarPix())

@bot.tree.command(name="login", description="Solicita dados de acesso")
async def login(interaction: discord.Interaction): await interaction.response.send_message(view=ViewPainelLogin())

@bot.tree.command(name="diferenca", description="Diferença Manual vs Script")
async def diferenca(interaction: discord.Interaction):
    await interaction.response.send_message("• Manual: Seguro.\n• Script: Rápido, mas com risco.")

@bot.tree.command(name="termos", description="Links dos termos")
async def termos(interaction: discord.Interaction):
    await interaction.response.send_message(embed=gerar_embed_termos(), view=ViewLinksTermos(interaction.guild_id, ID_CANAL_TERMOS, ID_CANAL_REGRAS))

@bot.event
async def on_ready():
    print(f"👻 Bot {bot.user.name} online!")

bot.run(os.getenv("DISCORD_TOKEN"))
