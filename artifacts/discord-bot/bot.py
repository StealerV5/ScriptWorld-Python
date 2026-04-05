import discord
from discord.ext import commands
import os
import asyncio

PREFIX = "m."

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.moderation = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    print(f"Serving {len(bot.guilds)} guild(s).")
    await bot.change_presence(activity=discord.Game(name="m.cmds | Chat & Moderation"))


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.reply(f"Unknown command. Try `m.cmds` for a list of commands.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.reply("You don't have permission to use that command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        cmd = ctx.command
        usage = getattr(cmd, "usage", None) or f"m.{cmd.name}"
        await ctx.reply(f"Missing argument. Usage: `{usage}`")
    elif isinstance(error, commands.BadArgument):
        await ctx.reply("Invalid argument provided.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.reply("I don't have permission to do that.")


async def main():
    async with bot:
        for cog in ["cogs.general", "cogs.moderation", "cogs.chat"]:
            await bot.load_extension(cog)
        token = os.environ.get("DISCORD_BOT_TOKEN")
        if not token:
            print("ERROR: DISCORD_BOT_TOKEN is not set.")
            return
        await bot.start(token)


asyncio.run(main())
