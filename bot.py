import os
import json
import httpx
from openai import OpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

LEADS = {}

def load_catalog():
    with open("catalog.json", "r", encoding="utf-8") as f:
        return json.load(f)

async def brave_search(query: str):
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {"Accept": "application/json", "X-Subscription-Token": BRAVE_API_KEY}
    params = {"q": query, "count": "5"}
    async with httpx.AsyncClient(timeout=20) as hx:
        r = await hx.get(url, headers=headers, params=params)
        r.raise_for_status()
        data = r.json()
    return data.get("web", {}).get("results", [])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Use /analyze @username")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Commands: /analyze @username, then /report")

async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Use /analyze @username")
        return
    username = context.args[0].replace("@", "")
    LEADS[update.effective_chat.id] = {"username": username}
    await update.message.reply_text(
        "Now paste ONE message with:\nBIO: ...\nLINK: ...\nPOSTS: ...\nNOTES: ..."
    )

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lead = LEADS.get(chat_id)
    if not lead:
        await update.message.reply_text("Run /analyze first.")
        return

    catalog = load_catalog()
    web_results = await brave_search(
        f'{lead["username"]} LinkedIn OR interview OR website OR TikTok OR YouTube'
    )

    prompt = f"""
Analyze this Instagram lead:
Username: {lead['username']}

Public web results:
{web_results}

Catalog:
{catalog}

Tasks:
1) Fit score 0-100 + budget (Low/Med/High) with evidence
2) Top 3 authority gaps
3) Recommend ONE primary offer and ONE upsell (choose from catalog, allowed=true)
4) Include cost, sell price, profit
5) Write DM1 + Follow-up1 + Follow-up2
Rules: No illegal actions, no private data, no scraping bypass, no guarantees of editorial.
"""

    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "You are a sharp, realistic sales strategist."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.35,
    )

    text = resp.choices[0].message.content.strip()
    # Telegram message size safety
    await update.message.reply_text(text[:4000])

def main():
    if not BOT_TOKEN or not OPENAI_API_KEY or not BRAVE_API_KEY:
        raise RuntimeError("Missing BOT_TOKEN / OPENAI_API_KEY / BRAVE_API_KEY environment variables")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("analyze", analyze))
    app.add_handler(CommandHandler("report", report))
    app.run_polling()

if __name__ == "__main__":
    main()
