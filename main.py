import discord
from discord.ext import commands
import asyncio
import json
import os
import aiohttp
from flask import Flask
from threading import Thread
from googletrans import Translator

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

animes = {}

def salvar_animes():
    with open("animes.json", "w", encoding="utf-8") as f:
        json.dump(animes, f, ensure_ascii=False, indent=4)

def carregar_animes():
    global animes
    if os.path.exists("animes.json"):
        with open("animes.json", "r", encoding="utf-8") as f:
            animes = json.load(f)

carregar_animes()

@bot.event
async def on_ready():
    print(f"Bot online como {bot.user}")

@bot.command()
async def ola(ctx):
    usuario = ctx.author.name
    await ctx.send(f"Olá, {usuario}, seja bem-vindo. Digite !comandos para ver o que posso fazer!")

@bot.command()
async def comandos(ctx):
    texto = (
        "**Comandos disponíveis:**\n"
        "`!ola` - Saudação\n"
        "`!comandos` - Lista comandos\n"
        "`!addanime <nome> <nota>` - Adiciona anime com nota (1 a 5)\n"
        "`!removeranime <nome>` - Remove anime da lista\n"
        "`!veranime <nome>` - Mostra detalhes do anime (local ou API)\n"
        "`!assistido <nome>` - Alterna status de assistido\n"
        "`!lista` - Lista todos os animes com status e nota\n"
        "`!feedback <nome> <comentário>` - Adiciona comentário para o anime\n"
        "`!verfeedback <nome>` - Mostra comentários do anime\n"
        "`!topicos <nome> <tópico>` - Adiciona ou remove tópicos do anime\n"
    )
    await ctx.send(texto)

@bot.command()
async def addanime(ctx, nome: str, nota: float):
    nome = nome.lower()
    if nome in animes:
        await ctx.send(f"O anime '{nome}' já está cadastrado.")
    else:
        if 1 <= nota <= 5:
            animes[nome] = {
                "nota": nota,
                "descricao": "",
                "foto": "",
                "assistido_por": [],
                "total_assistido": 0,
                "comentarios": [],
                "topicos": []
            }
            salvar_animes()
            await ctx.send(f"Anime '{nome}' adicionado com nota {nota}.")
        else:
            await ctx.send("Nota inválida! Use um número entre 1 e 5.")

@bot.command()
async def removeranime(ctx, *, nome: str):
    nome = nome.lower()
    if nome in animes:
        del animes[nome]
        salvar_animes()
        await ctx.send(f"Anime '{nome}' removido da lista.")
    else:
        await ctx.send(f"Anime '{nome}' não encontrado na lista.")

@bot.command()
async def veranime(ctx, *, nome: str):
    nome = nome.lower()
    if nome in animes:
        info = animes[nome]
        status = "Assistido" if ctx.author.name in info["assistido_por"] else "Não assistido"
        embed = discord.Embed(
            title=nome.title(),
            description=info.get("descricao", "Sem descrição."),
            color=discord.Color.purple()
        )
        embed.add_field(name="Nota (local)", value=str(info.get("nota", "N/A")))
        embed.add_field(name="Status", value=status)
        if info.get("foto"):
            embed.set_image(url=info["foto"])
        await ctx.send(embed=embed)
    else:
        url = f"https://api.jikan.moe/v4/anime?q={nome}&limit=1"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data["data"]:
                        anime = data["data"][0]
                        anime_id = anime["mal_id"]
                        translator = Translator()

                        url_pt = f"https://api.jikan.moe/v4/anime/{anime_id}/full"
                        await asyncio.sleep(1)
                        async with session.get(url_pt) as resp_pt:
                            if resp_pt.status == 200:
                                data_pt = await resp_pt.json()
                                anime_pt = data_pt["data"]
                                titulo = anime_pt.get("title", "")
                                sinopse = anime_pt.get("synopsis", "Sem descrição disponível.")
                                try:
                                    titulo_traduzido = translator.translate(titulo, dest='pt').text
                                    descricao = translator.translate(sinopse, dest='pt').text
                                except:
                                    titulo_traduzido = titulo
                                    descricao = sinopse
                                imagem = anime_pt["images"]["jpg"]["image_url"]
                                nota_real = anime_pt.get("score", "N/A")

                        jikan_url = f"https://myanimelist.net/anime/{anime_id}"
                        descricao_com_link = f"{descricao[:300]}{'...' if len(descricao) > 300 else ''}\n\n[Ver descrição completa]({jikan_url})"

                        embed = discord.Embed(
                            title=titulo_traduzido,
                            description=descricao_com_link,
                            color=discord.Color.purple(),
                            url=jikan_url
                        )
                        embed.add_field(name="Nota (API)", value=str(nota_real), inline=False)
                        embed.set_image(url=imagem)
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send(f"Anime '{nome}' não encontrado nem na lista nem na API.")
                else:
                    await ctx.send("Erro ao buscar informações do anime na API.")

@bot.command()
async def assistido(ctx, *, nome: str):
    nome = nome.lower()
    if nome in animes:
        usuario = ctx.author.name
        if usuario not in animes[nome]["assistido_por"]:
            animes[nome]["assistido_por"].append(usuario)
            animes[nome]["total_assistido"] += 1
            await ctx.send(f"{usuario} marcou '{nome}' como assistido! Total de {animes[nome]['total_assistido']} pessoa(s) assistiram.")
        else:
            animes[nome]["assistido_por"].remove(usuario)
            animes[nome]["total_assistido"] -= 1
            await ctx.send(f"{usuario} removeu '{nome}' da lista de assistidos. Total de {animes[nome]['total_assistido']} pessoa(s) assistiram.")
        salvar_animes()
    else:
        await ctx.send(f"O anime '{nome}' não está cadastrado. Use !addanime para adicioná-lo.")

@bot.command()
async def lista(ctx):
    if not animes:
        await ctx.send("Nenhum anime cadastrado ainda.")
    else:
        for nome, info in animes.items():
            embed = discord.Embed(
                title=nome.title(),
                color=discord.Color.green()
            )
            assistido_por = info.get("assistido_por", [])
            total = info.get("total_assistido", 0)
            status = f"Assistido por {total} pessoa(s)"
            if ctx.author.name in assistido_por:
                status += " (incluindo você)"

            embed.add_field(name="Status", value=status, inline=True)
            embed.add_field(name="Nota", value=str(info.get("nota", "N/A")), inline=True)
            embed.add_field(name="Tópicos", value=" | ".join(info.get("topicos", [])), inline=False)
            await ctx.send(embed=embed)

@bot.command()
async def topicos(ctx, nome: str, *, topico: str):
    nome = nome.lower()
    if nome in animes:
        if topico in animes[nome]["topicos"]:
            animes[nome]["topicos"].remove(topico)
            await ctx.send(f"Tópico '{topico}' removido de '{nome}'.")
        else:
            animes[nome]["topicos"].append(topico)
            await ctx.send(f"Tópico '{topico}' adicionado a '{nome}'.")
        salvar_animes()
    else:
        await ctx.send(f"O anime '{nome}' não está cadastrado. Use !addanime para adicioná-lo.")

@bot.command()
async def feedback(ctx, nome: str, *, comentario: str):
    nome = nome.lower()
    if nome in animes:
        usuario = ctx.author.name
        animes[nome]["comentarios"].append({"usuario": usuario, "comentario": comentario})
        salvar_animes()
        await ctx.send(f"Comentário adicionado para '{nome}'.")
    else:
        await ctx.send(f"O anime '{nome}' não está cadastrado. Use !addanime para adicioná-lo.")

@bot.command()
async def verfeedback(ctx, *, nome: str):
    nome = nome.lower()
    if nome in animes:
        comentarios = animes[nome].get("comentarios", [])
        if comentarios:
            embed = discord.Embed(
                title=f"Comentários sobre {nome.title()}",
                color=discord.Color.blue()
            )
            for c in comentarios:
                embed.add_field(name=c["usuario"], value=c["comentario"], inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"Não há comentários para '{nome}'.")
    else:
        await ctx.send(f"O anime '{nome}' não está cadastrado. Use !addanime para adicioná-lo.")

# Flask server para manter vivo
app = Flask('')

@app.route('/')
def home():
    return "Bot online"

def run():
    app.run(host='0.0.0.0', port=3000)

def keep_alive():
    server = Thread(target=run)
    server.start()

TOKEN = os.getenv('DISCORD_TOKEN')
if TOKEN is None:
    print("Please set your DISCORD_TOKEN in the Secrets tab")
    exit(1)

keep_alive()
bot.run(TOKEN)