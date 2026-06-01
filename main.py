import discord
from discord.ext import commands
from discord import app_commands
import os
import threading
import http.server
import socketserver

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
# 🔑 MODAL E FLUXO DE ENVIO DE DADOS DE ACESSO
# ==========================================
class ModalDadosAcesso(discord.ui.Modal, title="🔑 Enviar Dados de Acesso"):
    email = discord.ui.TextInput(label="Email (completo)", placeholder="Ex: ceciliandrade2010@hotmail.com")
    senha = discord.ui.TextInput(label="Senha (completa)", placeholder="Ex: babyrikicheg0u!")
    servidor = discord.ui.TextInput(label="Servidor", placeholder="Ex: america")
    metodo = discord.ui.TextInput(label="Método de Login", placeholder="Ex: direto no jogo")

    async def on_submit(self, interaction: discord.Interaction):
        embed_recebido = discord.Embed(
            title="🔑 Dados de Acesso Recebidos",
            color=discord.Color.from_rgb(120, 50, 150)
        )
        embed_recebido.add_field(name="📩 Email", value=f"`{self.email.value}`", inline=False)
        embed_recebido.add_field(name="🔒 Senha", value=f"`{self.senha.value}`", inline=False)
        embed_recebido.add_field(name="🌐 Servidor", value=f"`{self.servidor.value}`", inline=True)
        embed_recebido.add_field(name="🔗 Método de Login", value=f"`{self.metodo.value}`", inline=True)
        embed_recebido.set_footer(text=f"Enviado por {interaction.user.name} 🌸")

        await interaction.message.delete()
        await interaction.response.send_message(embed=embed_recebido)

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

class ModalGerarPix(discord.ui.Modal, title="⚡ Gerar Cobrança PIX"):
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
                "Bootao Services 🌸"
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
    await interaction.response.send_message("👻 **Manual:** Total segurança.\n🤖 **Script:** Automação rápida.")

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
