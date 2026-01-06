import os
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import asyncio
import json
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Set up bot intents and command prefix
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

CHORES = 'chores.json'
CHORE_ROTATION = 'chore_rotation.json'

# Debug message to show bot is online
@bot.event
async def on_ready():
    print(f'{bot.user.name} is online!')

# Helper functions to load and save chores
def load_chores():
    try:
        with open(CHORES, 'r') as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    
def save_chores(chores):
    with open(CHORES, 'w') as f:
        json.dump(chores, f, indent=4)

# Helper functions to load and save chore rotation
def load_chore_rotation():
    try:
        with open(CHORE_ROTATION, 'r') as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    
def save_chore_rotation(rotation):
    with open(CHORE_ROTATION, 'w') as f:
        json.dump(rotation, f, indent=4)

# Command to add users to the chore rotation
@bot.command()
async def adduser(ctx, *users: discord.Member):
    curr_rotation = load_chore_rotation()
    rotation = []
    for user in users:
        if user.id in curr_rotation:
            await ctx.send(f'{user.mention} is already in the chore rotation.')
        else:
            rotation.append(user.id)
    new_rotation = curr_rotation + rotation
    save_chore_rotation(new_rotation)
    if len(rotation) == 1:
        if len(new_rotation) == 1:
            await ctx.send(f'Added 1 user to the chore rotation. Total: 1 user.')
        await ctx.send(f'Added 1 user to the chore rotation. Total: {len(new_rotation)} users.')
    else:
        await ctx.send(f'Added {len(rotation)} users to the chore rotation. Total: {len(new_rotation)} users.')

# Command to remove a user from the chore rotation
@bot.command()
async def removeuser(ctx, user: discord.Member):
    user_id = user.id
    rotation = load_chore_rotation()
    if user_id in rotation:
        user = await bot.fetch_user(user_id)
        rotation.remove(user_id)
        save_chore_rotation(rotation)
        await ctx.send(f'Removed user ID {user.mention} from the chore rotation.')

# Command to clear the chore rotation
@bot.command()
async def clearrotation(ctx):
    save_chore_rotation([])
    await ctx.send('Cleared the chore rotation.')

# Command to list the chore rotation
@bot.command()
async def listrotation(ctx):
    rotation = load_chore_rotation()
    if not rotation:
        await ctx.send('Chore rotation is empty.')
        return

    message = 'Chore Rotation:\n'
    for user_id in rotation:
        user = await bot.fetch_user(user_id)
        message += f'- {user.mention if user else "Unknown User"}\n'

    await ctx.send(message)

# Helper function to add a chore
async def __addchore(ctx, user: discord.Member, chore_name: str, frequency_days: int):
    chores = load_chores()

    if user.id not in load_chore_rotation():
        await ctx.send(f'{user.mention} is not in the chore rotation. Please add them first using !adduser.')
        return
    
    chores[chore_name] = {
        'user_id': user.id,
        'frequency_days': frequency_days,
        'last_done': None
    }

    save_chores(chores)
    await ctx.send(f'Chore "{chore_name}" added for {user.mention} with frequency {frequency_days} days.')

# Command to add a chore with custom frequency
@bot.command()
async def addchore(ctx, user: discord.Member, chore_name: str, frequency_days: int):
    await __addchore(ctx, user, chore_name, frequency_days)

# Command to add a weekly chore
@bot.command()
async def addweeklychore(ctx, user: discord.Member, chore_name: str):
    await __addchore(ctx, user, chore_name, 7)

# Command to add a monthly chore
@bot.command()
async def addmonthlychore(ctx, user: discord.Member, chore_name: str):
    curr_month = datetime.now(timezone.utc).month
    days_in_month = (datetime(datetime.now(timezone.utc).year, curr_month % 12 + 1, 1) - relativedelta(days=1)).day
    await __addchore(ctx, user, chore_name, days_in_month)

# Command to remove a chore
@bot.command()
async def removechore(ctx, chore_name: str):
    chores = load_chores()
    
    if chore_name in chores:
        del chores[chore_name]
        save_chores(chores)
        await ctx.send(f'Chore "{chore_name}" removed.')
    else:
        await ctx.send(f'Chore "{chore_name}" not found.')

# Command to list all chores
@bot.command()
async def listchores(ctx):
    chores = load_chores()
    
    if not chores:
        await ctx.send('No chores found.')
        return

    message = 'Chores:\n'
    for chore_name, details in chores.items():
        print(details['user_id'])
        user = await bot.fetch_user(details['user_id'])
        last_done = details['last_done'] or 'Never'
        message += f'- {chore_name}: assigned to {user.mention if user else "Unknown User"}, frequency {details["frequency_days"]} days, last done: {last_done}\n'

    await ctx.send(message)

# Command to mark a chore as done
@bot.command()
async def donechore(ctx, chore_name: str):
    chores = load_chores()
    
    if chore_name in chores:
        chores[chore_name]['last_done'] = datetime.now(timezone.utc).date().isoformat()
        save_chores(chores)
        await ctx.send(f'Chore "{chore_name}" marked as done.')
    else:
        await ctx.send(f'Chore "{chore_name}" not found.')

# Helper function to check next due date for a chore
async def __nextchore(ctx, chore_name: str):
    chores = load_chores()
    
    if chore_name in chores:
        last_done_str = chores[chore_name]['last_done']
        frequency_days = chores[chore_name]['frequency_days']
        
        if last_done_str:
            last_done = datetime.fromisoformat(last_done_str).date()
            next_due = last_done + relativedelta(days=frequency_days)
            await ctx.send(f'Next due date for chore "{chore_name}" is {next_due.isoformat()}.')
        else:
            await ctx.send(f'Chore "{chore_name}" has never been done. It is due now.')
    else:
        await ctx.send(f'Chore "{chore_name}" not found.')

# Command to check next due date for a chore
@bot.command()
async def nextchore(ctx, chore_name: str):
    await __nextchore(ctx, chore_name)

bot.run(TOKEN)
