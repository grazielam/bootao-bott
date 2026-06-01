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
# ⚙️ CONFIGURAÇÕES DA LOJA (IDs ATUALIZADOS)
# ==========================================
ID_CANAL_TERMOS = 1457188949364707421  
ID_CANAL_REGRAS = 1457183013807853764  
ID_CATEGORIA_TICKETS = 1468070452655034499  
ID_CARGO_ATENDENTES = 1422264212817838132  

# ==========================================
# 🌐 SERVIDOR WEB PARA MANTER O BOT ACORDADO
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
        print(f"Servidor Web ativo na porta {port}")
        httpd.serve_forever()

threading.Thread(target=rodar_servidor_web, daemon=True).start()

# ==========================================
# 🗄️ BANCO DE DADOS PERSISTENTE (SQLITE)
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
    conn.commit()
    conn.close()

inicializar_banco()

def salvar_embed_no_banco(titulo_chave, titulo_resposta, texto_resposta, imagem_resposta, cor_int):
    conn = sqlite3.connect("dados_loja.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO embeds_personalizados (titulo_chave, titulo_resposta, texto_resposta, imagem_resposta, cor_int)
        VALUES (?, ?, ?, ?, ?)
    """, (titulo_chave, titulo_resposta, texto_resposta, imagem_resposta, cor_int))
    conn.commit()
    conn.close()

def puxar_embed_do_banco(titulo_chave):
    conn = sqlite3.connect("dados_loja.db")
    cursor = conn.cursor()
    cursor.execute("SELECT titulo_resposta, texto_resposta, imagem_resposta, cor_int FROM embeds_personalizados WHERE titulo_chave = ?", (titulo_chave,))
    resultado = cursor.fetchone()
    conn.close()
    if resultado:
        return {
            "titulo_resposta": resultado[0],
            "texto_resposta": resultado[1],
            "imagem_resposta": resultado[2],
            "cor_int": resultado[3]
        }
    return None

# ==========================================
# 🤖 CONFIGURAÇÃO DO BOT E VIEWS GLOBAIS
# ==========================================
CHAVE_PIX_PADRAO = os.getenv("CHAVE_PIX", "bootaoservices01@gmail.com")

class ViewBotaoDinamicoGlobal(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Visualizar Informações", style=discord.ButtonStyle.primary, custom_id="btn_global_visualizar_info")
    async def responder_clique_dinamico(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.message.embeds:
            await interaction.response.send_message("❌ Erro: Não foi possível identificar a embed deste painel.", ephemeral=True)
            return

        titulo_painel = interaction.message.embeds[0].title
        dados_guardados = puxar_embed_do_banco(titulo_painel)
        
        if dados_guardados:
            titulo_res = dados_guardados.get("titulo_resposta", "Informações")
            texto_original = dados_guardados.get("texto_resposta", "")
            img_rodape_url = dados_guardados.get("imagem_resposta", "")
            cor_int = dados_guardados.get("cor_int", 7877270)
            cor = discord.Color(cor_int)
            
            regex_imagens = r'(https?://\S+\.(?:png|jpg|jpeg|gif|webp))'
            links_encontrados = re.findall(regex_imagens, texto_original, re.IGNORECASE)
            texto_limpo = re.sub(regex_imagens, '', texto_original).strip()
            
            lista_embeds = []
            embed_texto = discord.Embed(title=titulo_res, description=texto_limpo if texto_limpo else "Visualizar Imagens anexadas:", color=cor)
            
            if img_rodape_url:
                embed_texto.set_image(url=img_rodape_url)
                lista_embeds.append(embed_texto)
            else:
                if links_encontrados:
                    embed_texto.set_image(url=links_encontrados.pop(0))
                lista_embeds.append(embed_texto)
            
            for link_img in links_encontrados[:9]:
                embed_extra = discord.Embed(color=cor)
                embed_extra.set_image(url=link_img)
                lista_embeds.append(embed_extra)
            
            await interaction.response.send_message(embeds=lista_embeds, ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Nenhuma configuração encontrada no banco de dados.", ephemeral=True)

class ModalFormularioTicket(discord.ui.Modal, title="🛒 Detalhes do Atendimento"):
    produto = discord.ui.TextInput(label="Qual produto você deseja?", placeholder="ex: Farm de resina, Exploração 100%, Build...", required=True)
    metodo = discord.ui.TextInput(label="Método de farm?", placeholder="Manual ou Script", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        categoria = discord.utils.get(guild.categories, id=ID_CATEGORIA_TICKETS)
        nome_canal = f"🛒-{interaction.user.name}"
        
        canal_existente = discord.utils.get(guild.text_channels, name=nome_canal.lower())
        if canal_existente:
            await interaction.response.send_message(f"❌ Você já possui um ticket aberto em {canal_existente.mention}!", ephemeral=True)
            return

        permissoes = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        cargo_suporte = guild.get_role(ID_CARGO_ATENDENTES)
        if cargo_suporte:
            permissoes[cargo_suporte] = discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True)

        canal_ticket = await guild.create_text_channel(name=nome_canal, category=categoria, overwrites=permissoes)
        await interaction.response.send_message(f"✅ Ticket criado: {canal_ticket.mention}!", ephemeral=True)

        embed_detalhes = discord.Embed(
            title="⚠️ Detalhes do Atendimento",
            description=f"**qual produto vc deseja?**\n{self.produto.value}\n\n**método de farm?**\n{self.metodo.value}\n\n👤 **Criado por**\n{interaction.user.name}",
            color=discord.Color(int("c8131e", 16))
        )
        embed_detalhes.set_footer(text="Bootao Services • aguardando atendimento 🌸")
        await canal_ticket.send(content=f"{interaction.user.mention} <@&{ID_CARGO_ATENDENTES}>", embed=embed_detalhes)

class ViewAbreTicketDinamico(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🛒 Fazer Pedido", style=discord.ButtonStyle.success, custom_id="btn_abrir_ticket_dinamico", emoji="🎫")
    async def abrir_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalFormularioTicket())

class HuTaoBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.tree.clear_commands(guild=None) # LIMPA COMANDOS ANTIGOS DO DISCORD
        self.add_view(ViewAbreTicketDinamico())
        self.add_view(ViewPainelLogin())
        self.add_view(ViewBotaoDinamicoGlobal())
        await self.tree.sync() 

bot = HuTaoBot()

# ==========================================
# 📥 COMANDOS DE BARRA (SLASH COMMANDS)
# ==========================================

@bot.tree.command(name="fechar_ticket", description="Fecha o canal de atendimento atual")
@app_commands.default_permissions(manage_channels=True)
async def fechar_ticket(interaction: discord.Interaction):
    await interaction.response.send_message("⏳ Deletando canal em 5 segundos...")
    await asyncio.sleep(5)
    await interaction.channel.delete()

@bot.tree.command(name="setup_panel", description="Cria um painel de tickets")
@app_commands.describe(canal="Canal de envio")
@app_commands.default_permissions(administrator=True)
async def setup_panel_slash(interaction: discord.Interaction, canal: discord.TextChannel):
    class ModalSetup(discord.ui.Modal, title="Configurar Painel"):
        titulo = discord.ui.TextInput(label="Título", required=True)
        desc = discord.ui.TextInput(label="Descrição", style=discord.TextStyle.paragraph, required=True)
        img = discord.ui.TextInput(label="URL Imagem", required=False)
        async def on_submit(self, it: discord.Interaction):
            cor = discord.Color.from_rgb(120, 50, 150)
            emb = discord.Embed(title=self.titulo.value, description=self.desc.value, color=cor)
            if self.img.value: emb.set_image(url=self.img.value)
            await canal.send(embed=emb, view=ViewAbreTicketDinamico())
            await it.response.send_message("✅ Painel Enviado!", ephemeral=True)
    await interaction.response.send_modal(ModalSetup())

@bot.tree.command(name="criar_embed", description="Cria uma embed com resposta de imagem")
@app_commands.describe(canal="Destino", cor_hex="Ex: #783296", img_principal="Link da imagem principal")
@app_commands.default_permissions(administrator=True)
async def criar_embed_slash(interaction: discord.Interaction, canal: discord.TextChannel, cor_hex: str = None, img_principal: str = None):
    class ModalEmbed(discord.ui.Modal, title="🎨 Criar Embed"):
        titulo = discord.ui.TextInput(label="Título Principal", required=True)
        desc = discord.ui.TextInput(label="Texto Principal", style=discord.TextStyle.paragraph, required=True)
        btn = discord.ui.TextInput(label="Texto do Botão", required=True)
        res = discord.ui.TextInput(label="Resposta (Texto + Links)", style=discord.TextStyle.paragraph, required=True)
        img_res = discord.ui.TextInput(label="URL Imagem Resposta", required=False)
        async def on_submit(self, it: discord.Interaction):
            cor = discord.Color.from_str(cor_hex) if cor_hex else discord.Color.blue()
            emb = discord.Embed(title=self.titulo.value, description=self.desc.value, color=cor)
            if img_principal: emb.set_image(url=img_principal)
            salvar_embed_no_banco(self.titulo.value, self.titulo.value, self.res.value, self.img_res.value, cor.value)
            v = ViewBotaoDinamicoGlobal()
            v.children[0].label = self.btn.value
            await canal.send(embed=emb, view=v)
            await it.response.send_message("✅ Embed Criada!", ephemeral=True)
    await interaction.response.send_modal(ModalEmbed())

@bot.tree.command(name="reiniciar", description="Reinicia o bot")
@app_commands.default_permissions(administrator=True)
async def reiniciar_slash(interaction: discord.Interaction):
    await interaction.response.send_message("🔄 Reiniciando...", ephemeral=True)
    await bot.close()
    sys.exit(0)

@bot.tree.command(name="pix", description="Gera cobrança PIX")
async def pix(interaction: discord.Interaction):
    class ModalPix(discord.ui.Modal, title="Gerar PIX"):
        val = discord.ui.TextInput(label="Valor (R$)", placeholder="50")
        async def on_submit(self, it: discord.Interaction):
            emb = discord.Embed(title="Pagamento PIX", description=f"💲 **Valor:** R$ {self.val.value}\n**Chave:** `{CHAVE_PIX_PADRAO}`", color=discord.Color.dark_grey())
            await it.response.send_message(embed=emb, view=ViewPainelPix(CHAVE_PIX_PADRAO))
    await interaction.response.send_modal(ModalPix())

@bot.tree.command(name="login", description="Solicita dados de acesso")
async def login(interaction: discord.Interaction):
    emb = discord.Embed(title="🔑 Dados para Acesso", description="Clique no botão abaixo para preencher seus dados de acesso.", color=discord.Color.from_rgb(120, 50, 150))
    await interaction.response.send_message(embed=emb, view=ViewPainelLogin())

@bot.tree.command(name="diferenca", description="Diferença entre Manual e Script")
async def diferenca(interaction: discord.Interaction):
    await interaction.response.send_message("• **Manual:** 100% seguro, feito à mão.\n• **Script:** Mais rápido, mas possui riscos de ban.")

@bot.tree.command(name="termos", description="Links dos termos")
async def termos(interaction: discord.Interaction):
    emb = discord.Embed(title="📜 Termos de Compra", description="Leia nossos termos nos canais oficiais.", color=discord.Color.from_rgb(120, 50, 150))
    v = discord.ui.View()
    v.add_item(discord.ui.Button(label="Termos", url=f"https://discord.com/channels/{interaction.guild_id}/{ID_CANAL_TERMOS}"))
    v.add_item(discord.ui.Button(label="Regras", url=f"https://discord.com/channels/{interaction.guild_id}/{ID_CANAL_REGRAS}"))
    await interaction.response.send_message(embed=emb, view=v)

# ==========================================
# 🔘 VIEWS DE LOGIN E PIX
# ==========================================
class ViewPainelLogin(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="✍️ Preencher Dados", style=discord.ButtonStyle.success, custom_id="btn_preencher_dados")
    async def preencher(self, it: discord.Interaction, b: discord.ui.Button):
        class ModalDados(discord.ui.Modal, title="Enviar Dados"):
            e = discord.ui.TextInput(label="Email")
            s = discord.ui.TextInput(label="Senha")
            async def on_submit(self, it2: discord.Interaction):
                emb = discord.Embed(title="🔑 Dados Recebidos", color=discord.Color.green())
                emb.add_field(name="Email", value=it2.user.mention)
                await it2.channel.send(embed=emb)
                await it2.response.send_message("Dados enviados!", ephemeral=True)
        await it.response.send_modal(ModalDados())

class ViewPainelPix(discord.ui.View):
    def __init__(self, chave): 
        super().__init__(timeout=None)
        self.chave = chave
    @discord.ui.button(label="Chave Pix", style=discord.ButtonStyle.primary)
    async def copiar(self, it: discord.Interaction, b: discord.ui.Button):
        await it.response.send_message(self.chave, ephemeral=True)

@bot.event
async def on_ready():
    print(f"👻 Bot {bot.user.name} pronto! Comandos removidos.")

bot.run(os.getenv("DISCORD_TOKEN"))
