import discord
from discord.ext import commands
from discord import app_commands
import os
import threading
import http.server
import socketserver

# ==========================================
# ⚙️ CONFIGURAÇÕES DA LOJA (COLOQUE SEUS IDs AQUI)
# ==========================================
ID_CANAL_TERMOS = 1457188949364707421  # Substitua pelo ID do canal de termos
ID_CANAL_REGRAS = 1457183013807853764  # Substitua pelo ID do canal de regras

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

# Inicia o servidor web em uma linha separada para não travar o bot
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
        await self.tree.sync()

bot = HuTaoBot()

# ==========================================
# 📜 VIEW DOS BOTÕES DE LINK (TERMOS E REGRAS)
# ==========================================
class ViewLinksTermos(discord.ui.View):
    def __init__(self, guild_id: int, channel_termos_id: int, channel_regras_id: int):
        super().__init__(timeout=None)
        # Cria os links diretos para cada canal correspondente
        url_termos = f"https://discord.com/channels/{guild_id}/{channel_termos_id}"
        url_regras = f"https://discord.com/channels/{guild_id}/{channel_regras_id}"
        
        # Adiciona os botões de URL que redirecionam o usuário
        self.add_item(discord.ui.Button(label="📜 Ler Termos de Compra", style=discord.ButtonStyle.link, url=url_termos))
        self.add_item(discord.ui.Button(label="📋 Ver Regras", style=discord.ButtonStyle.link, url=url_regras))

# ==========================================
# 🔑 MODAL E FLUXO DE ENVIO DE DADOS DE ACESSO
# ==========================================
class ModalDadosAcesso(discord.ui.Modal, title="🔑 Enviar Dados de Acesso"):
    email = discord.ui.TextInput(label="Email (completo)", placeholder="Ex: seuemail@gmail.com")
    senha = discord.ui.TextInput(label="Senha (completa)", placeholder="Ex: suasenha123")
    servidor = discord.ui.TextInput(label="Servidor", placeholder="Ex: america/europa..")
    metodo = discord.ui.TextInput(label="Método de Login", placeholder="Ex: direto no jogo/google")

    async def on_submit(self, interaction: discord.Interaction):
        # 1. Cria a Embed com as credenciais recebidas
        embed_recebido = discord.Embed(
            title="🔑 Dados de Acesso Recebidos",
            color=discord.Color.from_rgb(120, 50, 150)
        )
        embed_recebido.add_field(name="📩 Email", value=f"`{self.email.value}`", inline=False)
        embed_recebido.add_field(name="🔒 Senha", value=f"`{self.senha.value}`", inline=False)
        embed_recebido.add_field(name="🌐 Servidor", value=f"`{self.servidor.value}`", inline=True)
        embed_recebido.add_field(name="🔗 Método de Login", value=f"`{self.metodo.value}`", inline=True)
        embed_recebido.set_footer(text=f"Enviado por {interaction.user.name} 🌸")

        # 2. Deleta o painel antigo de solicitação
        await interaction.message.delete()
        
        # 3. Envia os dados enviados no canal
        await interaction.response.send_message(embed=embed_recebido)

        # 4. Cria a Embed de Termos da Bootao Services
        embed_termos = discord.Embed(
            title="📜 Termos de Compra — Bootao Services",
            description=(
                "• **Dados recebidos com sucesso!** ✨\n"
                "Antes de começarmos, por favor leia nossos termos de compra.\n\n"
                "Isso evita qualquer mal entendido durante o atendimento ❤️"
            ),
            color=discord.Color.from_rgb(120, 50, 150)
        )
        
        # 5. Envia a mensagem de termos com os links configurados de forma independente
        view_links = ViewLinksTermos(interaction.guild_id, ID_CANAL_TERMOS, ID_CANAL_REGRAS)
        await interaction.followup.send(embed=embed_termos, view=view_links)

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

# ==========================================
# 🛑 COMANDOS DO BOT
# ==========================================
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
        "pois o script não está em um estado 100% seguro, mas se a pessoa não tem historico de banimento, o máximo "
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
    await interaction.response.send_message("⚖️ Ao comprar, você aceita as diretrizes de serviço da Bootao Services.")

@bot.event
async def on_ready():
    print(f"👻 Bot {bot.user.name} está online no Render!")

bot.run(os.getenv("DISCORD_TOKEN"))
