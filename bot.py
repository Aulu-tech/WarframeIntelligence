"""Warframe Intelligence blacklist bot"""
import logging            # stdlib structured logging, used instead of bare print
import re                 # snowflake-ID extraction from source-channel messages
from pathlib import Path  # locate token.txt next to this file, OS-agnostic

import nextcord  # Discord API client and types (Embed, Intents, exceptions)
from nextcord.ext import commands, tasks  # Bot framework + decorator for periodic_scan

import commands as wfi_commands  # %config and %blacklist command tree, local module
import patches  # monkeypatches is_blacklisted onto nextcord.User/Member
import storage  # JSON-backed state (blacklist, per-guild channel, notified set)
from config import SOURCE_CHANNEL_ID, SOURCE_GUILD_ID  # hardcoded project identity

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("wfi")

# Matches any run of 17-20 digits that isn't part of a longer digit run.
# Discord user IDs are 64-bit snowflakes:
#   17 digits: oldest accounts from ~2015
#   19 digits: typical accounts today
#   20 digits: theoretical max (2^64 - 1 = 18446744073709551615), so {17,20} covers the entire snowflake space
# The lookarounds prevent matching the middle of a longer number like a timestamp
ID_RE = re.compile(r"(?<!\d)(\d{17,20})(?!\d)")

intents = nextcord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="%", intents=intents, help_command=None)


async def ingest(message):
    """Parse one source-channel message, add any new IDs, notify partner guilds"""
    ids = [int(m) for m in ID_RE.findall(message.content)]
    if not ids:
        return
    await message.add_reaction("✅")
    reason = ID_RE.sub("", message.content).strip(" \t\n\r-:,.") or None
    for uid in dict.fromkeys(ids):  # dedup while preserving order
        if not storage.add_blacklisted(uid, reason, message.id):
            continue
        log.info("blacklisted %d", uid)
        for guild in bot.guilds:
            if guild.id == SOURCE_GUILD_ID:
                continue
            member = guild.get_member(uid)
            if member is not None:
                await notify(guild, member)


async def notify(guild, member):
    """Send a notification for one match, deduped per (guild, user)"""
    if storage.was_notified(guild.id, member.id):
        return
    channel_id = storage.get_channel(guild.id)
    if channel_id is None:
        return
    channel = guild.get_channel(channel_id)
    if not isinstance(channel, nextcord.TextChannel):
        return
    reason = storage.get_reason(member.id) or "no reason given"
    embed = nextcord.Embed(
        title="Blacklisted user detected",
        description=f"{member.mention} (`{member.id}`) is on the Warframe Intelligence blacklist",
        colour=nextcord.Colour.red(),
    )
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Account created", value=f"<t:{int(member.created_at.timestamp())}:R>")
    if member.joined_at:
        embed.add_field(name="Joined server", value=f"<t:{int(member.joined_at.timestamp())}:R>")
    if member.display_avatar:
        embed.set_thumbnail(url=member.display_avatar.url)
    try:
        await channel.send(embed=embed)
        storage.mark_notified(guild.id, member.id)
    except (nextcord.Forbidden, nextcord.HTTPException) as exc:
        log.warning("failed to post in %s/%d: %s", guild.name, channel.id, exc)


async def scan_guild(guild):
    """Check every blacklisted user against one guild's member cache"""
    if guild.id == SOURCE_GUILD_ID:
        return
    for key in list(storage.data["blacklist"]):
        member = guild.get_member(int(key))
        if member is not None:
            await notify(guild, member)


@bot.event
async def on_message(message):
    await bot.process_commands(message)
    if message.author.bot:
        return
    if getattr(message.channel, "id", None) == SOURCE_CHANNEL_ID:
        await ingest(message)


@bot.event
async def on_member_join(member):
    if member.is_blacklisted():
        await notify(member.guild, member)


@bot.event
async def on_guild_join(guild):
    await scan_guild(guild)


@tasks.loop(minutes=30)
async def periodic_scan():
    for guild in bot.guilds:
        await scan_guild(guild)


@bot.event
async def on_ready():
    if getattr(bot, "_booted", False):
        return
    bot._booted = True
    log.info("logged in as %s, %d guild(s)", bot.user, len(bot.guilds))
    guild = bot.get_guild(SOURCE_GUILD_ID)
    channel = guild and guild.get_channel(SOURCE_CHANNEL_ID)
    if isinstance(channel, nextcord.TextChannel):
        # Backfill the last 10 messages in case any were posted while we were offline
        async for m in channel.history(limit=10, oldest_first=True):
            await ingest(m)
    periodic_scan.start()


wfi_commands.setup(bot, scan_guild, log)


if __name__ == "__main__":
    token_file = Path(__file__).resolve().parent / "token.txt"
    if not token_file.exists() or not token_file.read_text(encoding="utf-8").strip():
        raise SystemExit(f"paste your bot token into {token_file}")
    patches.install()
    storage.load()
    try:
        bot.run(token_file.read_text(encoding="utf-8").strip())
    except KeyboardInterrupt:
        pass
