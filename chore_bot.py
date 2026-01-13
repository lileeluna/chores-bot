import os
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import asyncio
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta
import re

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Set up bot intents and command prefix
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

CHORES = 'chores.json'
CHORE_ROTATION = 'chore_rotation.json'
SMILEY_SYSTEM = 'smiley_system.json'

class ChoreBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.chore_check.start()

    def cog_unload(self):
        self.chore_check.cancel()

    @tasks.loop(hours=24)
    async def chore_check(self):
        print("Checking for due chores...")
        chores = load_chores()
        time_now = datetime.now().astimezone().date()
        for chore_name, details in chores.items():
            last_done_str = details['last_done']
            if not last_done_str:
                continue

            last_done = datetime.fromisoformat(last_done_str).date()
            frequency_days = details['frequency_days']
            next_due = last_done + relativedelta(days=frequency_days)

            if time_now >= next_due:
                assigned_to = details['assigned_to']
                channel = discord.utils.get(self.bot.get_all_channels(), name='bot-test')
                if channel:
                    await channel.send(f'<@{assigned_to}> Please complete "{chore_name}" as soon as possible. Thank you!')

# Debug message to show bot is online
@bot.event
async def on_ready():
    await bot.add_cog(ChoreBot(bot))
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

# Helper functions to load and save smiley system
def load_smiley_system():
    try:
        with open (SMILEY_SYSTEM, 'r') as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    
def save_smiley_system(smiley_system):
    with open(SMILEY_SYSTEM, 'w') as f:
        json.dump(smiley_system, f, indent=4)

# Helper function to add a smiley
def add_smiley(user_id: int, chore: str):
    smiley_system = load_smiley_system()
    if str(user_id) not in smiley_system:
        smiley_system[str(user_id)] = {}
    if chore not in smiley_system[str(user_id)]:
        smiley_system[str(user_id)][chore] = 1
    else:
        smiley_system[str(user_id)][chore] += 1
    save_smiley_system(smiley_system)

# Helper function to remove a smiley
def remove_smiley(user_id: int, chore: str):
    smiley_system = load_smiley_system()
    if str(user_id) not in smiley_system:
        smiley_system[str(user_id)] = {}
    if chore not in smiley_system[str(user_id)]:
        smiley_system[str(user_id)][chore] = 0
    else:
        smiley_system[str(user_id)][chore] -= 1
    if smiley_system[str(user_id)][chore] < 0:
        smiley_system[str(user_id)][chore] = 0
    save_smiley_system(smiley_system)

# Helper function to get smiley count
def get_smileys(user_id: int, chore: str):
    smiley_system = load_smiley_system()
    if str(user_id) not in smiley_system:
        return 0
    if chore not in smiley_system[str(user_id)]:
        return 0
    return smiley_system[str(user_id)][chore]

# Command to view smileys for a user
@bot.command()
async def viewsmileys(ctx, user: discord.Member = None):
    if user is None:
        user = ctx.author
    smiley_system = load_smiley_system()
    user_id = str(user.id)
    if user_id not in smiley_system or not smiley_system[user_id]:
        await ctx.send(f'{user.mention} has no smileys recorded.')
        return
    for chore, count in smiley_system[user_id].items():
        await ctx.send(f'{chore.title()}: {user.mention} has {count} smileys.')

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

    message = 'Default Chore Rotation:\n'
    for user_id in rotation:
        user = await bot.fetch_user(user_id)
        message += f'- {user.mention if user else "Unknown User"}\n'

    await ctx.send(message)

# Helper function to get the next user in rotation
def get_next_user_in_rotation(rotation: list[int], current_user_id: int) -> int:
    if len(rotation) == 1:
        return rotation[0] if rotation else None
    
    if current_user_id not in rotation:
        return rotation[0] if rotation else None
    current_index = rotation.index(current_user_id)
    next_index = (current_index + 1) % len(rotation)
    return rotation[next_index]

# Helper function to add a chore
async def __addchore(ctx, user: discord.Member, chore_name: str, frequency_days: int, rotation: str = None):
    chores = load_chores()

    if chore_name in chores:
        await ctx.send(f'Chore "{chore_name}" already exists! Please choose a different name or remove the existing chore first.')
        return

    if user.id not in load_chore_rotation():
        await ctx.send(f'{user.mention} is not in the chore rotation. Please add them first using !adduser.')
        return
    
    if rotation is None:
        rotation = load_chore_rotation()
    else:
        rotation = [int(uid) for uid in re.findall(r'<@!?(\d+)>', rotation)]

    if user.id not in rotation:
        rotation.append(user.id)
    
    chores[chore_name] = {
        'assigned_to': user.id,
        'frequency_days': frequency_days,
        'last_done': None,
        'last_done_by': None,
        'rotation': rotation
    }

    save_chores(chores)
    await ctx.send(f'Chore "{chore_name}" added for {user.mention} with frequency {frequency_days} days.')

# Command to add a chore with custom frequency
@bot.command()
async def addchore(ctx, user: discord.Member, chore_name: str, frequency_days: int, rotation: str = None):
    await __addchore(ctx, user, chore_name, frequency_days, rotation)

# Command to add a weekly chore
@bot.command()
async def addweeklychore(ctx, user: discord.Member, chore_name: str, rotation: str = None):
    await __addchore(ctx, user, chore_name, 7, rotation)

# Command to add a monthly chore
@bot.command()
async def addmonthlychore(ctx, user: discord.Member, chore_name: str, rotation: str = None):
    curr_month = datetime.now().astimezone().month
    days_in_month = (datetime(datetime.now().astimezone().year, curr_month % 12 + 1, 1) - relativedelta(days=1)).day
    await __addchore(ctx, user, chore_name, days_in_month, rotation)

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

# Command to clear all chores
@bot.command()
async def clearchores(ctx):
    save_chores({})
    await ctx.send('All chores cleared.')

# Command to list all chores
@bot.command()
async def listchores(ctx):
    chores = load_chores()
    
    if not chores:
        await ctx.send('No chores found.')
        return

    message = 'Chores:\n'
    for chore_name, details in chores.items():
        user = await bot.fetch_user(details['assigned_to'])
        last_done = details['last_done'] or 'Never'
        last_done_by = details['last_done_by']
        if last_done_by:
            last_done += f' by <@{last_done_by}>'
        message += f'- {chore_name}: assigned to {user.mention if user else "Unknown User"}, frequency {details["frequency_days"]} days, last done: {last_done}\n'

    await ctx.send(message)

# Helper function to schedule chore reminder
async def schedule_chore_reminder(ctx, chore_name, assigned_to, delay_seconds):
    await asyncio.sleep(delay_seconds)
    chores = load_chores()
    if chore_name in chores:
        await ctx.send(f'<@{assigned_to}> Please do "{chore_name}" whenever possible. Thank you!')

# Command to mark a chore as done
@bot.command()
async def donechore(ctx, chore_name: str):
    chores = load_chores()
    user = ctx.author

    if chore_name not in chores:
        await ctx.send(f'Chore "{chore_name}" not found.')
        return

    if user.id == chores[chore_name]['assigned_to']:
        while True:
            assigned_to = get_next_user_in_rotation(chores[chore_name]['rotation'], user.id)
            if get_smileys(assigned_to, chore_name) == 0:
                chores[chore_name]['assigned_to'] = assigned_to
            else:
                remove_smiley(assigned_to, chore_name)
    else:
        add_smiley(user.id, chore_name)

    chores[chore_name]['last_done_by'] = user.id
    chores[chore_name]['last_done'] = datetime.now().astimezone().date().isoformat()
    save_chores(chores)
    await ctx.send(f'Chore "{chore_name}" marked as done.')

    next_due = chores[chore_name]['frequency_days']
    remaining_time_in_day = 86400 - (datetime.now().astimezone().hour * 3600 + datetime.now().astimezone().minute * 60 + datetime.now().astimezone().second)
    next_due_seconds = (next_due * 24 * 60 * 60) + remaining_time_in_day
    next_due_seconds *= 0.00001
    asyncio.create_task(schedule_chore_reminder(ctx, chore_name, assigned_to, next_due_seconds))

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
