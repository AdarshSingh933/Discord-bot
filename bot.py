import discord
from discord.ext import commands, tasks
from discord import Interaction
from discord.ui import Button, View, Modal, TextInput
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

# Load environment variables from .env file
load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='$', intents=intents)

# Dictionary to store standup settings
standups = {}

class StandupModal(discord.ui.Modal, title="Standup Setup"):
    # Define the fields for the modal
    channel_name = TextInput(label="Channel Name", placeholder="Enter the channel name")
    standup_time = TextInput(label="Standup Time", placeholder="HH:MM")
    standup_details = TextInput(label="Standup Details", style=discord.TextStyle.paragraph, placeholder="Details for the standup")
    team_name = TextInput(label="Team Name", placeholder="Enter the team name")

    async def on_submit(self, interaction: discord.Interaction):
        # Process the collected data
        await interaction.response.send_message(f"Standup setup complete. Details:\n"
                                                f"Channel: {self.channel_name}\n"
                                                f"Time: {self.standup_time}\n"
                                                f"Details: {self.standup_details}\n"
                                                f"Team: {self.team_name}", ephemeral=True)

        await set_standup(interaction, self.channel_name, self.standup_time, self.standup_details, self.team_name)

# Function to set the standup
async def set_standup(interaction, channel_name, time, standup, team_name):
    # Strip extra spaces and convert to lowercase for case-insensitive search
    channel_name_clean = channel_name.value.strip().lower()


    # Find the channel in the guild, ignore case when searching
    target_channel = discord.utils.get(interaction.guild.channels, name=channel_name_clean)
    if not target_channel:
        await interaction.followup.send(f'Channel "{channel_name}" not found. Please make sure the name is correct.', ephemeral=True)
        return

    try:
        standup_time = datetime.strptime(time, '%H:%M').time()
    except ValueError:
        await interaction.followup.send('Invalid time format. Please use HH:MM.', ephemeral=True)
        return

    standup_time = datetime.combine(datetime.today(), standup_time)
    if standup_time < datetime.now():
        standup_time += timedelta(days=1)  # Schedule for the next day if the time has already passed

    standups[interaction.guild.id] = {
        'channel': target_channel.id,
        'standup_time': standup_time,
        'standup': standup,
        'team_name': team_name
    }

    await interaction.followup.send(f'Standup for team "{team_name}" is set at {standup_time.strftime("%H:%M")}.')
    await target_channel.send(f'Standup Reminder: A standup is scheduled for {standup_time.strftime("%H:%M")}.')

class StandupForm(discord.ui.View):
    @discord.ui.button(label="Start Standup Setup", style=discord.ButtonStyle.primary)
    async def start_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = StandupModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Standup setup has been canceled.", ephemeral=True)
        self.stop()  # Stop the form interaction

@bot.command()
async def standup(ctx):
    """Initiates the standup setup process"""
    view = StandupForm()
    await ctx.send("Click the button below to start the standup setup process:", view=view)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    check_standups.start()  # Start the task to check for standups

@tasks.loop(minutes=1)
async def check_standups():
    """Check if any standup is due"""
    now = datetime.now()
    for guild_id, settings in standups.items():
        standup_time = settings['standup_time']
        if standup_time - timedelta(minutes=15) <= now <= standup_time:
            channel = bot.get_channel(settings['channel'])
            if channel:
                await channel.send(f'Reminder: Please update your standup for team "{settings["team_name"]}".')

bot.run(os.getenv('TOKEN'))
