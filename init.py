# Make sure cache dirs exist
import os
folders = ["program/music/cache", "log"]
for folder in folders:
    if not os.path.exists(f"{os.path.realpath(os.path.dirname(__file__))}/{folder}"):
        os.makedirs(f"{os.path.realpath(os.path.dirname(__file__))}/{folder}")
        print(f"[init.py]-[Info]: Created directory '{folder}'")

# Imports
import subprocess, asyncio, json, platform, sys, aiosqlite, exceptions, discord, time
from discord.ext import commands
from discord.ext.commands import Bot, Context
from program.logger import logger
from dotenv import load_dotenv


# Load base config file
if not os.path.isfile(f"{os.path.realpath(os.path.dirname(__file__))}/config.json"):
    sys.exit("[init.py]-[Error]: 'config.json' not found.")
else:
    with open(f"{os.path.realpath(os.path.dirname(__file__))}/config.json") as file:
        config = json.load(file)

# Check presence of ffmpeg
if platform.system() == 'Windows':
    if not os.path.isfile(f"{os.path.realpath(os.path.dirname(__file__))}/ffmpeg.exe"):
        sys.exit("[init.py]-[Error]: 'ffmpeg.exe' not found.")
elif platform.system() == 'Linux':
    try:
        # Try to execute ffmpeg if on linux
        result = subprocess.run(['ffmpeg', '-version'], 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE, 
                                text=True)
        if result.returncode != 0:
            sys.exit("[init.py]-[Error]: 'ffmpeg' not found on this system, please install it, or if it is installed, check if it is available in PATH.")
    except FileNotFoundError:
        sys.exit("[init.py]-[Error]: 'ffmpeg' not found on this system, please install it, or if it is installed, check if it is available in PATH.")

# Bot intentions (many)
intents = discord.Intents.all()
intents.dm_messages = True
intents.dm_reactions = True
intents.dm_typing = True
intents.emojis = True
intents.guild_messages = True
intents.guild_reactions = True
intents.guild_scheduled_events = True
intents.guild_typing = True
intents.guilds = True
intents.integrations = True
intents.invites = True
intents.voice_states = True
intents.webhooks = True
intents.members = True
intents.message_content = True
intents.presences = True
intents.emojis_and_stickers = True
intents.messages = True
intents.reactions = True
intents.typing = True
intents.bans = True

# Bot
bot = Bot(
    command_prefix=commands.when_mentioned_or(config["prefix"]),
    intents=intents,
    help_command=None,)
bot.logger = logger
bot.config = config

# Vars
freshstart = True


# Start SQL database
async def init_db():
    async with aiosqlite.connect(
        f"{os.path.realpath(os.path.dirname(__file__))}/database/database.db"
    ) as db:
        with open(
            f"{os.path.realpath(os.path.dirname(__file__))}/database/schema.sql"
        ) as file:
            await db.executescript(file.read())


# When ready
@bot.event
async def on_ready() -> None:
    # Initial logger info (splash)
    bot.logger.info("--------------------------------------")
    bot.logger.info(" >   RinBot v1.5.1 (GitHub release)   ")
    bot.logger.info("--------------------------------------")
    bot.logger.info(f" > Logged as {bot.user.name}")
    bot.logger.info(f" > API Version: {discord.__version__}")
    bot.logger.info(f" > Python Version: {platform.python_version()}")
    bot.logger.info(f" > Running on: {platform.system()}-{platform.release()} ({os.name})")
    bot.logger.info("--------------------------------------")
    
    
    # Default status
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening, name='to your commands :3'))
        
    # Sync commands with discord
    bot.logger.info("Synching commands globally")
    await bot.tree.sync()

# TODO: Change the guild_id to be at the database
# Save new guild ID's when joining
@bot.event
async def on_guild_join(guild):
    config['joined_on'].append(guild.id)
    with open(f"{os.path.realpath(os.path.dirname(__file__))}/config.json") as file:
        json.dump(config, file, indent=4)
    bot.logger.info(f'Joined guild ID: {guild.id}')

# Process non-slash commands (not-in-use at the moment)
@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author == bot.user or message.author.bot:
        return
    await bot.process_commands(message)

# Show executed commands on the log
@bot.event
async def on_command_completion(context: Context) -> None:
    full_command_name = context.command.qualified_name
    split = full_command_name.split(" ")
    executed_command = str(split[0])
    if context.guild is not None:
        bot.logger.info(
            f"Comando {executed_command} executado em {context.guild.name} (ID: {context.guild.id}) por {context.author} (ID: {context.author.id})")
    else:
        bot.logger.info(
            f"Comando {executed_command} executado por {context.author} (ID: {context.author.id}) nas DMs.")

# What to do when commands go no-no
@bot.event
async def on_command_error(context: Context, error) -> None:
    if isinstance(error, commands.CommandOnCooldown):
        minutes, seconds = divmod(error.retry_after, 60)
        hours, minutes = divmod(minutes, 60)
        hours = hours % 24
        embed = discord.Embed(
            description=f"**Please wait! >-< ** - You can use this command again in {f'{round(hours)} hours' if round(hours) > 0 else ''} {f'{round(minutes)} minutes' if round(minutes) > 0 else ''} {f'{round(seconds)} seconds' if round(seconds) > 0 else ''}.",
            color=0xE02B2B,)
        await context.send(embed=embed)
    elif isinstance(error, exceptions.UserBlacklisted):
        embed = discord.Embed(
            description="You are blocked from using RinBot!", color=0xE02B2B)
        await context.send(embed=embed)
        if context.guild:
            bot.logger.warning(
                f"{context.author} (ID: {context.author.id}) tried running a command on guild {context.guild.name} (ID: {context.guild.id}), but they're blocked from using RinBot.")
        else:
            bot.logger.warning(
                f"{context.author} (ID: {context.author.id}) tried running a command on my DMs, but they're blocked from using RinBot.")
    elif isinstance(error, exceptions.UserNotOwner):
        embed = discord.Embed(
            description="You are not on the RinBot `owners` class, kinda SUS!", color=0xE02B2B)
        await context.send(embed=embed)
        if context.guild:
            bot.logger.warning(
                f"{context.author} (ID: {context.author.id}) tried running a command of class `owner` {context.guild.name} (ID: {context.guild.id}), but they're not a part of this class")
        else:
            bot.logger.warning(
                f"{context.author} (ID: {context.author.id}) tried running a command of class `owner` on my DMs, but they're not a part of this class")
    elif isinstance(error, exceptions.UserNotAdmin):
        embed = discord.Embed(
            description="You are not on the RinBot `admins` class, kinda SUS!", color=0xE02B2B)
        await context.send(embed=embed)
        if context.guild:
            bot.logger.warning(
                f"{context.author} (ID: {context.author.id}) tried running a command of class `admin` {context.guild.name} (ID: {context.guild.id}), but they're not a part of this class")
        else:
            bot.logger.warning(
                f"{context.author} (ID: {context.author.id}) tried running a command of class `admin` on my DMs, but they're not a part of this class")
    elif isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            description="You don't have `"
            + ", ".join(error.missing_permissions)
            + "` permissions, which are necessary to run this command!",
            color=0xE02B2B,)
        await context.send(embed=embed)
    elif isinstance(error, commands.BotMissingPermissions):
        embed = discord.Embed(
            description="I don't have `"
            + ", ".join(error.missing_permissions)
            + "` permissions, which are necessary to run this command!",
            color=0xE02B2B,)
        await context.send(embed=embed)
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            title="Error!",
            description=str(error).capitalize(),
            color=0xE02B2B,)
        await context.send(embed=embed)
    else:
        raise error

# Loads extensions (command cogs)
async def load_extensions() -> None:
    for file in os.listdir(f"{os.path.realpath(os.path.dirname(__file__))}/extensions"):
        if file.endswith(".py"):
            extension = file[:-3]
            try:
                await bot.load_extension(f"extensions.{extension}")
                bot.logger.info(f"Extension loaded '{extension}'")
            except Exception as e:
                exception = f"{type(e).__name__}: {e}"
                bot.logger.error(f"Error while loading extension {extension}\n{exception}")


# Wait 5 seconds when coming from a reset
try:
    if sys.argv[1] == 'reset':
        print('Coming from a reset, waiting for previous instance to finish...')
        time.sleep(5)
except:
    pass

# RUN
asyncio.run(init_db())
asyncio.run(load_extensions())
bot.run(config["token"])
