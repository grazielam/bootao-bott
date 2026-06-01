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

# ==========================================
# ⚙️ CONFIGURAÇÕES DA LOJA (COLOQUE SEUS IDs AQUI)
# ==========================================
ID_CANAL_TERMOS = 1457188949364707421  # Substitua pelo ID do canal de termos 
ID_CANAL_REGRAS = 1457183013807853764  # Substitua pelo ID do canal de regras 
ID_CATEGORIA_TICKETS = 1468070452655034499  # Substitua pelo ID da categoria onde os tickets serão abertos 

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
    # Mudamos a chave primária para o título da embed principal para associar corretamente o clique
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
SETUP_TEMPORARIO_PARAMETROS = {}

# 🔘 NOVA VIEW GLOBAL PARA OS BOTÕES PERSONALIZADOS
class ViewBotaoDinamicoGlobal(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Visualizar Informações", style=discord.ButtonStyle.primary, custom_id="btn_global_visualizar_info")
    async def responder_clique_dinamico(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Identifica qual painel foi clicado usando o título da embed que contém o botão
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
            
            embed_texto = discord.Embed(
                title=titulo_res,
                description=texto_limpo if texto_limpo else "Visualizar Imagens anexadas:",
                color=cor
            )
            
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
            await interaction.response.send_message(f"❌ Nenhuma configuração encontrada para o painel: **{titulo_painel}**.", ephemeral=True)


class ViewAbreTicketDinamico(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🛒 Fazer Pedido", style=discord.ButtonStyle.success, custom_id="btn_abrir_ticket_dinamico", emoji="🎫")
    async def abrir_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
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

        canal_ticket = await guild.create_text_channel(
            name=nome_canal,
            category=categoria,
            overwrites=permissoes,
            topic=f"Ticket de {interaction.user.mention} para realizar um pedido."
        )

        await interaction.response.send_message(f"✅ Seu ticket foi criado com sucesso em {canal_ticket.mention}!", ephemeral=True)

        embed_boas_vindas = discord.Embed(
            title="🌸 Bem-vindo à Bootao Services!",
            description=(
                f"Olá {interaction.user.mention},\n"
                "A Staff foi notificada e logo iniciará o seu atendimento!\n\n"
                "Para agilizar o processo, você já pode utilizar o comando `/pix` para realizar o seu pagamento."
            ),
            color=discord.Color.from_rgb(120, 50, 150)
        )
        await canal_ticket.send(embed=embed_boas_vindas)


class HuTaoBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Aqui registramos as Views persistentes globais do Bot.
        # Elas NUNCA vão falhar após o bot reiniciar porque os seus IDs internos são fixos!
        self.add_view(ViewAbreTicketDinamico())
        self.add_view(ViewPainelLogin())
        self.add_view(ViewBotaoDinamicoGlobal())
        await self.tree.sync()

bot = HuTaoBot()

# ==========================================
# 📥 FORMULÁRIOS DE CONFIGURAÇÃO INTERATIVOS
# ==========================================

class ModalCriarSetupCompleto(discord.ui.Modal, title="🛒 Configurar Painel de Tickets"):
    titulo = discord.ui.TextInput(label="Título do Painel", placeholder="Ex: 🛒 Central de Pedidos", required=True)
    description = discord.ui.TextInput(label="Descrição / Texto", style=discord.TextStyle.paragraph, placeholder="Escreva as regras/boas-vindas do seu ticket aqui...", required=True)
    cor_hex = discord.ui.TextInput(label="Cor da Barra Lateral (Hex)", placeholder="Ex: #783296", required=False)
    url_imagem = discord.ui.TextInput(label="URL da Imagem / Banner (Opcional)", placeholder="Cole o link da imagem...", required=False)

    def __init__(self, canal):
        super().__init__()
        self.canal = canal

    async def on_submit(self, interaction: discord.Interaction):
        cor = discord.Color.from_rgb(120, 50, 150)
        if self.cor_hex.value:
            try:
                hex_limpo = self.cor_hex.value.lstrip('#')
                cor = discord.Color(int(hex_limpo, 16))
            except ValueError:
                pass

        embed_construida = discord.Embed(
            title=self.titulo.value,
            description=self.description.value.replace(r'\n', '\n'),
            color=cor
        )

        if self.url_imagem.value:
            embed_construida.set_image(url=self.url_imagem.value)

        await self.canal.send(embed=embed_construida, view=ViewAbreTicketDinamico())
        await interaction.response.send_message(f"✅ Painel de Tickets enviado com sucesso em {self.canal.mention}!", ephemeral=True)


class ModalCriarEmbedCompleto(discord.ui.Modal, title="🎨 Criar Embed Personalizada"):
    titulo = discord.ui.TextInput(label="Título da Embed Principal", placeholder="Ex: 📜 Tabela de Valores", required=True)
    description = discord.ui.TextInput(label="Descrição / Texto da Embed Principal", style=discord.TextStyle.paragraph, placeholder="Clique no botão abaixo e veja nossos valores...", required=True)
    texto_botao = discord.ui.TextInput(label="Texto do Botão Informativo", placeholder="Ex: 👻 Valores", max_length=50, required=True)
    resposta_clique = discord.ui.TextInput(label="Texto da Resposta (Ao clicar)", style=discord.TextStyle.paragraph, placeholder="Escreva seu texto e links de imagens direto aqui!", required=True)
    url_imagem_resposta = discord.ui.TextInput(label="URL da Imagem da Resposta (Opcional)", placeholder="Cole um link de imagem que aparece ao clicar...", required=False)

    def __init__(self, token_referencia: str):
        super().__init__()
        self.token_referencia = token_referencia

    async def on_submit(self, interaction: discord.Interaction):
        parametros = SETUP_TEMPORARIO_PARAMETROS.get(self.token_referencia, {})
        canal = parametros.get("canal")
        cor_hex = parametros.get("cor_hex")
        url_imagem_principal = parametros.get("url_imagem_principal")

        if not canal:
            await interaction.response.send_message("❌ Houve um erro de sessão. Tente usar o comando novamente.", ephemeral=True)
            return

        cor = discord.Color.from_rgb(120, 50, 150)
        if cor_hex:
            try:
                hex_limpo = cor_hex.lstrip('#')
                cor = discord.Color(int(hex_limpo, 16))
            except ValueError:
                pass

        embed_construida = discord.Embed(
            title=self.titulo.value,
            description=self.description.value.replace(r'\n', '\n'),
            color=cor
        )

        if url_imagem_principal:
            embed_construida.set_image(url=url_imagem_principal)

        # Salva as informações da resposta usando o TÍTULO PRINCIPAL como chave única de busca
        salvar_embed_no_banco(
            titulo_chave=self.titulo.value,
            titulo_resposta=self.titulo.value,
            texto_resposta=self.resposta_clique.value.replace(r'\n', '\n'),
            imagem_resposta=self.url_imagem_resposta.value if self.url_imagem_resposta.value else None,
            cor_int=cor.value
        )

        # Criamos a View Global e alteramos dinamicamente apenas o texto (Label) do botão para o que você escolheu
        view_global = ViewBotaoDinamicoGlobal()
        view_global.children[0].label = self.texto_botao.value

        await canal.send(embed=embed_construida, view=view_global)
        await interaction.response.send_message(f"✅ Embed personalizada enviada com sucesso em {canal.mention}!", ephemeral=True)
        
        # Limpa cache temporário
        SETUP_TEMPORARIO_PARAMETROS.pop(self.token_referencia, None)


# ==========================================
# 👑 COMANDOS DE BARRA ADMINISTRATIVOS
# ==========================================

@bot.tree.command(name="setup_panel", description="Cria e envia um painel de tickets 100% customizável")
@app_commands.describe(canal="Selecione o canal onde o painel de tickets será enviado")
@app_commands.default_permissions(administrator=True)
async def setup_panel_slash(interaction: discord.Interaction, canal: discord.TextChannel):
    await interaction.response.send_modal(ModalCriarSetupCompleto(canal))

@bot.tree.command(name="criar_embed", description="Cria uma embed totalmente customizada com imagem e botão informativo")
@app_commands.describe(
    canal="Canal de destino", 
    cor_hex="Cor lateral em Hex (Ex: #783296)", 
    url_imagem_principal="Link da imagem/banner da embed principal (Opcional)"
)
@app_commands.default_permissions(administrator=True)
async def criar_embed_slash(
    interaction: discord.Interaction, 
    canal: discord.TextChannel, 
    cor_hex: str = None, 
    url_imagem_principal: str = None
):
    token_id = str(interaction.id)
    SETUP_TEMPORARIO_PARAMETROS[token_id] = {
        "canal": canal,
        "cor_hex": cor_hex,
        "url_imagem_principal": url_imagem_principal
    }
    await interaction.response.send_modal(ModalCriarEmbedCompleto(token_id))

@bot.tree.command(name="reiniciar", description="Reinicia o bot de forma limpa e segura")
@app_commands.default_permissions(administrator=True)
async def reiniciar_slash(interaction: discord.Interaction):
    await interaction.response.send_message("🔄 Reiniciando o bot de forma segura...", ephemeral=True)
    await bot.close()
    sys.exit(0)


# ==========================================
# 📜 VIEW DOS BOTÕES DE LINK (TERMOS E REGRAS)
# ==========================================
class ViewLinksTermos(discord.ui.View):
    def __init__(self, guild_id: int, channel_termos_id: int, channel_regras_id: int):
        super().__init__(timeout=None)
        url_termos = f"https://discord.com/channels/{guild_id}/{channel_termos_id}"
        url_regras = f"https://discord.com/channels/{guild_id}/{channel_regras_id}"
        
        self.add_item(discord.ui.Button(label="📜 Ler Termos de Compra", style=discord.ButtonStyle.link, url=url_termos))
        self.add_item(discord.ui.Button(label="📋 Ver Regras", style=discord.ButtonStyle.link, url=url_regras))

def gerar_embed_termos():
    return discord.Embed(
        title="📜 Termos de Compra — Bootao Services",
        description=(
            "• **Dados recebidos com sucesso!** ✨\n"
            "Antes de começarmos, por favor leia nossos termos de compra.\n\n"
            "Isso evita qualquer mal entendido durante o atendimento ❤️"
        ),
        color=discord.Color.from_rgb(120, 50, 150)
    )

# ==========================================
# 🔑 MODAL E FLUXO DE ENVIO DE DADOS DE ACESSO
# ==========================================
class ModalDadosAcesso(discord.ui.Modal, title="🔑 Enviar Dados de Acesso"):
    email = discord.ui.TextInput(label="Email (completo)", placeholder="Ex: seuemail@gmail.com")
    senha = discord.ui.TextInput(label="Senha (completa)", placeholder="Ex: suasenha123")
    servidor = discord.ui.TextInput(label="Servidor", placeholder="Ex: america/europa..")
    metodo = discord.ui.TextInput(label="Método de Login", placeholder="Ex: direto no jogo/google")

    async def on_submit(self, interaction: discord.Interaction):
        mensagem_painel = interaction.message

        embed_termos = gerar_embed_termos()
        view_links = ViewLinksTermos(interaction.guild_id, ID_CANAL_TERMOS, ID_CANAL_REGRAS)
        await interaction.response.send_message(embed=embed_termos, view=view_links)

        embed_recebido = discord.Embed(
            title="🔑 Dados de Acesso Recebidos",
            color=discord.Color.from_rgb(120, 50, 150)
        )
        embed_recebido.add_field(name="📩 Email", value=f"`{self.email.value}`", inline=False)
        embed_recebido.add_field(name="🔒 Senha", value=f"`{self.senha.value}`", inline=False)
        embed_recebido.add_field(name="🌐 Servidor", value=f"`{self.servidor.value}`", inline=True)
        embed_recebido.add_field(name="🔗 Método de Login", value=f"`{self.metodo.value}`", inline=True)
        embed_recebido.set_footer(text=f"Enviado por {interaction.user.name} 🌸")

        await interaction.channel.send(embed=embed_recebido)

        if mensagem_painel:
            try:
                await mensagem_painel.delete()
            except discord.NotFound:
                pass

class ViewPainelLogin(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✍️ Preencher Dados de Acesso", style=discord.ButtonStyle.success, custom_id="btn_preencher_dados")
    async def preencher_dados(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalDadosAcesso())

# ==========================================
# ⚡ PAINEL DE PAGAMENTO (PIX)
# ==========================================
class ViewPainelPix(discord.ui.View):
    def __init__(self, chave_pix: str):
        super().__init__(timeout=None)
        self.chave_pix = chave_pix

    @discord.ui.button(label="🔑 Chave Pix", style=discord.ButtonStyle.primary, custom_id="btn_copiar_pix")
    async def copiar_pix(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"{self.chave_pix}", ephemeral=True)

    @discord.ui.button(label="【 ✓ Confirmar 】", style=discord.ButtonStyle.success, custom_id="btn_confirmar_pagamento")
    async def confirmar_pagamento(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ Apenas a Staff pode confirmar este pagamento!", ephemeral=True)
            return

        for item in self.children:
            item.disabled = True
        
        embed_login = discord.Embed(
            title="🔑 Dados para Acesso",
            description=(
                "📋 • **Precisamos das suas informações de acesso!**\n"
                "Por favor, clique no botão abaixo e preencha os dados:\n\n"
                "✦ **Email** *(completo)*\n"
                "✦ **Senha** *(completa)*\n"
                "✦ **Servidor** *(ex: América / Europa)*\n"
                "✦ **Método de Login** *(ex: Direto no jogo / Google)*"
            ),
            color=discord.Color.from_rgb(120, 50, 150)
        )
        
        await interaction.message.edit(view=self)
        await interaction.response.send_message(embed=embed_login, view=ViewPainelLogin())

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.danger, custom_id="btn_cancelar_pagamento")
    async def cancelar_pagamento(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ Apenas a Staff pode cancelar esta cobrança!", ephemeral=True)
            return
        
        await interaction.message.delete()
        await interaction.response.send_message("🚨 Cobrança PIX cancelada pela Staff.", ephemeral=True)

class ModalGerarPix(discord.ui.Modal, title="👻 Gerar Cobrança PIX"):
    valor = discord.ui.TextInput(label="Valor da cobrança (R$)", placeholder="Ex: 50")

    async def on_submit(self, interaction: discord.Interaction):
        embed_pix = discord.Embed(
            title="Sistema de pagamento",
            description=(
                "Escolha a forma de pagamento\n\n"
                "💲 **Valor:**\n"
                f"**R$ {self.valor.value}**\n\n"
                "🔷 **Chave Pix:**\n"
                f"`{CHAVE_PIX_PADRAO}`\n\n"
                "Bootao Services 🌹"
            ),
            color=discord.Color.from_rgb(20, 20, 20)
        )
        await interaction.response.send_message(embed=embed_pix, view=ViewPainelPix(CHAVE_PIX_PADRAO))


# --- Restante dos comandos normais ---

@bot.tree.command(name="fechar_ticket", description="Fecha o canal")
@app_commands.default_permissions(manage_channels=True)
async def fechar_ticket(interaction: discord.Interaction):
    await interaction.response.send_message("Trancando ticket...")
    await interaction.channel.delete(delay=5)

@bot.tree.command(name="pix", description="Gera cobrança PIX")
async def pix(interaction: discord.Interaction):
    await interaction.response.send_modal(ModalGerarPix())

@bot.tree.command(name="login", description="Solicita os dados de acesso")
async def login(interaction: discord.Interaction):
    embed_login = discord.Embed(
        title="🔑 Dados para Acesso",
        description=(
            "📋 • **Precisamos das suas informações de acesso!**\n"
            "Por favor, clique no botão abaixo e preencha os dados:\n\n"
            "✦ **Email** *(completo)*\n"
            "✦ **Senha** *(completa)*\n"
            "✦ **Servidor** *(ex: América / Europa)*\n"
            "✦ **Método de Login** *(ex: Direto no jogo / Google)*"
        ),
        color=discord.Color.from_rgb(120, 50, 150)
    )
    await interaction.response.send_message(embed=embed_login, view=ViewPainelLogin())

@bot.tree.command(name="diferenca", description="Diferença entre Manual e Script")
async def diferenca(interaction: discord.Interaction):
    texto_diferenca = (
        "• **Manual:** tudo é feito na mão, 100% seguro!, o prazo de entrega costuma ser maior.\n"
        "• **Script:** usamos programas para agilizar o farm, então o prazo de entrega é menor + tem risco sim, "
        "pois o script não está em um estado 100% seguro, mas se a pessoa não tem historico de farm antigo, o máximo "
        "que pode acontecer é o ban de uma semana, se já tiver levado ban duas vezes é ban de 1 mês se for o terceiro "
        "é ban de 50 anos (ban permanente)"
    )
    await interaction.response.send_message(texto_diferenca)

@bot.tree.command(name="builds", description="Tipos de build")
async def builds(interaction: discord.Interaction):
    await interaction.response.send_message("🛠️ Builds de Dano Crítico, Suporte e Farm cadastrados!")

@bot.tree.command(name="feedback", description="Pede a avaliação")
async def feedback(interaction: discord.Interaction):
    await interaction.response.send_message("🦋 Deixe sua avaliação de 🌟 a 🌟🌟🌟🌟🌟!")

@bot.tree.command(name="genshin", description="Tabela de preços")
async def genshin(interaction: discord.Interaction):
    await interaction.response.send_message("📜 **Tabela Genshin Impact:**\n• 160 Gemas: R$ 2,00\n• 3200 Gemas: R$ 24,00")

@bot.tree.command(name="termos", description="Links dos termos")
async def termos(interaction: discord.Interaction):
    embed_termos = gerar_embed_termos()
    view_links = ViewLinksTermos(interaction.guild_id, ID_CANAL_TERMOS, ID_CANAL_REGRAS)
    await interaction.response.send_message(embed=embed_termos, view=view_links)

@bot.event
async def on_ready():
    print(f"👻 Bot {bot.user.name} está online com Views Globais e Persistência Ativa!")

bot.run(os.getenv("DISCORD_TOKEN"))
