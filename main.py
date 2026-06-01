import discord
from discord.ext import commands
from discord import app_commands
import os
import threading
import http.server
import socketserver
import sys

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
# 🤖 CONFIGURAÇÃO DO BOT
# ==========================================
CHAVE_PIX_PADRAO = os.getenv("CHAVE_PIX", "bootaoservices01@gmail.com")

class HuTaoBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Registra as Views de forma persistente para que os botões continuem funcionando mesmo se o bot reiniciar
        self.add_view(ViewAbreTicket())
        self.add_view(ViewPainelSetupPanel())
        self.add_view(ViewPainelCriarEmbed())
        self.add_view(ViewPainelReiniciar())
        self.add_view(ViewBotaoDinamicoPersistente())
        await self.tree.sync()

bot = HuTaoBot()

# ==========================================
# 🎫 SISTEMA DE TICKET (ABRIR E CONFIGURAR)
# ==========================================
class ViewAbreTicket(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🛒 Fazer Pedido", style=discord.ButtonStyle.success, custom_id="btn_abrir_ticket", emoji="🎫")
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

# ==========================================
# 🔘 RECEPTOR DE CLIQUES DOS BOTÕES PERSONALIZADOS
# ==========================================
class ViewBotaoDinamicoPersistente(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        custom_id = interaction.data.get("custom_id", "")
        if custom_id.startswith("msg_custom_"):
            mensagem_para_exibir = custom_id.replace("msg_custom_", "", 1)
            await interaction.response.send_message(mensagem_para_exibir, ephemeral=True)
            return True
        return await super().interaction_check(interaction)

# ==========================================
# 📥 MODAIS ADMINISTRATIVOS (FORMULÁRIOS)
# ==========================================

class ModalEnvioPainelTicket(discord.ui.Modal, title="🛒 Configurar Destino do Painel"):
    id_canal = discord.ui.TextInput(label="ID do Canal de Destino", placeholder="Cole o ID do canal aqui...", required=True)
    url_imagem = discord.ui.TextInput(label="URL da Imagem (Opcional)", placeholder="Cole o link da imagem/banner...", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            canal = interaction.guild.get_channel(int(self.id_canal.value))
            if not canal or not isinstance(canal, discord.TextChannel):
                await interaction.response.send_message("❌ ID de canal inválido ou não é um canal de texto!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ O ID do canal deve conter apenas números!", ephemeral=True)
            return

        embed_ticket = discord.Embed(
            title="🛒 Central de Pedidos — Bootao Services",
            description=(
                "Bem-vindo à nossa loja! Para fazer o seu pedido de forma segura, "
                "clique no botão abaixo para abrir um ticket de atendimento exclusivo.\n\n"
                "⚠️ **Aviso:** Não abra tickets sem a real intenção de compra."
            ),
            color=discord.Color.from_rgb(120, 50, 150)
        )
        
        if self.url_imagem.value:
            embed_ticket.set_image(url=self.url_imagem.value)

        await canal.send(embed=embed_ticket, view=ViewAbreTicket())
        await interaction.response.send_message(f"✅ Painel de Tickets enviado com sucesso em {canal.mention}!", ephemeral=True)


# Passo 2: Configuração física do Botão e da sua resposta efémera
class ModalConfigurarBotaoEmbed(discord.ui.Modal, title="🔘 Passo 2: Configurar o Botão"):
    texto_botao = discord.ui.TextInput(label="Texto exibido no Botão", placeholder="Ex: Ver Informações Extras", max_length=80, required=True)
    resposta_clique = discord.ui.TextInput(label="Mensagem ao Clicar (Apenas ele verá)", style=discord.TextStyle.paragraph, placeholder="Texto que aparece na tela do cliente quando ele aperta o botão...", required=True)

    def __init__(self, canal, embed_pronta):
        super().__init__()
        self.canal = canal
        self.embed_pronta = embed_pronta

    async def on_submit(self, interaction: discord.Interaction):
        view_customizada = discord.ui.View(timeout=None)
        id_customizado = f"msg_custom_{self.resposta_clique.value}"
        
        view_customizada.add_item(discord.ui.Button(
            label=self.texto_botao.value,
            style=discord.ButtonStyle.primary,
            custom_id=id_customizado[:100]
        ))

        await self.canal.send(embed=self.embed_pronta, view=view_customizada)
        await interaction.response.send_message(f"✅ Embed com botão personalizado enviada em {self.canal.mention}!", ephemeral=True)


# Passo 1: Construção visual da Embed (Título, Descrição, Cor e Imagem)
class ModalCriarEmbedPersonalizado(discord.ui.Modal, title="🎨 Passo 1: Criar a Embed"):
    id_canal = discord.ui.TextInput(label="ID do Canal de Destino", placeholder="Ex: 123456789...", required=True)
    titulo = discord.ui.TextInput(label="Título da Embed", placeholder="Ex: 📜 Informações Adicionais", required=True)
    descricao = discord.ui.TextInput(label="Descrição / Texto", style=discord.TextStyle.paragraph, placeholder="Informações do seu serviço aqui...", required=True)
    cor_hex = discord.ui.TextInput(label="Cor da Barra Lateral (Hex)", placeholder="Ex: #783296 ou deixe vazio para Roxo", required=False)
    url_imagem = discord.ui.TextInput(label="URL da Imagem / Banner", placeholder="Cole o link da imagem...", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            canal = interaction.guild.get_channel(int(self.id_canal.value))
            if not canal or not isinstance(canal, discord.TextChannel):
                await interaction.response.send_message("❌ ID de canal inválido ou não é um canal de texto!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ O ID do canal deve conter apenas números!", ephemeral=True)
            return

        cor = discord.Color.from_rgb(120, 50, 150)
        if self.cor_hex.value:
            try:
                hex_limpo = self.cor_hex.value.lstrip('#')
                cor = discord.Color(int(hex_limpo, 16))
            except ValueError:
                pass

        embed_construida = discord.Embed(
            title=self.titulo.value,
            description=self.descricao.value.replace(r'\n', '\n'),
            color=cor
        )

        if self.url_imagem.value:
            embed_construida.set_image(url=self.url_imagem.value)

        # Chama o Passo 2 imediatamente de forma encadeada
        await interaction.response.send_modal(ModalConfigurarBotaoEmbed(canal, embed_construida))


# ==========================================
# 🛠️ CLASSES ISOLADAS DE VIEWS DO MENU ADMIN
# ==========================================

class ViewPainelSetupPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Enviar", style=discord.ButtonStyle.secondary, custom_id="admin_btn_setup_isolated", emoji="▶️")
    async def admin_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Apenas administradores podem usar este painel.", ephemeral=True)
            return
        await interaction.response.send_modal(ModalEnvioPainelTicket())

class ViewPainelCriarEmbed(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Enviar", style=discord.ButtonStyle.secondary, custom_id="admin_btn_embed_isolated", emoji="🎨")
    async def admin_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Apenas administradores podem usar este painel.", ephemeral=True)
            return
        await interaction.response.send_modal(ModalCriarEmbedPersonalizado())

class ViewPainelReiniciar(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Enviar", style=discord.ButtonStyle.secondary, custom_id="admin_btn_reiniciar_isolated", emoji="🔄")
    async def admin_reiniciar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Apenas administradores podem usar este painel.", ephemeral=True)
            return
        
        await interaction.response.send_message("🔄 Reiniciando o bot de forma segura...", ephemeral=True)
        print("🚨 Bot desligado via Painel de Controle Admin. Reiniciando...")
        await bot.close()
        sys.exit(0)


# ==========================================
# 🛑 GERADOR DO MENU DE CONTROLE ADMIN (PREFIXO)
# ==========================================
@bot.command(name="painel_admin")
@commands.has_permissions(administrator=True)
async def criar_painel_admin(ctx):
    await ctx.message.delete()
    
    # 1. Linha do Setup Painel
    embed_setup = discord.Embed(
        title="**setup_panel**",
        description="Posta o painel de tickets em qualquer canal de texto (admin)",
        color=discord.Color.from_rgb(30, 30, 30)
    )
    await ctx.send(embed=embed_setup, view=ViewPainelSetupPanel())

    # 2. Linha do Criador de Embeds Customizados com Botão
    embed_personalizado = discord.Embed(
        title="**criar_embed**",
        description="Cria uma embed totalmente customizada com imagem, cor e botão secreto de resposta (admin)",
        color=discord.Color.from_rgb(30, 30, 30)
    )
    await ctx.send(embed=embed_personalizado, view=ViewPainelCriarEmbed())

    # 3. Linha de Reiniciar o Bot
    embed_reiniciar = discord.Embed(
        title="**reiniciar**",
        description="Reinicia o bot (admin)",
        color=discord.Color.from_rgb(30, 30, 30)
    )
    await ctx.send(embed=embed_reiniciar, view=ViewPainelReiniciar())


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


# --- Comandos de barra normais para os clientes/atendimentos ---
@bot.tree.command(name="criar_embed", description="Cria uma embed totalmente customizada com um botão e resposta efémera")
@app_commands.default_permissions(administrator=True)
async def criar_embed_slash(interaction: discord.Interaction):
    # Permite abrir o criador de embeds diretamente digitando /criar_embed no Discord
    await interaction.response.send_modal(ModalCriarEmbedPersonalizado())

@bot.tree.command(name="setup_panel", description="Posta o painel de tickets em qualquer canal de texto")
@app_commands.default_permissions(administrator=True)
async def setup_panel_slash(interaction: discord.Interaction):
    await interaction.response.send_modal(ModalEnvioPainelTicket())

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
    print(f"👻 Bot {bot.user.name} está online no Render!")

bot.run(os.getenv("DISCORD_TOKEN"))
