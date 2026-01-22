import discord
from discord.ext import commands
from src.utils.audit import log_action
import time


def register(bot: commands.Bot):
    @bot.command(name='volume')
    async def _volume(ctx: commands.Context, percent: int):
        """Set volume 0-200"""
        vc = ctx.guild.voice_client
        if not vc or not vc.source:
            await ctx.send('No active audio source.')
            return
        try:
            vol = max(0, min(200, percent)) / 100.0
            if hasattr(vc.source, 'volume'):
                vc.source.volume = vol
            else:
                # wrap in PCMVolumeTransformer
                vc.source = discord.PCMVolumeTransformer(vc.source)
                vc.source.volume = vol
            await ctx.send(f'Set volume to {percent}%')
            await log_action(bot, ctx.author.id, 'volume', {'percent': percent})
        except Exception as exc:
            await ctx.send(f'Failed to set volume: {exc}')
            await log_action(bot, ctx.author.id, 'volume_failed', {'error': str(exc)})

    @bot.tree.command(name='volume')
    @discord.app_commands.describe(percent='Volume percent 0-200')
    async def _volume_slash(interaction: discord.Interaction, percent: int):
        await interaction.response.defer(ephemeral=True)
        perms = interaction.user.guild_permissions
        if not perms.manage_guild:
            await interaction.followup.send('You need the Manage Server permission to use this command.', ephemeral=True)
            return
        # simple per-user cooldown to avoid spam
        if not hasattr(register, '_last_volume'):
            register._last_volume = {}
            register._volume_cooldown = 3.0
        now = time.time()
        last = register._last_volume.get(interaction.user.id, 0)
        if now - last < register._volume_cooldown:
            rem = int(register._volume_cooldown - (now - last))
            await interaction.followup.send(f'Volume is on cooldown. Try again in {rem}s.', ephemeral=True)
            return
        register._last_volume[interaction.user.id] = now
        ctx = await commands.Context.from_interaction(interaction)
        await _volume(ctx, percent=percent)


    class VolumeView(discord.ui.View):
        def __init__(self, bot):
            super().__init__(timeout=300)
            self.bot = bot
            self._last_vol_down: dict[int, float] = {}
            self._vol_down_cooldown = 5.0

        @discord.ui.button(label='Vol +10%', style=discord.ButtonStyle.primary, custom_id='sonus_vol_up')
        async def vol_up(self, button: discord.ui.Button, interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            ctx = await commands.Context.from_interaction(interaction)
            try:
                vc = ctx.guild.voice_client
                if not vc or not vc.source:
                    await interaction.followup.send('No active audio source.', ephemeral=True)
                    return
                current = getattr(vc.source, 'volume', 1.0)
                new = min(2.0, current + 0.1)
                if not hasattr(vc.source, 'volume'):
                    vc.source = discord.PCMVolumeTransformer(vc.source)
                vc.source.volume = new
                await interaction.followup.send(f'Volume: {int(new*100)}%', ephemeral=True)
                await log_action(self.bot, interaction.user.id, 'volume', {'percent': int(new*100)})
            except Exception as exc:
                await interaction.followup.send(f'Failed to change volume: {exc}', ephemeral=True)

        @discord.ui.button(label='Vol -10%', style=discord.ButtonStyle.primary, custom_id='sonus_vol_down')
        async def vol_down(self, button: discord.ui.Button, interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            try:
                # permission check: require Manage Guild to bypass cooldown
                perms = interaction.user.guild_permissions
                now = time.time()
                last = self._last_vol_down.get(interaction.user.id, 0)
                if not perms.manage_guild and now - last < self._vol_down_cooldown:
                    rem = int(self._vol_down_cooldown - (now - last))
                    await interaction.followup.send(f'Volume down is on cooldown. Try again in {rem}s.', ephemeral=True)
                    return

                vc = interaction.guild.voice_client
                if not vc or not vc.source:
                    await interaction.followup.send('No active audio source.', ephemeral=True)
                    return
                current = getattr(vc.source, 'volume', 1.0)
                new = max(0.0, current - 0.1)
                if not hasattr(vc.source, 'volume'):
                    vc.source = discord.PCMVolumeTransformer(vc.source)
                vc.source.volume = new
                self._last_vol_down[interaction.user.id] = now
                await interaction.followup.send(f'Volume: {int(new*100)}%', ephemeral=True)
                await log_action(self.bot, interaction.user.id, 'volume', {'percent': int(new*100), 'via': 'button_down'})
            except Exception as exc:
                await interaction.followup.send(f'Failed to change volume: {exc}', ephemeral=True)

        @discord.ui.button(label='Set Volume', style=discord.ButtonStyle.success, custom_id='sonus_vol_set')
        async def vol_set(self, button: discord.ui.Button, interaction: discord.Interaction):
            class VolumeModal(discord.ui.Modal):
                def __init__(self, bot):
                    super().__init__(title='Set Volume')
                    self.bot = bot
                    self.volume_input = discord.ui.TextInput(label='Volume (0-200)', style=discord.TextStyle.short, placeholder='100', max_length=3)
                    self.add_item(self.volume_input)

                async def on_submit(self, modal_interaction: discord.Interaction):
                    await modal_interaction.response.defer(ephemeral=True)
                    try:
                        # permission: require Manage Guild to set exact numeric volume
                        perms = modal_interaction.user.guild_permissions
                        if not perms.manage_guild:
                            await modal_interaction.followup.send('You need the Manage Server permission to set an exact volume.', ephemeral=True)
                            return

                        percent = int(self.volume_input.value)
                        percent = max(0, min(200, percent))
                        vc = modal_interaction.guild.voice_client
                        if not vc or not vc.source:
                            await modal_interaction.followup.send('No active audio source.', ephemeral=True)
                            return
                        vol = percent / 100.0
                        if not hasattr(vc.source, 'volume'):
                            vc.source = discord.PCMVolumeTransformer(vc.source)
                        vc.source.volume = vol
                        await modal_interaction.followup.send(f'Volume set to {percent}%', ephemeral=True)
                        await log_action(self.bot, modal_interaction.user.id, 'volume', {'percent': percent, 'via': 'modal'})
                    except ValueError:
                        await modal_interaction.followup.send('Please enter a valid integer between 0 and 200.', ephemeral=True)
                    except Exception as exc:
                        await modal_interaction.followup.send(f'Failed to set volume: {exc}', ephemeral=True)

            modal = VolumeModal(self.bot)
            await interaction.response.send_modal(modal)
