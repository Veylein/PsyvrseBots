import discord
from discord.ext import commands
from discord import app_commands

class Activities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Defines the custom Ludus Games activity ID
    # This application hosts the suite of arcade/board/card games
    ACTIVITIES = {
        "ludus": 1438766171338838048
    }

    @app_commands.command(name="activity", description="Start the Ludus Games Activity (Arcade, Board Games, Cards & More!)")
    async def activity_slash(self, interaction: discord.Interaction):
        """Starts the Ludus Games voice channel activity."""
        # Check voice state
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ You must be in a voice channel first!", ephemeral=True)
            return

        channel = interaction.user.voice.channel
        activity_id = self.ACTIVITIES["ludus"]

        # ------------------------------------------------------------------------------------------------
        # NOTE: For this to work, the Application with ID 1438766171338838048 MUST be configured in the
        # Discord Developer Portal with the 'Embedded App URL' pointing to where 'LudusGames' is hosted.
        # ------------------------------------------------------------------------------------------------

        try:
            invite = await channel.create_invite(
                target_application_id=activity_id,
                target_type=discord.InviteTarget.embedded_application,
                max_age=3600,
                max_uses=0
            ) 
            await interaction.response.send_message(
                f"🚀 **Ludus Games** started in {channel.mention}!\n\n"
                f"Play Arcade, Board Games, Cards, and more here:\n"
                f"👉 **[Click to Join Activity]({invite.url})**"
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to create invites in that channel.", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to start activity: {str(e)}", 
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Activities(bot))
