import discord
from discord.ext import commands
import json
import os
import re

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


def load_count() -> int:
    try:
        with open(DATA_FILE) as f:
            return json.load(f).get("count", 0)
    except (FileNotFoundError, json.JSONDecodeError):
        return 0


def save_count(count: int) -> None:
    with open(DATA_FILE, "w") as f:
        json.dump({"count": count}, f)


def safe_channel_name(name: str, ticket_num: int) -> str:
    cleaned = re.sub(r"[^a-z0-9\-]", "", name.lower().replace(" ", "-").replace("_", "-"))
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    if not cleaned:
        cleaned = "user"
    return f"{cleaned[:40]}-{ticket_num}"


ticket_count: int = load_count()


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
        global ticket_count

        await interaction.response.defer(ephemeral=True)

        value = self.values[0]
        emoji, label = CATEGORY_LABELS[value]
        guild = interaction.guild
        member = interaction.user

        # Increment and persist ticket number
        ticket_count += 1
        save_count(ticket_count)
        num = ticket_count

        # Find or create "Active Tickets" category
        active_cat = discord.utils.get(guild.categories, name="Active Tickets")
        if not active_cat:
            active_cat = await guild.create_category(
                "Active Tickets",
                overwrites={
                    guild.default_role: discord.PermissionOverwrite(view_channel=False)
                },
            )

        # Collect mod roles from the category's permission overwrites
        mod_roles: list[discord.Role] = []
        for target, overwrite in active_cat.overwrites.items():
            if (
                isinstance(target, discord.Role)
                and target != guild.default_role
                and overwrite.view_channel is not False
            ):
                mod_roles.append(target)

        # Channel overwrites: private by default, visible to ticket creator + mods + bot
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

        channel_name = safe_channel_name(member.name, num)
        ticket_channel = await guild.create_text_channel(
            channel_name,
            category=active_cat,
            overwrites=overwrites,
            topic=f"Ticket #{num} | {member} | {label}",
        )

        # ── Ticket channel embed ──
        embed = discord.Embed(
            title=f"🎫 Ticket #{num}",
            color=0x57F287,
        )
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="👤 User", value=member.mention, inline=True)
        embed.add_field(name="📋 Category", value=f"{emoji} {label}", inline=True)
        embed.add_field(name="🔢 Ticket", value=f"#{num}", inline=True)
        embed.add_field(name="🟢 Status", value="Open", inline=True)
        embed.add_field(
            name="\u200b",
            value="\u200b",
            inline=True,
        )
        embed.add_field(
            name="📝 How to get help",
            value="Describe your issue below and a staff member will assist you shortly.",
            inline=False,
        )
        embed.set_footer(text=f"Ticket created • {guild.name}")
        embed.timestamp = discord.utils.utcnow()

        # Ping the user + all mod roles
        pings = member.mention
        if mod_roles:
            pings += " " + " ".join(r.mention for r in mod_roles)

        await ticket_channel.send(content=pings, embed=embed)

        # ── Success reply (ephemeral) ──
        success = discord.Embed(
            title="✅ Ticket Created!",
            description=(
                f"Your ticket has been created: {ticket_channel.mention}\n\n"
                "A staff member will be with you shortly. Please describe your issue there."
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
        await interaction.response.send_message(
            embed=embed, view=CategoryView(), ephemeral=True
        )


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(OpenTicketButton())


# ─────────────────────── Cog ───────────────────────

class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        # Re-register the persistent view so it survives bot restarts
        self.bot.add_view(TicketPanelView())

    @commands.command(name="ticketsetup")
    @commands.guild_only()
    async def ticketsetup(self, ctx: commands.Context):
        """Owner-only: Post the ticket support panel"""
        if ctx.author.id != ctx.guild.owner_id:
            await ctx.reply("❌ Only the server owner can use this command.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🎫 Ticket Support",
            description="Make a ticket if you need help with something",
            color=0x5865F2,
        )
        embed.add_field(
            name="📌 How it works",
            value=(
                "1. Click **Open Ticket** below\n"
                "2. Select the category that fits your issue\n"
                "3. A private channel will be created just for you\n"
                "4. Our staff will assist you shortly!"
            ),
            inline=False,
        )
        embed.add_field(
            name="⚠️ Before opening a ticket",
            value=(
                "• Make sure your issue isn't already answered in the FAQ\n"
                "• Provide as much detail as possible\n"
                "• Be patient — staff will respond when available"
            ),
            inline=False,
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text=ctx.guild.name)
        embed.timestamp = discord.utils.utcnow()

        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        await ctx.send(embed=embed, view=TicketPanelView())


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
