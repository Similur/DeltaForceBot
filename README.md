# Delta Force Build Bot

A Discord bot I put together to make looking up **Delta Force** weapon builds a little easier. Instead of opening a browser every time, you can use `/build` to pull up a loadout in your Discord server.

The bot looks at public weapon pages on [CODMunity](https://codmunity.gg/delta-force) and tries to grab the build's attachments, import code, image, and estimated cost when those details are available.

## What it does

- Adds a `/build` slash command with weapon-name autocomplete.
- Lets you choose between **Expensive / Meta** and **Budget / Operations**.
- Sends the build as a Discord embed, with a link back to the source.
- Handles missing builds and temporary website errors without crashing the bot.
- Reads the Discord token and server ID from environment variables, so they don't need to be in the code.

**A note on build types:** The Budget option looks for an Operations loadout. Operations doesn't necessarily mean cheap, and the source doesn't always publish a price. The bot won't make up missing costs or loadouts.

## Getting started

You'll need **Python 3.10+**, a Discord bot application, and permission to add that bot to a server.

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and add your own values:

   ```dotenv
   DISCORD_BOT_TOKEN=your_bot_token_here
   DISCORD_GUILD_ID=your_server_id_here
   ```

3. Invite your bot to the server with the `bot` and `applications.commands` scopes, then start it:

   ```bash
   python bot.py
   ```

4. In Discord, try `/build weapon:M4A1 category:Expensive`.

For the server ID, enable Developer Mode in Discord and copy your server's ID. Keep your `.env` file private: it's already excluded by `.gitignore`.

## Project files

- `bot.py` — Discord command, autocomplete, and embeds.
- `scraper.py` — Requests and parsing for public weapon pages.
- `tests/` — Small parser tests that don't call Discord or the live website.
- `.env.example` — Example config, with no real credentials.

Run the tests with:

```bash
python -m unittest discover -s tests -v
```

## Things to know

This is a personal learning/portfolio project, not an official Delta Force or CODMunity tool. It's based on publicly viewable pages and doesn't use a private API. Since the website can change its HTML at any time, scraping may need maintenance; not every weapon or build will be available. Please respect the site's usage rules and avoid sending unnecessary requests.

I made this to practice Python automation, working with third-party web content, and building Discord slash commands. It isn't meant to be a production-grade integration.
