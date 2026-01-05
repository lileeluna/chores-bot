import os
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import asyncio
import json
import datetime
from dateutil.relativedelta import relativedelta

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user.name} is online!')

CHORES = 'chores.json'

def load_chores():
    try:
        with open(CHORES, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    
def save_chores(chores):
    with open(CHORES, 'w') as f:
        json.dump(chores, f, indent=4)

@bot.command()
async def addchore(ctx, user: discord.Member, chore_name: str, frequency_days: int):
    chores = load_chores()
    
    chores[chore_name] = {
        'user_id': user.id,
        'frequency_days': frequency_days,
        'last_done': None
    }

    save_chores(chores)
    await ctx.send(f'Chore "{chore_name}" added for {user.mention} with frequency {frequency_days} days.')

@bot.command()
async def addweeklychore(ctx, user: discord.Member, chore_name: str):
    chores = load_chores()
    
    chores[chore_name] = {
        'user_id': user.id,
        'frequency_days': 7,
        'last_done': None
    }

    save_chores(chores)
    await ctx.send(f'Weekly chore "{chore_name}" added for {user.mention}.')

@bot.command()
async def removechore(ctx, chore_name: str):
    chores = load_chores()
    
    if chore_name in chores:
        del chores[chore_name]
        save_chores(chores)
        await ctx.send(f'Chore "{chore_name}" removed.')
    else:
        await ctx.send(f'Chore "{chore_name}" not found.')

bot.run(TOKEN)