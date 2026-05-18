# Warframe Intelligence

A community-run blacklist bot for Warframe Discord servers

Warframe Intelligence sits in any number of partner servers and quietly watches for users who have been flagged as bad actors by the central Warframe Intelligence community. When a flagged user joins, or is already a member, the bot pings a moderator channel (or a DM) so your staff can act on it. That is all it does. No moderation actions, no kicks, no bans, no data leaving your server. Just a heads-up

The blacklist itself is sourced from a single, public Discord channel inside the Warframe Intelligence community, which makes the source of truth fully auditable. If you want to know why someone is on the list, you can read the original message yourself

## Why this exists

Bad actors usually don't stop at one warframe clan, they crave MORE
We don't want them to hop between our communities, so we have a shared
collaboration we call Warframe Intelligence

This project is intentionally:

- **Open source.** Anyone can read the code, propose changes, or fork it
- **Unbranded.** The bot just shows up as "Warframe Intelligence". It is not tied to any single server, person, or trade community
- **Read-only on your server.** It does not need ban, kick, or message-management permissions
- **Backed by a public channel, not a private database.** The data is "whatever is posted in the source channel", nothing more
(public within warframe intelligence)

## How it works

1. The bot is in the central Warframe Intelligence guild and watches a single channel for new posts
2. Any Discord user ID that appears in a message in that channel is added to the local SQLite blacklist
3. On startup the bot also fetches the most recent messages from that channel and reconciles them against the local copy, so nothing is missed if the bot was offline when a new entry was posted
4. In every other server the bot is in, it listens for `on_member_join`, and periodically scans the existing member list, so users who were already in the server when they got blacklisted are still caught
5. When a match is found, the bot sends a notification according to that server's configuration (a channel ping, a DM to a chosen moderator, or both), and remembers that it already notified so it does not spam

## Setup

### Requirements

- Python 3.11+
- A Discord bot token, with the **Server Members Intent** enabled in the developer portal
- The bot must be invited to the central Warframe Intelligence guild and to each partner server

### Install

```powershell
git clone https://github.com/your-org/WarframeIntelligence.git
cd WarframeIntelligence
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Configure

The bot reads its token from a plain text file called `token.txt` in the project root. Create it and paste the bot token inside, nothing else

```powershell
Set-Content -Path token.txt -Value "YOUR_BOT_TOKEN_HERE"
```

The source guild and channel are hardcoded in `config.py` on purpose, since they are part of the project identity and not something individual hosts should be reconfiguring

### Run

```powershell
python bot.py
```

## Per-server configuration

In the channel you want notifications in, an admin runs:

```
%blacklist set
```

That's it. The bot will post in that channel whenever a blacklisted user joins or is found in the existing member list. Other commands:

- `%blacklist off` stops notifications in this server
- `%blacklist status` shows the current notification channel
- `%blacklist check @user` checks a specific user against the blacklist
- `%blacklist scan` forces an immediate scan of the server's members

All commands require the `Manage Server` permission

## Privacy and data

The bot stores only:

- Discord user IDs found in the central blacklist channel, with the optional reason text from the same message
- The notification channel id for each opted-in server
- A record of which blacklisted users have already been announced in each server, so the same person is not announced repeatedly

Everything lives in a single `data.json` file next to the bot. No message content from your server is ever stored or transmitted

## Contributing

Pull requests welcome. The whole thing is four files:

- `config.py` the two hardcoded IDs
- `storage.py` JSON-backed state
- `patches.py` adds `is_blacklisted()` onto `nextcord.User` and `nextcord.Member`
- `bot.py` everything else

## License

MIT. See `LICENSE`
