# SneakerCheckPriceBot

[Read in Russian](./README_RU.md)

Telegram bot for searching and comparing sneaker prices, as well as getting the latest sneaker news.

## Description
SneakerCheckPriceBot is a modern Telegram bot that helps you quickly find up-to-date prices for sneakers from popular websites and stay informed about the latest industry news. The bot is designed for sneaker enthusiasts, resellers, collectors, and anyone who wants to save time searching for the best deals.

The bot works fully automatically, supports asynchronous request processing, and is designed to handle many users at once.

## Features
- 🔍 **Price check** — find the best deals for your favorite sneaker models.
- 🆕 **News** — get the latest sneaker news from the past 24 hours.
- ✅ **Subscription check** — access to features only for channel subscribers.
- 🗂️ **User-friendly menu** — intuitive navigation with buttons.
- ⚡ **Fast** — asynchronous processing, no delays.
- 🛡️ **Security** — all keys and tokens are stored in .env.

## Usage examples
- **/start** — start the bot, greeting and subscription check.
- **Check prices** — the bot will ask for a model name and show found offers.
- **News** — the bot will show the latest sneaker news.
- **Order sneakers** — (coming soon) a link to the order website will be available.

## Typical scenario
1. User starts the bot with `/start`.
2. If not subscribed to the channel, the bot will prompt to subscribe.
3. After subscribing, the main menu opens:
    - Check prices
    - News
    - Order sneakers
    - Help
4. When choosing "Check prices", the bot will ask for a model name and show results.
5. When choosing "News", the bot will show the latest news.

## Quick start

### 1. Clone the repository
```bash
git clone https://github.com/Kirill-cmd-ops/SneakerCheckPriceBot.git
cd SneakerCheckPriceBot
```

### 2. Install Poetry (if not installed)
```bash
pip install poetry
```

### 3. Install dependencies
```bash
poetry install
```

### 4. Create a `.env` file in the project root and add environment variables:

#### Example .env
```
SECRET_TOKEN_BOT=your_bot_token
ID_CHANNEL=@your_channel_id
USER_AGENT=your_user_agent
BASE_URL=https://example.com
CATALOG_MEN_PATH=path_to_men
CATALOG_WOMEN_PATH=path_to_women
MAX_PAGES=3
SNEAKERS_WOMEN_URL=https://example.com/women
SNEAKERS_MEN_URL=https://example.com/men
MAX_PAGES_BUNT=1
MAX_PAGES_SNEAK=1
```

### 5. Run the bot
```bash
poetry run python -m sneaker_bot.main
```

## Project structure
```
sneaker_bot/
  handlers/        # Command and button handlers
  menu/            # Keyboards and menus
  parsers/         # News and price parsers
  services/        # Service functions (messaging, logic)
  setting.py       # Bot and dispatcher settings
  startup.py       # Bot command setup
  sub_checker.py   # Subscription check
  tasks.py         # Async task management
  main.py          # Entry point
```

## Technical details
- Language: **Python 3.12**
- Framework: **aiogram 3.x**
- Dependency management: **Poetry**
- Web parsing: **aiohttp, BeautifulSoup**
- Secrets: **python-dotenv**
- Async: **asyncio**
- FSM: **aiogram.fsm**

### Architecture
- All code is split into modules by responsibility.
- Routers are used for command and button logic.
- Keyboards are separated for easy editing.
- All external calls (parsing, messaging) are in services.
- Task management prevents race conditions and duplicate requests.

## FAQ
**Q: The bot won't start, what should I do?**
- Check that all environment variables are set correctly in .env
- Make sure Python 3.12 and poetry are installed
- Check that your bot token is valid

**Q: How to add a new site for parsing?**
- Add a new function in parsers/price_parser.py and connect it to the main search process.

**Q: How to change the menu or text?**
- Edit the corresponding file in menu/ or services/send_messages.py

**Q: How to deploy the bot on a server?**
- Use any VPS with Python 3.12+, set up .env, and run via poetry.

## Contributing
1. Fork the repository
2. Create a new branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Submit a pull request
5. Describe what and why you changed

## License
MIT License. Free to use with attribution.

## Contacts
- Author: [Kirill](https://github.com/Kirill-cmd-ops)
- Telegram: [@SkForbes](https://t.me/SkForbes)

---

> Project uses [aiogram 3.x](https://docs.aiogram.dev/) and Poetry for dependency management.
