# TikTok → Telegram auto-watcher

Checks a list of TikTok accounts every hour and sends any new videos
straight to a Telegram chat, automatically. Runs entirely on GitHub's
servers — your computer can be off.

## Setup (5 steps, one-time)

1. **Create a Telegram bot.** In Telegram, message **@BotFather**, send
   `/newbot`, follow the prompts. It gives you a token that looks like
   `123456789:ABCdefGhIjKlmNoPQRstuVwxyz`. Save it.

2. **Get your chat ID.** Message your new bot anything (e.g. "hi"), then
   open this URL in a browser (with your real token):
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   Look for `"chat":{"id":123456789` in the response — that number is
   your chat ID.

3. **Create a new GitHub repo** (private is fine) and upload all the
   files in this folder to it.

4. **Add two secrets** in the repo: go to
   `Settings → Secrets and variables → Actions → New repository secret`
   and add:
   - `TELEGRAM_BOT_TOKEN` — the token from step 1
   - `TELEGRAM_CHAT_ID` — the number from step 2

5. **Edit `accounts.txt`** and add the TikTok profile URLs you want
   watched, one per line, e.g.:
   ```
   https://www.tiktok.com/@example_username
   ```
   Commit the change.

That's it. Go to the **Actions** tab in your repo — the workflow will
run automatically every hour from now on. You can also click
"Run workflow" there to trigger it immediately instead of waiting.

## Notes

- It only looks at each account's most recent 20 uploads per check, so
  as long as it runs at least once between a video going up and coming
  down, it'll catch it.
- Videos over 50MB can't be sent through Telegram's bot API — you'll
  get a text notice instead of the file in that case.
- `seen.json` is how it remembers what's already been sent; don't
  delete it or it may re-send old videos.
- Free GitHub accounts get 2,000 Action-minutes/month on private repos
  (unlimited on public repos) — this job is tiny, so you won't come
  close to that running hourly.
