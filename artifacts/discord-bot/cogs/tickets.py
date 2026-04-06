import discord
from discord.ext import commands
import json
import os
import re
import asyncio

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "tickets.json")
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

CATEGORY_OPTIONS = [
    discord.SelectOption(
        label="General Support", value="general",
        description="General questions or help", emoji="🛡️"
    ),
    discord.SelectOption(
        label="Technical Issue", value="technical",
        description="Technical problems or errors", emoji="🔧"
    ),
    discord.SelectOption(
        label="Bug Report", value="bug",
        description="Found a bug or glitch", emoji="🐛"
    ),
    discord.SelectOption(
        label="Suggestion", value="suggestion",
        description="Share an idea or feedback", emoji="💡"
    ),
    discord.SelectOption(
        label="Other", value="other",
        description="Something else not listed above", emoji="📋"
    ),
]

CATEGORY_LABELS: dict[str, tuple[str, str]] = {
    "general":    ("🛡️", "General Support"),
    "technical":  ("🔧", "Technical Issue"),
    "bug":        ("🐛", "Bug Report"),
    "suggestion": ("💡", "Suggestion"),
    "other":      ("📋", "Other"),
}

# Channel topic format: #{num}|{creator_id}|{cat_value}|{cat_label}|{claimer_id}
TOPIC_SEP = "|"

DEFAULT_SETTINGS = {
    "category_name": "Active Tickets",
    "mod_role_ids": [],
    "embed_style": "detailed",
}


# ─────────────────────── Data helpers ───────────────────────

def load_data() -> dict:
    try:
        with open(DATA_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"count": 0, "guilds": {}}


def save_data(data: dict) -> None:
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_ticket_count() -> int:
    return load_data().get("count", 0)


def increment_ticket_count() -> int:
    data = load_data()
    data["count"] = data.get("count", 0) + 1
    save_data(data)
    return data["count"]


def get_guild_settings(guild_id: int) -> dict:
    data = load_data()
    return data.get("guilds", {}).get(str(guild_id), dict(DEFAULT_SETTINGS))


def save_guild_settings(guild_id: int, settings: dict) -> None:
    data = load_data()
    if "guilds" not in data:
        data["guilds"] = {}
    data["guilds"][str(guild_id)] = settings
    save_data(data)


# ─────────────────────── Topic helpers ───────────────────────

def build_topic(num: int, creator_id: int, cat_value: str, cat_label: str, claimer_id: int = 0) -> str:
    return TOPIC_SEP.join([f"#{num}", str(creator_id), cat_value, cat_label, str(claimer_id)])


def parse_topic(topic: str | None) -> dict | None:
    if not topic:
        return None
    parts = topic.split(TOPIC_SEP)
    if len(parts) < 5 or not parts[0].startswith("#"):
        return None
    try:
        return {
            "num":        int(parts[0][1:]),
            "creator_id": int(parts[1]),
            "cat_value":  parts[2],
            "cat_label":  parts[3],
            "claimer_id": int(parts[4]),
        }
    except (ValueError, IndexError):
        return None


# ─────────────────────── Misc helpers ───────────────────────

def safe_channel_name(name: str, ticket_num: int) -> str:
    cleaned = re.sub(r"[^a-z0-9\-]", "", name.lower().replace(" ", "-").replace("_", "-"))
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return f"{(cleaned or 'user')[:40]}-{ticket_num}"


def is_ticket_channel(channel: discord.TextChannel, settings: dict) -> bool:
    return (
        isinstance(channel, discord.TextChannel)
        and channel.category is not None
        and channel.category.name == settings["category_name"]
        and parse_topic(channel.topic) is not None
    )


def is_staff(member: discord.Member) -> bool:
    return member.guild_permissions.manage_channels


def build_ticket_embed(
    num: int,
    member: discord.Member,
    emoji: str,
    label: str,
    guild: discord.Guild,
    style: str,
) -> discord.Embed:
    embed = discord.Embed(title=f"🎫 Ticket #{num}", color=0x57F287)
    embed.set_author(name=str(member), icon_url=member.display_avatar.url)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="👤 User", value=member.mention, inline=True)
    embed.add_field(name="📋 Category", value=f"{emoji} {label}", inline=True)
    embed.add_field(name="🔢 Ticket", value=f"#{num}", inline=True)
    embed.add_field(name="🟢 Status", value="Open", inline=True)
    embed.add_field(name="🙋 Claimed By", value="Unclaimed", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)

    if style == "detailed":
        embed.add_field(
            name="📝 How to get help",
            value="Describe your issue below and a staff member will assist you shortly.",
            inline=False,
        )
        embed.add_field(
            name="🔧 Ticket Commands",
            value=(
                "`m.close` — Close and delete this ticket\n"
                "`m.claim` — Claim this ticket (staff only)\n"
                "`m.ticketinfo` — View detailed info about this ticket"
            ),
            inline=False,
        )

    embed.set_footer(text=f"Ticket created • {guild.name}")
    embed.timestamp = discord.utils.utcnow()
    return embed


# ─────────────────────── Views ───────────────────────

class CategorySelect(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="Choose a category...",
            options=CATEGORY_OPTIONS,
            custom_id="ticket_cat_select",
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        value = self.values[0]
        emoji, label = CATEGORY_LABELS[value]
        guild = interaction.guild
        member = interaction.user
        settings = get_guild_settings(guild.id)

        num = increment_ticket_count()

        # Find or create the configured ticket category
        cat_name = settings["category_name"]
        active_cat = discord.utils.get(guild.categories, name=cat_name)
        if not active_cat:
            active_cat = await guild.create_category(
                cat_name,
                overwrites={guild.default_role: discord.PermissionOverwrite(view_channel=False)},
            )

        # Resolve saved mod roles
        mod_roles: list[discord.Role] = []
        for role_id in settings.get("mod_role_ids", []):
            role = guild.get_role(role_id)
            if role:
                mod_roles.append(role)

        # Build channel permission overwrites
        overwrites: dict = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True, send_messages=True,
                manage_channels=True, manage_messages=True,
            ),
        }
        for role in mod_roles:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            )

        ticket_channel = await guild.create_text_channel(
            safe_channel_name(member.name, num),
            category=active_cat,
            overwrites=overwrites,
            topic=build_topic(num, member.id, value, label),
        )

        embed = build_ticket_embed(num, member, emoji, label, guild, settings["embed_style"])

        pings = member.mention
        if mod_roles:
            pings += " " + " ".join(r.mention for r in mod_roles)
        await ticket_channel.send(content=pings, embed=embed)

        success = discord.Embed(
            title="✅ Ticket Created!",
            description=(
                f"Your ticket has been created: {ticket_channel.mention}\n\n"
                "A staff member will be with you shortly."
            ),
            color=0x57F287,
        )
        await interaction.edit_original_response(embed=success, view=None)
        self.view.stop()


class CategoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(CategorySelect())


class OpenTicketButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Open Ticket",
            style=discord.ButtonStyle.primary,
            emoji="🎫",
            custom_id="ticket_open_persistent_v1",
        )

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📋 Select Category",
            description="Select from the categories of what do you need help with",
            color=0x5865F2,
        )
        embed.add_field(
            name="Available Categories",
            value="\n".join(
                f"{opt.emoji} **{opt.label}** — {opt.description}"
                for opt in CATEGORY_OPTIONS
            ),
            inline=False,
        )
        embed.set_footer(text="Only you can see this message.")
        await interaction.response.send_message(embed=embed, view=CategoryView(), ephemeral=True)


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(OpenTicketButton())


# ─────────────────────── Cog ───────────────────────

class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(TicketPanelView())

    # ── Setup wizard helpers ──────────────────────────

    async def _ask(self, ctx: commands.Context, embed: discord.Embed, timeout: int = 60) -> discord.Message | None:
        """Send a question embed and wait for the owner's reply. Returns None on timeout."""
        await ctx.send(embed=embed)
        try:
            return await self.bot.wait_for(
                "message",
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            timed_out = discord.Embed(
                title="⏰ Setup Timed Out",
                description="You took too long to respond. Run `m.ticketsetup` again to restart.",
                color=0xED4245,
            )
            await ctx.send(embed=timed_out)
            return None

    async def _try_delete(self, msg: discord.Message) -> None:
        try:
            await msg.delete()
        except (discord.Forbidden, discord.NotFound):
            pass

    # ── m.ticketsetup ──────────────────────────────────

    @commands.command(name="ticketsetup")
    @commands.guild_only()
    async def ticketsetup(self, ctx: commands.Context):
        """Owner-only: Interactive setup wizard for the ticket panel"""
        if ctx.author.id != ctx.guild.owner_id:
            await ctx.reply("❌ Only the server owner can use this command.")
            return

        await self._try_delete(ctx.message)

        # ── Step 1 — Category name ──────────────────────
        q1 = discord.Embed(
            title="🎫 Ticket Setup — Step 1 of 3",
            description=(
                "**What Discord category should ticket channels be created in?**\n\n"
                "Type the exact name you want (e.g. `Active Tickets`).\n"
                "The bot will create it if it doesn't already exist.\n\n"
                "Type `skip` to use the default: **`Active Tickets`**"
            ),
            color=0x5865F2,
        )
        q1.set_footer(text="You have 60 seconds to respond • Step 1 of 3")

        reply1 = await self._ask(ctx, q1)
        if reply1 is None:
            return
        category_name = (
            "Active Tickets"
            if reply1.content.strip().lower() == "skip"
            else reply1.content.strip()
        )
        await self._try_delete(reply1)

        # ── Step 2 — Mod roles ─────────────────────────
        q2 = discord.Embed(
            title="🎫 Ticket Setup — Step 2 of 3",
            description=(
                "**Which roles should have access to ticket channels?**\n\n"
                "Mention the roles you want (e.g. `@Mods @Admin @Support`).\n"
                "These roles will be pinged when a ticket is opened and will be able to see all ticket channels.\n\n"
                "Type `none` if you don't need any specific roles."
            ),
            color=0x5865F2,
        )
        q2.set_footer(text="You have 60 seconds to respond • Step 2 of 3")

        reply2 = await self._ask(ctx, q2)
        if reply2 is None:
            return
        mod_role_ids = [r.id for r in reply2.role_mentions]
        mod_roles_display = (
            " ".join(r.mention for r in reply2.role_mentions) if mod_role_ids else "None"
        )
        await self._try_delete(reply2)

        # ── Step 3 — Embed style ───────────────────────
        q3 = discord.Embed(
            title="🎫 Ticket Setup — Step 3 of 3",
            description=(
                "**Should ticket embeds be simple or detailed?**\n\n"
                "🔹 **`simple`** — Clean, minimal embed with just the essentials "
                "(user, category, ticket number, status)\n\n"
                "🔸 **`detailed`** — Full embed including a how-to-get-help section "
                "and a list of ticket commands\n\n"
                "Reply with `simple` or `detailed`."
            ),
            color=0x5865F2,
        )
        q3.set_footer(text="You have 60 seconds to respond • Step 3 of 3")

        reply3 = await self._ask(ctx, q3)
        if reply3 is None:
            return
        embed_style = (
            "simple"
            if reply3.content.strip().lower() == "simple"
            else "detailed"
        )
        await self._try_delete(reply3)

        # ── Save settings ──────────────────────────────
        settings = {
            "category_name": category_name,
            "mod_role_ids": mod_role_ids,
            "embed_style": embed_style,
        }
        save_guild_settings(ctx.guild.id, settings)

        # ── Summary embed ──────────────────────────────
        style_display = "🔸 Detailed" if embed_style == "detailed" else "🔹 Simple"
        summary = discord.Embed(
            title="✅ Setup Complete!",
            description="Your ticket system is configured. The panel has been posted below.",
            color=0x57F287,
        )
        summary.add_field(name="📁 Ticket Category", value=f"`{category_name}`", inline=True)
        summary.add_field(name="🙋 Staff Roles", value=mod_roles_display, inline=True)
        summary.add_field(name="🎨 Embed Style", value=style_display, inline=True)
        summary.set_footer(text="Run m.ticketsetup again anytime to reconfigure.")
        await ctx.send(embed=summary)

        # ── Panel embed ────────────────────────────────
        panel = discord.Embed(
            title="🎫 Ticket Support",
            description="Make a ticket if you need help with something",
            color=0x5865F2,
        )
        panel.add_field(
            name="📌 How it works",
            value=(
                "1. Click **Open Ticket** below\n"
                "2. Select the category that fits your issue\n"
                "3. A private channel will be created just for you\n"
                "4. Our staff will assist you shortly!"
            ),
            inline=False,
        )
        panel.add_field(
            name="⚠️ Before opening a ticket",
            value=(
                "• Make sure your issue isn't already answered in the FAQ\n"
                "• Provide as much detail as possible\n"
                "• Be patient — staff will respond when available"
            ),
            inline=False,
        )
        if ctx.guild.icon:
            panel.set_thumbnail(url=ctx.guild.icon.url)
        panel.set_footer(text=ctx.guild.name)
        panel.timestamp = discord.utils.utcnow()
        await ctx.send(embed=panel, view=TicketPanelView())

    # ── m.close ────────────────────────────────────────

    @commands.command(name="close")
    @commands.guild_only()
    async def close(self, ctx: commands.Context):
        """Close and delete a ticket channel"""
        settings = get_guild_settings(ctx.guild.id)
        if not is_ticket_channel(ctx.channel, settings):
            await ctx.reply("❌ This command can only be used inside a ticket channel.")
            return

        data = parse_topic(ctx.channel.topic)
        if not data:
            await ctx.reply("❌ Could not read ticket data.")
            return

        if ctx.author.id != data["creator_id"] and not is_staff(ctx.author):
            await ctx.reply("❌ Only the ticket creator or staff can close this ticket.")
            return

        embed = discord.Embed(
            title="🔒 Ticket Closing",
            description=(
                f"This ticket is being closed by {ctx.author.mention}.\n"
                "The channel will be deleted in **5 seconds**."
            ),
            color=0xED4245,
        )
        embed.set_footer(text=f"Ticket #{data['num']} • {ctx.guild.name}")
        embed.timestamp = discord.utils.utcnow()
        await ctx.send(embed=embed)

        await asyncio.sleep(5)
        try:
            await ctx.channel.delete(reason=f"Ticket closed by {ctx.author}")
        except discord.NotFound:
            pass

    # ── m.claim ────────────────────────────────────────

    @commands.command(name="claim")
    @commands.guild_only()
    async def claim(self, ctx: commands.Context):
        """Claim a ticket (staff only)"""
        settings = get_guild_settings(ctx.guild.id)
        if not is_ticket_channel(ctx.channel, settings):
            await ctx.reply("❌ This command can only be used inside a ticket channel.")
            return

        if not is_staff(ctx.author):
            await ctx.reply("❌ Only staff members can claim a ticket.")
            return

        data = parse_topic(ctx.channel.topic)
        if not data:
            await ctx.reply("❌ Could not read ticket data.")
            return

        if data["claimer_id"] != 0:
            claimer = ctx.guild.get_member(data["claimer_id"])
            name = claimer.mention if claimer else f"<@{data['claimer_id']}>"
            await ctx.reply(f"❌ This ticket is already claimed by {name}.")
            return

        new_topic = build_topic(
            data["num"], data["creator_id"],
            data["cat_value"], data["cat_label"],
            ctx.author.id,
        )
        await ctx.channel.edit(topic=new_topic)

        emoji, label = CATEGORY_LABELS.get(data["cat_value"], ("📋", data["cat_label"]))
        creator = ctx.guild.get_member(data["creator_id"])
        creator_display = creator.mention if creator else f"<@{data['creator_id']}>"

        embed = discord.Embed(title="🙋 Ticket Claimed", color=0xFEE75C)
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        embed.add_field(name="🙋 Claimed By", value=ctx.author.mention, inline=True)
        embed.add_field(name="👤 Ticket Creator", value=creator_display, inline=True)
        embed.add_field(name="📋 Category", value=f"{emoji} {label}", inline=True)
        embed.set_footer(text=f"Ticket #{data['num']} • {ctx.guild.name}")
        embed.timestamp = discord.utils.utcnow()
        await ctx.send(embed=embed)

    # ── m.ticketinfo ───────────────────────────────────

    @commands.command(name="ticketinfo")
    @commands.guild_only()
    async def ticketinfo(self, ctx: commands.Context):
        """Show detailed info about the current ticket"""
        settings = get_guild_settings(ctx.guild.id)
        if not is_ticket_channel(ctx.channel, settings):
            await ctx.reply("❌ This command can only be used inside a ticket channel.")
            return

        data = parse_topic(ctx.channel.topic)
        if not data:
            await ctx.reply("❌ Could not read ticket data.")
            return

        emoji, label = CATEGORY_LABELS.get(data["cat_value"], ("📋", data["cat_label"]))
        creator = ctx.guild.get_member(data["creator_id"])
        creator_display = creator.mention if creator else f"<@{data['creator_id']}>"
        creator_avatar = creator.display_avatar.url if creator else None

        claimer_display = "Unclaimed"
        if data["claimer_id"] != 0:
            claimer = ctx.guild.get_member(data["claimer_id"])
            claimer_display = claimer.mention if claimer else f"<@{data['claimer_id']}>"

        embed = discord.Embed(title=f"📋 Ticket Info — #{data['num']}", color=0x5865F2)
        if creator_avatar:
            embed.set_thumbnail(url=creator_avatar)
        embed.add_field(name="👤 Created By", value=creator_display, inline=True)
        embed.add_field(name="📋 Category", value=f"{emoji} {label}", inline=True)
        embed.add_field(name="🔢 Ticket #", value=f"#{data['num']}", inline=True)
        embed.add_field(name="🙋 Claimed By", value=claimer_display, inline=True)
        embed.add_field(name="🟢 Status", value="Open", inline=True)
        embed.add_field(name="📁 Channel", value=ctx.channel.mention, inline=True)
        embed.set_footer(text=f"Requested by {ctx.author} • {ctx.guild.name}")
        embed.timestamp = discord.utils.utcnow()
        await ctx.reply(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
