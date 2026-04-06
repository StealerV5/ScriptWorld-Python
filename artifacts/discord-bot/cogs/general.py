import discord
from discord.ext import commands


CHAT_COMMANDS = [
    ("m.ping", "Check the bot's latency"),
    ("m.cmds", "Show all commands"),
    ("m.userinfo [@user]", "Get info about a user"),
    ("m.serverinfo", "Get info about the server"),
    ("m.avatar [@user]", "Show a user's avatar"),
    ("m.say <message>", "Make the bot say something (Manage Messages)"),
]

MOD_COMMANDS = [
    ("m.kick <@user> [reason]", "Kick a member"),
    ("m.ban <@user> [reason]", "Ban a member"),
    ("m.unban <userID> [reason]", "Unban a user by ID"),
    ("m.mute <@user> <duration> [reason]", "Timeout a member (e.g. 10m, 2h, 1d)"),
    ("m.unmute <@user>", "Remove a timeout from a member"),
    ("m.warn <@user> [reason]", "Warn a member"),
    ("m.warnings [@user]", "View warnings for a user"),
    ("m.purge <1-100>", "Bulk delete messages"),
    ("m.slowmode <seconds>", "Set channel slowmode (0 to disable)"),
    ("m.lock", "Lock the channel for @everyone"),
    ("m.unlock", "Unlock the channel"),
]

TICKET_COMMANDS = [
    ("m.ticketsetup", "Post the ticket support panel (Server Owner only)"),
]


def build_commands_embed():
    embed = discord.Embed(
        title="📋 Command List",
        description="Prefix: **`m.`**  •  Use `m.cmds` to see this list anytime.",
        color=0x5865F2,
    )
    embed.add_field(
        name="💬 Chat & Utility",
        value="\n".join(f"**`{usage}`**\n{desc}" for usage, desc in CHAT_COMMANDS),
        inline=False,
    )
    embed.add_field(
        name="🔨 Moderation",
        value="\n".join(f"**`{usage}`**\n{desc}" for usage, desc in MOD_COMMANDS),
        inline=False,
    )
    embed.add_field(
        name="🎫 Tickets",
        value="\n".join(f"**`{usage}`**\n{desc}" for usage, desc in TICKET_COMMANDS),
        inline=False,
    )
    embed.set_footer(text="[] = optional  •  <> = required")
    return embed


class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="ping", aliases=["pong"])
    async def ping(self, ctx: commands.Context):
        """Check the bot's latency"""
        msg = await ctx.reply("Pinging...")
        roundtrip = round((msg.created_at - ctx.message.created_at).total_seconds() * 1000)
        api = round(self.bot.latency * 1000)
        await msg.edit(content=f"🏓 Pong! Roundtrip: **{roundtrip}ms** | API: **{api}ms**")

    @commands.command(name="cmds", aliases=["commands", "help", "h"])
    async def cmds(self, ctx: commands.Context):
        """List all commands"""
        await ctx.reply(embed=build_commands_embed())

    @commands.command(name="say")
    @commands.has_permissions(manage_messages=True)
    async def say(self, ctx: commands.Context, *, text: str):
        """Make the bot say something (mods only)"""
        await ctx.message.delete()
        await ctx.send(text)

    @commands.command(name="userinfo", aliases=["ui", "whois"])
    @commands.guild_only()
    async def userinfo(self, ctx: commands.Context, member: discord.Member = None):
        """Get info about a user"""
        member = member or ctx.author
        joined_ts = int(member.joined_at.timestamp()) if member.joined_at else 0
        created_ts = int(member.created_at.timestamp())
        roles = [r.mention for r in member.roles if r != ctx.guild.default_role]

        embed = discord.Embed(color=member.color if member.color.value else 0x5865F2)
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="Nickname", value=member.nick or "None", inline=True)
        embed.add_field(name="Bot?", value="Yes" if member.bot else "No", inline=True)
        embed.add_field(name="Account Created", value=f"<t:{created_ts}:F>", inline=False)
        embed.add_field(name="Joined Server", value=f"<t:{joined_ts}:F>", inline=False)
        roles_str = " ".join(roles) if roles else "None"
        if len(roles_str) > 1024:
            roles_str = roles_str[:1021] + "..."
        embed.add_field(name=f"Roles ({len(roles)})", value=roles_str, inline=False)
        embed.set_footer(text=f"Requested by {ctx.author}")
        embed.timestamp = discord.utils.utcnow()
        await ctx.reply(embed=embed)

    @commands.command(name="serverinfo", aliases=["si", "server"])
    @commands.guild_only()
    async def serverinfo(self, ctx: commands.Context):
        """Get info about the server"""
        g = ctx.guild
        created_ts = int(g.created_at.timestamp())
        embed = discord.Embed(title=g.name, color=0x5865F2)
        if g.icon:
            embed.set_thumbnail(url=g.icon.url)
        embed.add_field(name="ID", value=g.id, inline=True)
        embed.add_field(name="Owner", value=f"<@{g.owner_id}>", inline=True)
        embed.add_field(name="Members", value=g.member_count, inline=True)
        embed.add_field(name="Channels", value=len(g.channels), inline=True)
        embed.add_field(name="Roles", value=len(g.roles), inline=True)
        embed.add_field(name="Boosts", value=f"{g.premium_subscription_count} (Tier {g.premium_tier})", inline=True)
        embed.add_field(name="Created", value=f"<t:{created_ts}:F>", inline=False)
        embed.set_footer(text=f"Requested by {ctx.author}")
        embed.timestamp = discord.utils.utcnow()
        await ctx.reply(embed=embed)

    @commands.command(name="avatar", aliases=["av", "pfp"])
    async def avatar(self, ctx: commands.Context, user: discord.User = None):
        """Get a user's avatar"""
        user = user or ctx.author
        embed = discord.Embed(title=f"{user.name}'s Avatar", color=0x5865F2, url=user.display_avatar.url)
        embed.set_image(url=user.display_avatar.with_size(1024).url)
        await ctx.reply(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))
