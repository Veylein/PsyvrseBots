import discord
from discord import app_commands
from discord.ext import commands

from src.logger import setup_logger
from src.utils.audit import log_action

logger = setup_logger(__name__)

FEEDBACK_CHANNEL = 1462019751218778112


class Feedback(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="feedback")
    async def feedback_prefix(self, ctx: commands.Context, *, text: str):
        """Prefix command: S!feedback <text>"""
        success = await _handle_feedback(self.bot, author=ctx.author, content=text)
        if success:
            e = discord.Embed(title="Feedback Received", description="Thanks — your feedback was sent to the devs.", color=0x1DB954)
            try:
                await ctx.send(embed=e)
            except Exception:
                try:
                    await ctx.send("✅ Thanks — your feedback was sent to the devs.")
                except Exception:
                    pass
            try:
                await ctx.author.send(embed=e)
            except Exception:
                try:
                    await ctx.author.send("✅ Thanks — your feedback was sent to the devs.")
                except Exception:
                    pass
        else:
            e = discord.Embed(title="Feedback Delivery Failed", description="Sorry — I couldn't deliver your feedback. The devs have been notified.", color=0xE74C3C)
            try:
                await ctx.send(embed=e)
            except Exception:
                try:
                    await ctx.send("❌ Sorry — I couldn't deliver your feedback. The devs have been notified.")
                except Exception:
                    pass
        await log_action(self.bot, ctx.author.id, "feedback_prefix", {"text_preview": text[:200], "delivered": success})

    @app_commands.command(name="feedback", description="Send feedback to the devs")
    @app_commands.describe(text="Your feedback")
    async def feedback_slash(self, interaction: discord.Interaction, text: str):
        """Slash command: /feedback <text>"""
        await interaction.response.defer(ephemeral=True)
        success = await _handle_feedback(self.bot, author=interaction.user, content=text)
        if success:
            e = discord.Embed(title="Feedback Received", description="Thanks — your feedback was sent to the devs.", color=0x1DB954)
            try:
                await interaction.followup.send(embed=e, ephemeral=True)
            except Exception:
                try:
                    await interaction.followup.send("✅ Thanks — your feedback was sent to the devs.", ephemeral=True)
                except Exception:
                    pass
            try:
                await interaction.user.send(embed=e)
            except Exception:
                try:
                    await interaction.user.send("✅ Thanks — your feedback was sent to the devs.")
                except Exception:
                    pass
        else:
            e = discord.Embed(title="Feedback Delivery Failed", description="Sorry — I couldn't deliver your feedback. The devs have been notified.", color=0xE74C3C)
            try:
                await interaction.followup.send(embed=e, ephemeral=True)
            except Exception:
                try:
                    await interaction.followup.send("❌ Sorry — I couldn't deliver your feedback. The devs have been notified.", ephemeral=True)
                except Exception:
                    pass
        await log_action(self.bot, interaction.user.id, "feedback_slash", {"text_preview": text[:200], "delivered": success})


async def _handle_feedback(bot: commands.Bot, author: discord.abc.User, content: str) -> bool:
    """Deliver feedback to the configured channel, with owner DM fallback and audit logging.

    Returns True if delivered to the dev channel or an owner; False otherwise.
    """
    e = discord.Embed(title="User Feedback", color=0x1DB954)
    e.add_field(name="From", value=f"{author} (ID: {author.id})", inline=False)
    safe_content = (content or "(empty)")[:3900]
    e.description = safe_content
    text_payload = f"[{getattr(author, 'display_name', str(author))}] ID:{author.id} says:\n```\n{safe_content[:1900]}\n```"
    delivered_any = False
    try:
        ch = bot.get_channel(FEEDBACK_CHANNEL)
        if ch is None:
            ch = await bot.fetch_channel(FEEDBACK_CHANNEL)
        try:
            await ch.send(content=text_payload, embed=e)
        except Exception:
            await ch.send(text_payload)
        return True
    except Exception:
        logger.exception("Failed to deliver feedback to dev channel")
    # fallback: DM owners
    try:
        for owner_id in getattr(bot, "owner_ids", []) or []:
            try:
                owner = await bot.fetch_user(owner_id)
                if owner:
                    try:
                        await owner.send(f"Feedback delivery failed for message from {author}:", embed=e)
                    except Exception:
                        try:
                            await owner.send(f"Feedback delivery failed for message from {author}:\n{(content or '')[:1500]}")
                        except Exception:
                            logger.exception("Failed sending plain fallback to owner %s", owner_id)
                    delivered_any = True
            except Exception:
                logger.exception("Failed sending feedback DM to owner %s", owner_id)
    except Exception:
        logger.exception("Failed to deliver feedback to owners as fallback")

    try:
        await log_action(bot, author.id, "feedback_failed_delivery", {"text_preview": (content or "")[:200], "delivered_to_owner": delivered_any})
    except Exception:
        logger.exception("Failed to write feedback failure audit entry")

    return delivered_any


async def setup(bot: commands.Bot):
    # Prevent duplicate cog registration if an identical Feedback cog
    # (e.g. src.commands.feedback) is already loaded in the bot.
    if bot.get_cog('Feedback') is not None:
        logger.info('Feedback cog already loaded; skipping duplicate registration')
        return
    await bot.add_cog(Feedback(bot))
