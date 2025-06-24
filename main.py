import os
import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption, Embed, Colour, ui, TextStyle
from flask import Flask
from threading import Thread
import logging
import asyncio
from functools import wraps
from datetime import datetime


app = Flask('')

@app.route('/')
def home():
    return "Bot attivo."

def run():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run).start()


RIABILITAZIONI_ID = 1212887541137809448 
ASSEGNAZIONI_ID = 1077224605904818176  
ATTI_ID = 1077221214327689347
CANALE_UDIENZA_ID = 1288481660299513886
RUOLO_ID = 1075145554415341629


intents = nextcord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True


bot = commands.Bot(command_prefix="!", intents=intents)


logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%d/%m/%Y %H:%M:%S')


async def cambia_stato():
    await bot.wait_until_ready()
    stati = [
        "Richieste Riabilitazione Penale",
        "Procedimenti in Attesa",
        "Inchieste"
    ]
    index = 0

    while not bot.is_closed():
        stato_attuale = stati[index % len(stati)]
        await bot.change_presence(activity=nextcord.Activity(type=nextcord.ActivityType.watching, name=stato_attuale))
        index += 1
        await asyncio.sleep(1800)


def logs():
    def decorator(func):
        @wraps(func)
        async def wrapper(interaction: Interaction, *args, **kwargs):
            user = interaction.user
            timestamp = datetime.utcnow().strftime('%d/%m/%Y %H:%M:%S')
            logging.info(f"Comando eseguito da {user.display_name} (ID: {user.id}) alle {timestamp}")
            return await func(interaction, *args, **kwargs)
        return wrapper
    return decorator


def ruoli_ag():
    ids_ruoli = [
        1263135274863689829
    ]
    def decorator(func):
        @wraps(func)
        async def wrapper(interaction: Interaction, *args, **kwargs):
            if any(role.id in ids_ruoli for role in interaction.user.roles):
                return await func(interaction, *args, **kwargs)
            await interaction.response.send_message("Non hai i permessi per usare questo comando.", ephemeral=True)
        return wrapper
    return decorator


@bot.event
async def on_ready():
    await bot.wait_until_ready()
    try:
        synced = await bot.tree.sync()
        print(f"[DEBUG] Comandi slash sincronizzati: {len(synced)}")
    except Exception as e:
        print(f"[DEBUG] Errore sincronizzazione: {e}")
    print(f"[DEBUG] Bot connesso come {bot.user}")
    bot.loop.create_task(cambia_stato())



class RiabilitazioneModalAccettata(ui.Modal):
    def __init__(self, user: nextcord.Member, data: str, cancelliere: str):
        super().__init__("Dati riabilitazione accettata")
        self.user = user
        self.data = data
        self.cancelliere = cancelliere

        self.luogo = ui.TextInput(label="Luogo della riabilitazione", required=True)
        self.link_trello = ui.TextInput(label="Link Trello", required=True)

        self.add_item(self.luogo)
        self.add_item(self.link_trello)

    async def callback(self, interaction: Interaction):
     
        await interaction.response.defer(ephemeral=True)

        embed = Embed(
            title="Esito Riabilitazione Penale",
            colour=Colour.from_rgb(95, 134, 249)
        )
        embed.set_author(name="Cancelleria regionale")
        embed.description = (
            f"Salve, {self.user.mention}, la sua richiesta di riabilitazione penale è stata **accettata**.\n\n"
            f"Svolgerà una settimana di volontariato presso **{self.luogo.value}**.\n"
            f"**Link Trello**: {self.link_trello.value}\n\n"
            f"Lì, Napoli, {self.data},\n"
            f"Il Cancelliere,\n{self.cancelliere}"
        )

        try:
            canale = await bot.fetch_channel(RIABILITAZIONI_ID)
            await canale.send(embed=embed)
        except Exception as e:
            print(f"Errore nell'invio al canale riabilitazioni: {e}")

        try:
            await self.user.send(embed=embed)
        except Exception as e:
            print(f"Errore nell'invio dei DM: {e}")

   
        await interaction.followup.send("Esito inviato con successo.", ephemeral=True)


class RiabilitazioneModalRifiutata(ui.Modal):
    def __init__(self, user: nextcord.Member, data: str, cancelliere: str):
        super().__init__("Dati riabilitazione rifiutata")
        self.user = user
        self.data = data
        self.cancelliere = cancelliere

        self.motivazione = ui.TextInput(label="Motivazione del rifiuto", required=True)
        self.add_item(self.motivazione)

    async def callback(self, interaction: Interaction):
        embed = Embed(
            title="Esito Riabilitazione Penale",
            colour=Colour.from_rgb(95, 134, 249)
        )
        embed.set_author(name="Cancelleria regionale")
        embed.description = (
            f"Salve, {self.user.mention}, la sua richiesta di riabilitazione penale è stata **rifiutata**.\n\n"
            f"**Motivazione:** {self.motivazione.value}\n"
            f"Per ulteriori informazioni, contatti la segreteria (<#1122542213499469904>)\n\n"
            f"Lì, Napoli, {self.data},\n"
            f"Il Cancelliere,\n{self.cancelliere}"
        )

        try:
            canale = await bot.fetch_channel(RIABILITAZIONI_ID)
            await canale.send(embed=embed)
        except Exception as e:
            print(f"Errore nell'invio al canale riabilitazioni: {e}")

        try:
            await self.user.send(embed=embed)
        except Exception as e:
            print(f"Errore nell'invio dei DM: {e}")

        await interaction.response.send_message("Esito inviato con successo.", ephemeral=True)


@bot.slash_command(name="esito-riabilitazione", description="Invia l'esito della riabilitazione penale")
@ruoli_ag()
@logs()
async def esito_riabilitazione(
    interaction: Interaction,
    nome: nextcord.Member = SlashOption(description="Utente coinvolto"),
    esito: str = SlashOption(description="Esito", choices=["Accettata", "Rifiutata"]),
    data: str = SlashOption(description="Data (es. 23/06/2025)"),
    nome_cancelliere: str = SlashOption(description="Nome del Cancelliere")
):
    if esito == "Accettata":
        await interaction.response.send_modal(RiabilitazioneModalAccettata(nome, data, nome_cancelliere))
    else:
        await interaction.response.send_modal(RiabilitazioneModalRifiutata(nome, data, nome_cancelliere))



@bot.slash_command(name="assegnazione", description="Assegna un caso a un addetto")
@ruoli_ag()
@logs()
async def assegnazione(
    interaction: Interaction,
    qualifica: str = SlashOption(description="Qualifica del destinatario"),
    addetto: nextcord.Member = SlashOption(description="Utente assegnato"),
    link_trello: str = SlashOption(description="Link Trello"),
    data: str = SlashOption(description="Data di assegnazione"),
    nome: str = SlashOption(description="Nome di chi assegna")
):
    await interaction.response.defer(ephemeral=True)  

    embed = Embed(
        title="Assegnazione",
        description=(
            f"> Il **{qualifica}** {addetto.mention}, viene assegnato al seguente caso:\n"
            f"* {link_trello}\n\n"
            f"Lì, Napoli, {data}\n"
            f"{nome}"
        ),
        color=0x5f86f9
    )
    embed.set_author(name="Autorità Giudiziaria")

    try:
        canale = await bot.fetch_channel(ASSEGNAZIONI_ID)
        await canale.send(embed=embed)
    except Exception as e:
        print(f"Errore nell'invio al canale assegnazioni: {e}")

    try:
        await addetto.send(embed=embed)
    except Exception as e:
        print(f"Errore nell'invio dei DM: {e}")

    await interaction.followup.send("Assegnazione inviata con successo.", ephemeral=True)

    
    
@bot.slash_command(name="atto", description="Deposita un atto giudiziario")
@ruoli_ag()
@logs()
async def atto(
    interaction: Interaction,
    nome: str = SlashOption(description="Nome di chi deposita l'atto"),
    qualifica: str = SlashOption(description="Qualifica"),
    atto: str = SlashOption(description="Contenuto dell'atto")
):
    await interaction.response.defer(ephemeral=True)  

    now = datetime.now(timezone.utc)
    timestamp = int(now.timestamp())

    embed = Embed(
        title="Deposito Atti Giudiziari",
        colour=Colour.dark_blue()
    )
    embed.add_field(name="Nome", value=nome, inline=False)
    embed.add_field(name="Qualifica", value=qualifica, inline=False)
    embed.add_field(name="Atto Giudiziario", value=atto, inline=False)
    embed.add_field(name="Data", value=f"<t:{timestamp}:F>", inline=False)
    embed.set_footer(text="Autorità Giudiziaria")

    try:
        canale = await bot.fetch_channel(ATTI_ID)
        await canale.send(embed=embed)
    except Exception as e:
        print(f"Errore nell'invio dell'atto: {e}")
        await interaction.followup.send("Errore nell'invio dell'atto.", ephemeral=True)
        return

    await interaction.followup.send("Atto depositato correttamente.", ephemeral=True)  
    
    
    

@bot.slash_command(name="udienza", description="Annuncia una nuova udienza")
@ruoli_ag()
@logs()
async def udienza(
    interaction: Interaction,
    imputato: str = SlashOption(description="Nome dell'imputato"),
    data: str = SlashOption(description="Data dell'udienza (es. 25/06/2025)"),
    orario: str = SlashOption(description="Orario dell'udienza (es. 14:00)"),
    aula: str = SlashOption(description="Aula dell'udienza", choices=["Aula 1", "Aula 2", "Aula Bunker"]),
    luogo: str = SlashOption(description="Luogo del processo", choices=["Tribunale Ordinario", "Poggioreale"]),
    magistrato: nextcord.Member = SlashOption(description="Magistrato responsabile"),
    processo: str = SlashOption(description="Inserire che tipo di processo è")
):
    await interaction.response.defer(ephemeral=True)  

    embed = Embed(
        title="Tribunale Ordinario",
        description=(
            f"{processo} avverso **{imputato}** il giorno **{data}** alle ore **{orario}** "
            f"presso **{aula} {luogo}**\n\n"
            f"Presiede il dott. {magistrato.display_name}"
        ),
        colour=Colour.blue()
    )
    embed.set_footer(text=f"Creato il: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}")

    try:
        canale = await bot.fetch_channel(CANALE_UDIENZA_ID)
        await canale.send(embed=embed)

        ruolo = canale.guild.get_role(RUOLO_ID)
        if ruolo:
            await canale.send(
                content=ruolo.mention,
                allowed_mentions=nextcord.AllowedMentions(roles=True)
            )

        await interaction.followup.send("Udienza annunciata correttamente.", ephemeral=True)  

    except Exception as e:
        print(f"Errore nell'invio dell'udienza: {e}")
        await interaction.followup.send("Errore durante l'invio dell'udienza.", ephemeral=True)

    
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        print("[DEBUG] Avvio bot...")
        bot.run(token)
    else:
        print("[DEBUG] Variabile DISCORD_TOKEN non trovata.")
