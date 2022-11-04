import discord
from discord import app_commands


class Bot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.synced = False

    async def on_ready(self):
        await self.wait_until_ready()
        if not self.synced:
            await tree.sync(guild=discord.Object(id=1038138701961769021))
            self.synced = True
        print(f"we have logged in as {self.user}.")


bot = Bot()
tree = app_commands.CommandTree(bot)


@tree.command(guild=discord.Object(id=1038138701961769021), name="test", description="testing")
async def self(interaction: discord.Interaction, name: str):
    await interaction.response.send_message(f"I am working! {name}", ephemeral=True)


bot.run("Token")
