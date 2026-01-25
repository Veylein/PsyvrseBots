import discord
from discord import ui
from typing import Dict
from .templates.loader import load_default_template
from .parser import TemplateParser
from .creator import CreationPipeline
from discord import ui


class _PreviewConfirmView(ui.View):
    def __init__(self, plan, pipeline, timeout: int = 120):
        super().__init__(timeout=timeout)
        self.plan = plan
        self.pipeline = pipeline
        self.result = None

    @ui.button(label="Create server", style=discord.ButtonStyle.green)
    async def create(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(thinking=True)
        try:
            report = await self.pipeline.execute(self.plan, actor=interaction.user)
        except Exception as exc:
            await interaction.followup.send(f"Creation failed: {exc}", ephemeral=True)
            self.result = False
            self.stop()
            return
        await interaction.followup.send(f"Conditor completed setup. Created {report['summary']}", ephemeral=True)
        self.result = True
        self.stop()

    @ui.button(label="Cancel", style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("Cancelled setup.", ephemeral=True)
        self.result = False
        self.stop()


class SetupModalStep1(ui.Modal):
    def __init__(self, bot: discord.Client):
        super().__init__(title="Conditor Setup — Step 1/3")
        self.bot = bot
        self.theme = ui.TextInput(label="Server theme / purpose", style=discord.TextStyle.short, required=True)
        self.community_type = ui.TextInput(label="Community type", style=discord.TextStyle.short, required=True)
        self.moderation = ui.TextInput(label="Moderation strictness (low/medium/high)", style=discord.TextStyle.short, required=True)
        self.channel_density = ui.TextInput(label="Preferred channel density (minimal/standard/massive)", style=discord.TextStyle.short, required=True)
        self.primary_language = ui.TextInput(label="Primary language", style=discord.TextStyle.short, required=True)

        self.add_item(self.theme)
        self.add_item(self.community_type)
        self.add_item(self.moderation)
        self.add_item(self.channel_density)
        self.add_item(self.primary_language)

    async def on_submit(self, interaction: discord.Interaction):
        state = {
            "theme": self.theme.value.strip(),
            "community_type": self.community_type.value.strip(),
            "moderation": self.moderation.value.strip(),
            "channel_density": self.channel_density.value.strip(),
            "primary_language": self.primary_language.value.strip(),
        }
        await interaction.response.send_modal(SetupModalStep2(self.bot, state))


class SetupModalStep2(ui.Modal):
    def __init__(self, bot: discord.Client, state: Dict):
        super().__init__(title="Conditor Setup — Step 2/3")
        self.bot = bot
        self.state = state
        self.lore = ui.TextInput(label="Lore or aesthetic description", style=discord.TextStyle.long, required=False, max_length=1000)
        self.emoji_style = ui.TextInput(label="Emoji style preference", style=discord.TextStyle.short, required=False)
        self.voice_text_emphasis = ui.TextInput(label="Voice vs text emphasis", style=discord.TextStyle.short, required=False)
        self.automation_pref = ui.TextInput(label="Automation preference", style=discord.TextStyle.short, required=False)
        self.announcement_freq = ui.TextInput(label="Announcement frequency", style=discord.TextStyle.short, required=False)

        self.add_item(self.lore)
        self.add_item(self.emoji_style)
        self.add_item(self.voice_text_emphasis)
        self.add_item(self.automation_pref)
        self.add_item(self.announcement_freq)

    async def on_submit(self, interaction: discord.Interaction):
        self.state.update({
            "lore": self.lore.value.strip(),
            "emoji_style": self.emoji_style.value.strip(),
            "voice_text_emphasis": self.voice_text_emphasis.value.strip(),
            "automation_pref": self.automation_pref.value.strip(),
            "announcement_freq": self.announcement_freq.value.strip(),
        })
        await interaction.response.send_modal(SetupModalStep3(self.bot, self.state))


class SetupModalStep3(ui.Modal):
    def __init__(self, bot: discord.Client, state: Dict):
        super().__init__(title="Conditor Setup — Step 3/3")
        self.bot = bot
        self.state = state
        self.role_hierarchy = ui.TextInput(label="Role hierarchy depth", style=discord.TextStyle.short, required=False)
        self.accessibility = ui.TextInput(label="Accessibility needs", style=discord.TextStyle.short, required=False)
        self.nsfw_handling = ui.TextInput(label="NSFW handling", style=discord.TextStyle.short, required=False)
        self.event_focus = ui.TextInput(label="Event focus", style=discord.TextStyle.short, required=False)
        self.scalability = ui.TextInput(label="Expansion scalability notes", style=discord.TextStyle.short, required=False)

        self.add_item(self.role_hierarchy)
        self.add_item(self.accessibility)
        self.add_item(self.nsfw_handling)
        self.add_item(self.event_focus)
        self.add_item(self.scalability)

    async def on_submit(self, interaction: discord.Interaction):
        self.state.update({
            "role_hierarchy": self.role_hierarchy.value.strip(),
            "accessibility": self.accessibility.value.strip(),
            "nsfw_handling": self.nsfw_handling.value.strip(),
            "event_focus": self.event_focus.value.strip(),
            "scalability": self.scalability.value.strip(),
        })

        await interaction.response.defer(thinking=True)

        template = load_default_template()
        parser = TemplateParser(template)
        plan = parser.generate(self.state, actor_id=str(interaction.user.id))

        # send a deterministic preview and ask the user to confirm
        summary = plan.get('summary', '')
        preview_lines = [f"**Preview:** {summary}"]
        # show first categories and channel counts
        for c in plan.get('categories', [])[:6]:
            preview_lines.append(f"- {c['name']}: {len(c['channels'])} channels")

        preview_text = "\n".join(preview_lines)

        pipeline = CreationPipeline(interaction.guild)
        view = _PreviewConfirmView(plan, pipeline)
        await interaction.followup.send(preview_text, ephemeral=True, view=view)
        # Wait until user interacts or view times out
        await view.wait()
        if view.result is None:
            await interaction.followup.send("Preview timed out — setup cancelled.", ephemeral=True)
