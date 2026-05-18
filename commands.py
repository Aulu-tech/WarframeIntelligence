"""User-facing commands for the blacklist bot"""
import nextcord  # Embed/Colour types, UI primitives (View, Button), exception classes
from nextcord.ext import commands  # decorator-based prefix command framework

import storage  # per-guild notification channel + blacklist lookups


class ConfigView(nextcord.ui.View):
    """Button menu shown by %config, locked to the invoker for 60s"""

    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx

    async def interaction_check(self, interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Only the person who ran %config can use these buttons", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            await self.message.edit(view=self)
        except nextcord.HTTPException:
            pass

    @nextcord.ui.button(label="Set this channel", style=nextcord.ButtonStyle.success)
    async def set_here(self, button, interaction):
        storage.set_channel(interaction.guild.id, interaction.channel.id)
        await interaction.response.send_message(f"Notifications will be posted in {interaction.channel.mention}", ephemeral=True)

    @nextcord.ui.button(label="Disable", style=nextcord.ButtonStyle.danger)
    async def disable(self, button, interaction):
        storage.unset_channel(interaction.guild.id)
        await interaction.response.send_message("Notifications disabled for this server", ephemeral=True)

    @nextcord.ui.button(label="Status", style=nextcord.ButtonStyle.secondary)
    async def status(self, button, interaction):
        channel_id = storage.get_channel(interaction.guild.id)
        if channel_id is None:
            msg = "No notification channel set"
        else:
            msg = f"Notifications go to <#{channel_id}>"
        await interaction.response.send_message(msg, ephemeral=True)


def setup(bot, scan_guild, log):
    """Attach all %blacklist and %config commands to the bot

    scan_guild and log are passed in from bot.py to avoid a circular import
    """

    @bot.command(name="config")
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def cmd_config(ctx):
        view = ConfigView(ctx)
        view.message = await ctx.send("Warframe Intelligence configuration", view=view)

    @bot.group(name="blacklist", invoke_without_command=True)
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def blacklist_cmd(ctx):
        await ctx.send(
            "Usage: `%config` (button menu), or `%blacklist set/off/status/check <user>/scan`"
        )

    @blacklist_cmd.command(name="set")
    async def cmd_set(ctx):
        storage.set_channel(ctx.guild.id, ctx.channel.id)
        await ctx.send(f"Notifications will be posted in {ctx.channel.mention}")

    @blacklist_cmd.command(name="off")
    async def cmd_off(ctx):
        storage.unset_channel(ctx.guild.id)
        await ctx.send("Notifications disabled for this server")

    @blacklist_cmd.command(name="status")
    async def cmd_status(ctx):
        channel_id = storage.get_channel(ctx.guild.id)
        if channel_id is None:
            await ctx.send("No notification channel set, run `%config` or `%blacklist set`")
        else:
            await ctx.send(f"Notifications go to <#{channel_id}>")

    @blacklist_cmd.command(name="check")
    async def cmd_check(ctx, user: nextcord.User):
        if not user.is_blacklisted():
            await ctx.send(f"{user.mention} is not on the blacklist")
            return
        reason = storage.get_reason(user.id) or "no reason given"
        await ctx.send(f"{user.mention} **is** blacklisted. Reason: {reason}")

    @blacklist_cmd.command(name="scan")
    async def cmd_scan(ctx):
        await ctx.send(f"Scanning against {len(storage.data['blacklist'])} entries...")
        await scan_guild(ctx.guild)
        await ctx.send("Done")

    @blacklist_cmd.error
    async def blacklist_error(ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You need the Manage Server permission to use this")
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send("This command only works inside a server")
        else:
            log.exception("error in %%blacklist: %s", error)

    @cmd_config.error
    async def config_error(ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You need the Manage Server permission to use this")
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send("This command only works inside a server")
        else:
            log.exception("error in %%config: %s", error)
