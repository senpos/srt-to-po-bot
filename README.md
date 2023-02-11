# srt-to-po-bot
**❗ Starting November 28th 2022, [Heroku no longer provides a free tier](https://blog.heroku.com/next-chapter), so use this button with caution.**

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)
--

This is a simple Telegram bot which converts **SRT** files into **PO** file format, additionally replacing newlines with a special `<nl>` tag, so it is convenient to process them in different CAT tools like [Smartcat](http://smartcat.com/).

This is a **reversible** operation, which means you can send to bot (translated) PO files and get back your SRT files.

Keep in mind, since PO files which bot generates store cue's index and timestamps in the comment (`#.`) attribute, it won't be able to convert back any random PO files. Those have to be ones produced by the bot.

# Requirements
`Python 3.9+`

Check `requirements.txt` to see the full list of dependencies with pinned versions.

- [polib](https://github.com/izimobil/polib)
- [srt](https://github.com/cdown/srt)
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)

# Configuration
All parameters are set via **environment variables**.

`TELEGRAM_TOKEN` - you can get one by [creating a new bot](https://t.me/BotFather).

`ENV` - can be either `production` or any other value (or unset).

If `ENV=production` - bot will run using webhooks.
Otherwise, it will use polling.

If running webhooks, you need to additionally provide these environment variables:

`URL` - your application URL, which will be used to receive webhooks (it probably should have a valid SSL certificate). If you are hosting the bot on Heroku, just copy your application URL and put it here.

`PORT` - port the bot will be running on. You can omit it while running on Heroku, it sets it automatically.

`SECRET` - a string which will be used as a part of the path to receive webhooks. Usually, you don't want to put Telegram token here. You can generate nice token with Python:
```python
import secrets

print(secrets.token_urlsafe(4))
```

You can omit it if you created Heroku app using the "Deploy to Heroku" button at the top of this readme, it will create token for you automatically.
