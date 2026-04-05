import discord
from discord.ext import commands
from datetime import timedelta
from collections import defaultdict
import re
import asyncio

warnings_db: dict[str, list[dict]] = defaultdict(list)


def parse_duration(s: str) -> timedelta | None:
    match = re.match(r"^(\d+)(s|m|h|d)$", s, re.IGNORECASE)
    if not match:
        return None
    value = int(match.group(1))
    unit = match.group(2).lower()
    multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    return timedelta(seconds=value * multipliers[unit])


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="kick")
    @commands.guild_only()
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        """Kick a member from the server"""
        if not member.is_kickable():
            await ctx.reply("I can't kick that user (they may have a higher role than me).")
            return
        await member.kick(reason=reason)
        embed = discord.Embed(title="Member Kicked", color=0xFFA500)
        embed.add_field(name="User", value=f"{member} ({member.id})", inline=True)
        embed.add_field(name="Moderator", value=str(ctx.author), inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.timestamp = discord.utils.utcnow()
        await ctx.reply(embed=embed)

    @commands.command(name="ban")
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        """Ban a member from the server"""
        if not member.is_banned if hasattr(member, "is_banned") else False:
            pass
        if not member.is_kickable():
            await ctx.reply("I can't ban that user (they may have a higher role than me).")
            return
        await member.ban(reason=reason, delete_message_days=1)
        embed = discord.Embed(title="Member Banned", color=0xFF0000)
        embed.add_field(name="User", value=f"{member} ({member.id})", inline=True)
        embed.add_field(name="Moderator", value=str(ctx.author), inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.timestamp = discord.utils.utcnow()
        await ctx.reply(embed=embed)

    @commands.command(name="unban")
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, user_id: str, *, reason: str = "No reason provided"):
        """Unban a user by their ID"""
        try:
            uid = int(user_id)
        except ValueError:
            await ctx.reply("Please provide a valid user ID.")
            return
        try:
            user = discord.Object(id=uid)
            await ctx.guild.unban(user, reason=reason)
            embed = discord.Embed(title="User Unbanned", color=0x00FF00)
            embed.add_field(name="User ID", value=str(uid), inline=True)
            embed.add_field(name="Moderator", value=str(ctx.author), inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.timestamp = discord.utils.utcnow()
            await ctx.reply(embed=embed)
        except discord.NotFound:
            await ctx.reply("That user is not banned.")
        except Exception as e:
            await ctx.reply(f"Failed to unban: {e}")

    @commands.command(name="mute", aliases=["timeout"])
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def mute(self, ctx: commands.Context, member: discord.Member, duration_str: str, *, reason: str = "No reason provided"):
        """Timeout a member. Duration: 10s, 5m, 2h, 1d"""
        duration = parse_duration(duration_str)
        if not duration:
            await ctx.reply("Invalid duration. Use formats like `10s`, `5m`, `2h`, `1d`.")
            return
        if duration > timedelta(days=28):
            await ctx.reply("Max timeout duration is 28 days.")
            return
        try:
            until = discord.utils.utcnow() + duration
            await member.timeout(until, reason=reason)
            until_ts = int(until.timestamp())
            embed = discord.Embed(title="Member Muted (Timeout)", color=0xFFA500)
            embed.add_field(name="User", value=f"{member} ({member.id})", inline=True)
            embed.add_field(name="Moderator", value=str(ctx.author), inline=True)
            embed.add_field(name="Duration", value=duration_str, inline=True)
            embed.add_field(name="Expires", value=f"<t:{until_ts}:R>", inline=False)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.timestamp = discord.utils.utcnow()
            await ctx.reply(embed=embed)
        except discord.Forbidden:
            await ctx.reply("I can't timeout that user.")

    @commands.command(name="unmute", aliases=["untimeout"])
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def unmute(self, ctx: commands.Context, member: discord.Member):
        """Remove a timeout from a member"""
        try:
            await member.timeout(None)
            embed = discord.Embed(title="Member Unmuted", color=0x00FF00)
            embed.add_field(name="User", value=f"{member} ({member.id})", inline=True)
            embed.add_field(name="Moderator", value=str(ctx.author), inline=True)
            embed.timestamp = discord.utils.utcnow()
            await ctx.reply(embed=embed)
        except discord.Forbidden:
            await ctx.reply("I can't unmute that user.")

    @commands.command(name="warn")
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        """Warn a member"""
        key = f"{ctx.guild.id}:{member.id}"
        warnings_db[key].append({"reason": reason, "mod": str(ctx.author)})
        count = len(warnings_db[key])
        try:
            await member.send(
                f"⚠️ You have been warned in **{ctx.guild.name}**.\n"
                f"Reason: {reason}\nTotal warnings: {count}"
            )
        except Exception:
            pass
        embed = discord.Embed(title="Member Warned", color=0xFFFF00)
        embed.add_field(name="User", value=f"{member} ({member.id})", inline=True)
        embed.add_field(name="Moderator", value=str(ctx.author), inline=True)
        embed.add_field(name="Total Warnings", value=str(count), inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.timestamp = discord.utils.utcnow()
        await ctx.reply(embed=embed)

    @commands.command(name="warnings", aliases=["warns"])
    @commands.guild_only()
    async def warnings(self, ctx: commands.Context, member: discord.Member = None):
        """View warnings for a user"""
        member = member or ctx.author
        key = f"{ctx.guild.id}:{member.id}"
        wlist = warnings_db[key]
        if wlist:
            desc = "\n".join(
                f"**{i+1}.** {w['reason']} — by {w['mod']}"
                for i, w in enumerate(wlist)
            )
        else:
            desc = "No warnings on record."
        embed = discord.Embed(title=f"Warnings for {member}", description=desc, color=0xFFFF00)
        embed.set_footer(text=f"Total: {len(wlist)}")
        embed.timestamp = discord.utils.utcnow()
        await ctx.reply(embed=embed)

    @commands.command(name="purge", aliases=["clear", "clean"])
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx: commands.Context, amount: int):
        """Delete a number of messages (1–100)"""
        if not 1 <= amount <= 100:
            await ctx.reply("Please provide a number between 1 and 100.")
            return
        await ctx.message.delete()
        deleted = await ctx.channel.purge(limit=amount)
        notice = await ctx.send(f"🗑️ Deleted **{len(deleted)}** messages.")
        await asyncio.sleep(4)
        await notice.delete()

    @commands.command(name="slowmode", aliases=["slow"])
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def slowmode(self, ctx: commands.Context, seconds: int):
        """Set slowmode for a channel (0 to disable, max 21600)"""
        if not 0 <= seconds <= 21600:
            await ctx.reply("Please provide a number between 0 and 21600 seconds.")
            return
        await ctx.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            await ctx.reply("✅ Slowmode disabled.")
        else:
            await ctx.reply(f"✅ Slowmode set to **{seconds} second(s)**.")

    @commands.command(name="lock")
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def lock(self, ctx: commands.Context):
        """Lock the current channel"""
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.reply("🔒 Channel locked. Only moderators can send messages.")

    @commands.command(name="unlock")
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def unlock(self, ctx: commands.Context):
        """Unlock the current channel"""
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = None
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.reply("🔓 Channel unlocked. Everyone can send messages again.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
