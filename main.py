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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS embeds_personalizados (
            id_botao TEXT PRIMARY KEY,
            titulo TEXT,
            texto TEXT,
            imagem_resposta TEXT,
            cor_int INTEGER
        )
    """)
    conn.commit()
    conn.close()

inicializar_banco()

def salvar_embed_no_banco(id_botao, titulo, texto, imagem_resposta, cor_int):
    conn = sqlite3.connect("dados_loja.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO embeds_personalizados (id_botao, titulo, texto, imagem_resposta, cor_int)
        VALUES (?, ?, ?, ?, ?)
    """, (id_botao, titulo, texto, imagem_resposta, cor_int))
    conn.commit()
    conn.close()

def puxar_embed_do_banco(id_botao):
    conn = sqlite3.connect("dados_loja.db")
    cursor = conn.cursor()
    cursor.execute("SELECT titulo, texto, imagem_resposta, cor_int FROM embeds_personalizados WHERE id_botao = ?", (id_botao,))
    resultado = cursor.fetchone()
    conn.close()
    if resultado:
        return {
            "titulo": resultado[0],
            "texto": resultado[1],
            "imagem_resposta": resultado[2],
            "cor_int": resultado[3]
        }
    return None

# ==========================================
# 🤖 CONFIGURAÇÃO DO BOT
# ==========================================
CHAVE_PIX_PADRAO = os.getenv("CHAVE_PIX", "bootaoservices01@gmail.com")
SETUP_TEMPORARIO_PARAMETROS = {}

class HuTaoBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(ViewAbreTicketDinamico())
        self.add_view(ViewBotaoDinamicoPersistente())
        self.add_view(ViewPainelLogin())
        await self.tree.sync()

bot = HuTaoBot()

# ==========================================
# 🎫 SISTEMA DE TICKET DINÂMICO PERSISTENTE
# ==========================================
class ViewAbreTicketDinamico(discord.ui.View):
    def __init__(self, botao_texto: str = "🛒 Fazer Pedido"):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(
            label=botao_texto, 
            style=discord.ButtonStyle.success, 
            custom_id="btn_abrir_ticket_dinamico", 
            emoji="🎫"
        ))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.data.get("custom_id") == "btn_abrir_ticket_dinamico":
            guild = interaction.guild
            categoria = discord.utils.get(guild.categories, id=ID_CATEGORIA_TICKETS)
            
            nome_canal = f"🛒-{interaction.user.name}"
            
            canal_existente = discord.utils.get(guild.text_channels, name=nome_canal.lower())
            if canal_existente:
                await interaction.response.send_message(f"❌ Você já possui um ticket aberto em {canal_existente.mention}!", ephemeral=True)
                return False

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
            return True
        return await super().interaction_check(interaction)

# ==========================================
# 🔘 RECEPTOR DE CLIQUES COM BANCO DE DADOS
# ==========================================
class ViewBotaoDinamicoPersistente(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        custom_id = interaction.data.get("custom_id", "")
        
        if custom_id.startswith("info_"):
            # Puxa diretamente do Banco de Dados de forma permanente
            dados_guardados = puxar_embed_do_banco(custom_id)
            
            if dados_guardados:
                titulo = dados_guardados.get("titulo", "Informações")
                texto_original = dados_guardados.get("texto", "")
                img_rodape_url = dados_guardados.get("imagem_resposta", "")
                cor_int = dados_guardados.get("cor_int", 7877270)
                cor = discord.Color(cor_int)
                
                # Procura links de imagem no meio do texto
                regex_imagens = r'(https?://\S+\.(?:png|jpg|jpeg|gif|webp))'
                links_encontrados = re.findall(regex_imagens, texto_original, re.IGNORECASE)
                texto_limpo = re.sub(regex_imagens, '', texto_original).strip()
                
                lista_embeds = []
                
                embed_texto = discord.Embed(
                    title=titulo,
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
                await interaction.response.send_message("❌ Erro: As informações desse botão não foram encontradas no banco de dados!", ephemeral=True)
            return True
        return await super().interaction_check(interaction)

# ==========================================
# 📥 FORMULÁRIOS DE CONFIGURAÇÃO OTIMIZADOS
# ==========================================

class ModalCriarSetupCompleto(discord.ui.Modal, title="🛒 Configurar Painel de Tickets"):
    titulo = discord.ui.TextInput(label="Título do Painel", placeholder="Ex: 🛒 Central de Pedidos", required=True)
    description = discord.ui.TextInput(label="Descrição / Texto", style=discord.TextStyle.paragraph, placeholder="Escreva as regras/boas-vindas do seu ticket aqui...", required=True)
    texto_botao = discord.ui.TextInput(label="Texto do Botão", placeholder="Ex: 🛒 Fazer Pedido", max_length=50, default="🛒 Fazer Pedido", required=True)
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

        view_ticket = ViewAbreTicketDinamico(botao_texto=self.texto_botao.value)
        await self.canal.send(embed=embed_construida, view=view_ticket)
        await interaction.response.send_message(f"✅ Painel de Tickets enviado com sucesso em {self.canal.mention}!", ephemeral=True)


class ModalCriarEmbedCompleto(discord.ui.Modal, title="🎨 Criar Embed Personalizada"):
    titulo = discord.ui.TextInput(label="Título da Embed Principal", placeholder="Ex: 📜 Tabela de Valores", required=True)
    description = discord.ui.TextInput(label="Descrição / Texto da Embed Principal", style=discord.TextStyle.paragraph, placeholder="Clique no botão abaixo e veja nossos valores...", required=True)
    texto_botao = discord.ui.TextInput(label="Texto do Botão Informativo", placeholder="Ex: 👻 Valores", max_length=50, required=True)
    resposta_clique = discord.ui.TextInput(label="Texto da Resposta (Cole links de imagem tbm!)", style=discord.TextStyle.paragraph, placeholder="Pode escrever seu texto normalmente e colar links de imagens direto aqui!", required=True)
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
            await interaction.response.send_message("❌ Houve um erro de sessão ao processar o canal. Tente usar o comando novamente.", ephemeral=True)
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

        id_unico_botao = f"info_{interaction.id}"
        
        # 💾 SALVA PERMANENTEMENTE NO BANCO DE DADOS LOCAL
        salvar_embed_no_banco(
            id_botao=id_unico_botao,
            titulo=self.titulo.value,
            texto=self.resposta_clique.value.replace(r'\n', '\n'),
            imagem_resposta=self.url_imagem_resposta.value if self.url_imagem_resposta.value else None,
            cor_int=cor.value
        )

        view_customizada = discord.ui.View(timeout=None)
        view_customizada.add_item(discord.ui.Button(
            label=self.texto_botao.value,
            style=discord.ButtonStyle.primary,
            custom_id=id_unico_botao
        ))

        await canal.send(embed=embed_construida, view=view_customizada)
        await interaction.response.send_message(f"✅ Embed personalizada salva e enviada com sucesso em {canal.mention}!", ephemeral=True)
        
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
    print("🚨 Bot desligado via comando de barra /reiniciar.")
    await bot.close()
    sys.exit(0)


# ==========================================
# 📜 VIEW DOS BOTÕES DE LINK (TERMOS E REGRAS)
# ==========================================
class ViewLinksTermos(discord.ui.View):
    def __init__(self, guild_id: int, channel_termos_id: int, channel_regras_id: int):
        super
