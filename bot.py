import discord
from discord.ext import commands
from datetime import datetime, timedelta
import asyncio
import re
import webserver
import os

DISCORD_TOKEN = os.environ['discordkey']

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='.', intents=intents)

WARN_ROLE_NAME = 'Warn'
TARGET_VOICE_CHANNEL_ID = 
GREET_CHANNEL_ID = 
BAN_LOG_CHANNEL_ID = 
WARNING_DURATION = 86400

link_pattern = r'(https?://\S+|http://\S+|www\.\S+)'

warn_expiration = {}

@bot.event
async def on_ready():
    print(f'Bot is ready and logged in as {bot.user}')

@bot.event
async def on_member_join(member):
    greet_channel = bot.get_channel(GREET_CHANNEL_ID)
    if greet_channel:
        await greet_channel.send(f'Willkommen auf dem Server, {member.mention}! Wir freuen uns nicht! Sie hier zu haben!')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if re.search(link_pattern, message.content):
        try:
            await message.author.ban(reason="Link gesendet.")
            ban_log_channel = bot.get_channel(BAN_LOG_CHANNEL_ID)
            if ban_log_channel:
                await ban_log_channel.send(f'{message.author.mention} wurde für das Senden eines Links gesperrt.')
        except discord.Forbidden:
            print(f'Could not ban {message.author.mention} due to insufficient permissions.')
        except discord.HTTPException:
            print(f'Failed to ban {message.author.mention}.')

    await bot.process_commands(message)

@bot.command()
async def hello(ctx):
    await ctx.send(f'yo {ctx.author.mention}')

@bot.command()
async def warn(ctx, member: discord.Member):
    guild = ctx.guild
    warn_role = discord.utils.get(guild.roles, name=WARN_ROLE_NAME)

    if not warn_role:
        await ctx.send("Die 'Warn'-Rolle fehlt. Bitte erstellen Sie es zuerst.")
        return

    warn_message = (
        f'**Vote to warn {member.mention}!**\n'
        'Reagieren mit 🟢 zu warnen oder 🔴 nicht warnen.'
    )
    warning_message = await ctx.send(warn_message)
    await warning_message.add_reaction("🟢")
    await warning_message.add_reaction("🔴")

    def check(reaction, user):
        return user != bot.user and str(reaction.emoji) in ["🟢", "🔴"]

    green_votes = 0
    red_votes = 0

    try:
        await bot.wait_for('reaction_add', timeout=20.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send("Die Abstimmungsrunde wurde aus Zeitgründen beendet.")
    
    warning_message = await ctx.fetch_message(warning_message.id)
    green_votes = sum(reaction.count - 1 for reaction in warning_message.reactions if str(reaction.emoji) == "🟢")
    red_votes = sum(reaction.count - 1 for reaction in warning_message.reactions if str(reaction.emoji) == "🔴")

    total_votes = green_votes + red_votes

    if total_votes >= 2 and green_votes > red_votes:
        await member.add_roles(warn_role)
        warn_message = (
            "　　。　　　　•　 　ﾟ　　.\n"
            "　.　　.　　.　 　　.　　.　　　。　　 。　.\n"
            "　 。　　　.　　 ඞ 。 . 　　 • 　　　　•\n"
            f"　.　ﾟ {member.display_name} was an Impostor.  .\n"
            "　　'　　　。           。      .           。    . 　 　　。\n"
            "　.　ﾟ　.　　。　　　。,　　　　。　 . \n"
        )
        await ctx.send(warn_message)

        bot.loop.create_task(handle_warn_expiry(member))

@bot.command()
@commands.has_permissions(administrator=True)
async def warnn(ctx, member: discord.Member):
    """Administrator-only command to automatically warn a member"""
    guild = ctx.guild
    warn_role = discord.utils.get(guild.roles, name=WARN_ROLE_NAME)

    if not warn_role:
        await ctx.send("Die 'Warn'-Rolle fehlt. Bitte erstellen Sie es zuerst.")
        return

    await member.add_roles(warn_role)

    warn_message = (
        "　　。　　　　•　 　ﾟ　　.\n"
        "　.　　.　　.　 　　.　　.　　　。　　 。　.\n"
        "　 。　　　.　　 ඞ 。 . 　　 • 　　　　•\n"
        f"　.　ﾟ {member.display_name} was an Impostor.  .\n"
        "　　'　　　。           。      .           。    . 　 　　。\n"
        "　.　ﾟ　.　　。　　　。,　　　　。　 . \n"
    )
    
    await ctx.send(warn_message)
    
    bot.loop.create_task(handle_warn_expiry(member))

async def handle_warn_expiry(member):
    warn_role = discord.utils.get(member.guild.roles, name=WARN_ROLE_NAME)

    now = datetime.utcnow()
    if member.id in warn_expiration:
        warn_expiration[member.id] += timedelta(seconds=WARNING_DURATION)
    else:
        warn_expiration[member.id] = now + timedelta(seconds=WARNING_DURATION)

    while True:
        now = datetime.utcnow()
        if member.id not in warn_expiration:
            break

        if now >= warn_expiration[member.id]:
            await member.remove_roles(warn_role)
            del warn_expiration[member.id]
            break
        else:
            await asyncio.sleep(10)

@bot.command()
async def time(ctx):
    member = ctx.author
    now = datetime.utcnow()

    if member.id in warn_expiration:
        time_left = warn_expiration[member.id] - now

        if time_left.total_seconds() > 0:
            hours, remainder = divmod(time_left.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            await ctx.send(f'{member.display_name}, du hast {int(hours)} stunden, {int(minutes)} minuten, und {int(seconds)} Sekunden Warnung.')
        else:
            await ctx.send(f'{member.display_name}, Deine Warnung ist bereits abgelaufen.')
    else:
        await ctx.send(f'{member.display_name}, Du wirst derzeit nicht gewarnt. gut für dich :/')

@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel and after.channel.id == TARGET_VOICE_CHANNEL_ID:
        channel_name = f"{member.display_name}'s Kanal"
        limit = 5

        overwrites = {
            member.guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=True),
            member: discord.PermissionOverwrite(view_channel=True, connect=True, manage_channels=True, manage_permissions=True)
        }

        new_channel = await member.guild.create_voice_channel(
            name=channel_name,
            category=after.channel.category,
            overwrites=overwrites,
            user_limit=limit
        )

        await member.move_to(new_channel)

        bot.loop.create_task(delete_channel_if_empty(new_channel))

async def delete_channel_if_empty(voice_channel):
    await asyncio.sleep(1)
    while True:
        await asyncio.sleep(10)
        if len(voice_channel.members) == 0:
            await voice_channel.delete()
            break

webserver.keep_alive()

bot.run('BOT TOKEN HERE')
