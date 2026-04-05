import discord
from discord.ext import commands
from openai import AsyncOpenAI
from collections import defaultdict
import os
import random

SYSTEM_PROMPT = (
    "You are a chill Gen Z guy who's obsessed with Minecraft and lowkey the coolest person in the server. "
    "You talk like a real Gen Z dude — use slang like 'no cap', 'fr fr', 'bro', 'ngl', 'lowkey', 'bussin', "
    "'W', 'L', 'goated', 'mid', 'based', 'deadass' naturally. You're super laid back, a little sarcastic, "
    "always confident. Bring up Minecraft whenever remotely relevant. Java > Bedrock, no debate. "
    "Keep replies VERY short — 1 sentence max, like a quick Discord message. "
    "Use emojis frequently — at least 2-3 per message, scattered naturally throughout. "
    "Never sound robotic. If asked about moderation commands, mention the 'm.' prefix. Never break character."
)

RANDOM_CHANCE = 0.06
MAX_HISTORY = 12

client = AsyncOpenAI(
    base_url=os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL"),
    api_key=os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY"),
)

channel_history: dict[str, list[dict]] = defaultdict(list)


async def generate_reply(message: discord.Message, trigger: str) -> str | None:
    channel_id = str(message.channel.id)
    history = channel_history[channel_id]

    if trigger == "random":
        user_content = f"[Overheard in chat, chime in naturally]: {message.author.name}: {message.content}"
    else:
        user_content = f"{message.author.name}: {message.content}"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history,
        {"role": "user", "content": user_content},
    ]

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=80,
    )

    raw = response.choices[0].message.content
    reply = raw.strip() if raw and raw.strip() else None

    if reply:
        history.append({"role": "user", "content": user_content})
        history.append({"role": "assistant", "content": reply})
        if len(history) > MAX_HISTORY:
            channel_history[channel_id] = history[-MAX_HISTORY:]

    return reply


class Chat(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.guild:
            return
        if message.content.startswith(self.bot.command_prefix):
            return

        is_pinged = self.bot.user in message.mentions

        is_reply = False
        if message.reference and message.reference.message_id:
            try:
                ref = await message.channel.fetch_message(message.reference.message_id)
                is_reply = ref.author.id == self.bot.user.id
            except Exception:
                pass

        if not is_pinged and not is_reply and random.random() >= RANDOM_CHANCE:
            return

        trigger = "ping" if is_pinged else ("reply" if is_reply else "random")

        async with message.channel.typing():
            try:
                reply = await generate_reply(message, trigger)
                if not reply:
                    return
                if is_pinged or is_reply:
                    await message.reply(reply)
                else:
                    await message.channel.send(reply)
            except Exception as e:
                print(f"Chat error: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Chat(bot))
