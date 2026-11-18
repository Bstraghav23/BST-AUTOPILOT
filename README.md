# BST Autopilot

Free system for your GameBoost store:

1. **Upload CSVs with images:** builds GameBoost item-offer CSVs where every listing already has its banner image link.
2. **Price alerts on Telegram:** every 6 hours it checks your GameBoost listings, tells you which account prices to drop, and alerts you when something sells. It never changes a price itself.

Cost: €0 (GitHub free + Telegram free). Setup: about 15 minutes, all from your phone browser.

---

## Step 1: Put this folder on GitHub (5 min)

1. Make a free account at github.com.
2. Tap **+** → **New repository**. Name it `bst-autopilot`, choose **Public**, tap **Create repository**.
   - Public is needed so GameBoost can load the banner images. Your API key and Telegram token are never in the files; they go in Secrets (Step 3).
3. On the new repo page tap **uploading an existing file**, unzip this folder on your phone/PC and drag in **everything inside it** (keep the folders). Tap **Commit changes**.
   - The `.github` folder is hidden on some phones. If it doesn't upload, use a PC, or create the two files under **Add file → Create new file** named `.github/workflows/autopilot.yml` and `.github/workflows/build-csv.yml` and paste their contents.

## Step 2: Get your upload CSV with images (1 min)

1. Open the **Actions** tab → **Build upload CSV** → **Run workflow**.
2. After ~30 seconds open the `output` folder:
   - `upload-approved.csv`: your first 25 listings
   - `upload-all.csv`: all 105
3. Download it and upload it in GameBoost's bulk item-offer import.

To add more listings later: in `data/listings.json` change `"status": "draft"` to `"status": "approved"` for the ones you want, commit, and the CSV rebuilds itself.

## Step 3: Turn on Telegram alerts (8 min)

**Telegram bot**
1. In Telegram, message **@BotFather** → `/newbot` → pick a name. Copy the **token** it gives you.
2. Open your new bot and send it any message (e.g. `hi`).
3. Message **@userinfobot**; it replies with your **Id** number. That is your chat id.

**GameBoost key**
GameBoost dashboard → **Settings → Developers** → create/copy your API key.

**Save them in GitHub (never in chat or in files)**
Repo → **Settings → Secrets and variables → Actions → New repository secret**, three times:

| Name | Value |
|---|---|
| `GAMEBOOST_API_KEY` | your GameBoost API key |
| `TELEGRAM_BOT_TOKEN` | the BotFather token |
| `TELEGRAM_CHAT_ID` | your number from @userinfobot |

**Test it:** Actions → **Price alerts** → **Run workflow**. You should get a Telegram message within a minute (or nothing, if no listing needs a change yet; the run log says "Nothing to report").

## What the alerts look like

```
🔻 KT16 | 20 Evo | 3,093 Gems
   €36.49 → €33.49   (listed 9 days, 12 views, floor €25.54)

💰 SOLD: TH14 Near Max — €19.99

📊 Daily summary
Live listings: 31   Sales today: 3   Sales last 7 days: 14
```

## Change the rules (no code)

Edit `config.json` on GitHub:

| Setting | Meaning | Now |
|---|---|---|
| `drop_after_days` | suggest a drop once a listing is this old | 3 |
| `drop_percent` | size of each suggested drop | 8 |
| `days_between_suggestions` | wait before suggesting again on the same listing | 3 |
| `default_floor_percent` | never suggest below this % of the first price seen | 70 |
| `reprice_kinds` | which listings get price suggestions (`account`, `item`) | accounts only |
| `daily_summary_hour_ist` | summary hour (India time) | 21 |
| `currency_symbol` | used when GameBoost does not say the currency | € |

Set an exact lowest price for any listing in `data/floors.csv` (its title or external id, and the floor).

## If something fails

Actions tab → open the red run → read the last lines.
- `GameBoost API error 401`: the API key secret is wrong.
- `GameBoost API error 404` on `/item-offers`: remove the `"/item-offers"` line from `config.json`.
- No Telegram message but run is green: check the two Telegram secrets, and that you messaged your bot once.

## Coming next
- Market comparison: competitor prices next to each suggestion.
- Clash Royale account analysis → title, description and price, straight into the CSV.
