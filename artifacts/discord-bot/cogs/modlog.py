import discord
from discord.ext import commands
import json
import os
import asyncio

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "logging.json")
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

# action_key -> (emoji, title, color)
ACTIONS: dict[str, tuple[str, str, int]] = {
    "ban":      ("🔨", "Member Banned",    0xED4245),
    "kick":     ("👢", "Member Kicked",    0xE67E22),
    "mute":     ("🔇", "Member Muted",     0xFEE75C),
    "unmute":   ("🔊", "Member Unmuted",   0x57F287),
    "warn":     ("⚠️",  "Member Warned",   0xFEE75C),
    "unban":    ("🔓", "Member Unbanned",  0x57F287),
    "slowmode": ("⏱️", "Slowmode Set",     0x5865F2),
    "lock":     ("🔒", "Channel Locked",   0xED4245),
    "unlock":   ("🔓", "Channel Unlocked", 0x57F287),
    "purge":    ("🗑️",  "Messages Purged",  0x5865F2),
}

AUDIT_ACTION_MAP = {
    discord.AuditLogAction.ban:   "ban",
    discord.AuditLogAction.kick:  "kick",
    discord.AuditLogAction.unban: "unban",
}


# ─────────────────────── Data helpers ───────────────────────

def load_data() -> dict:
    try:
        with open(DATA_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"guilds": {}}


def save_data(data: dict) -> None:
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_logging_settings(guild_id: int) -> dict:
    return load_data().get("guilds", {}).get(str(guild_id), {})


def save_logging_settings(guild_id: int, settings: dict) -> None:
    data = load_data()
    data.setdefault("guilds", {})[str(guild_id)] = settings
    save_data(data)


def parse_footer(footer_text: str) -> tuple[int, int, str]:
    """Extract target_id, mod_id, action from the embed footer."""
    parts = {}
    for segment in footer_text.split(" | "):
        if ":" in segment:
            k, v = segment.split(":", 1)
            parts[k.strip()] = v.strip()
    return (
        int(parts.get("target", 0)),
        int(parts.get("mod", 0)),
        parts.get("action", "unknown"),
    )


def build_footer(target_id: int, mod_id: int, action: str) -> str:
    return f"target:{target_id} | mod:{mod_id} | action:{action}"


# ─────────────────────── Modals ───────────────────────

class ChangeReasonModal(discord.ui.Modal, title="Change Reason"):
    new_reason: discord.ui.TextInput = discord.ui.TextInput(
        label="New Reason",
        style=discord.TextStyle.paragraph,
        placeholder="Enter the updated reason...",
        max_length=500,
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        msg = interaction.message
        if not msg or not msg.embeds:
            await interaction.response.send_message("❌ Couldn't find the log embed.", ephemeral=True)
            return

        embed = msg.embeds[0].copy()
        updated = False
        for i, field in enumerate(embed.fields):
            if "Reason" in field.name:
                embed.set_field_at(i, name=field.name, value=self.new_reason.value, inline=field.inline)
                updated = True
                break

        if not updated:
            await interaction.response.send_message("❌ No reason field found in this log.", ephemeral=True)
            return

        try:
            await msg.edit(embed=embed)
        except (discord.Forbidden, discord.HTTPException):
            # Webhook message — use stored webhook URL to edit
            settings = get_logging_settings(interaction.guild_id)
            webhook_url = settings.get("webhook_url")
            if webhook_url:
                try:
                    wh = discord.Webhook.from_url(webhook_url, client=interaction.client)
                    await wh.edit_message(msg.id, embed=embed)
                except Exception:
                    await interaction.response.send_message("❌ Failed to edit webhook message.", ephemeral=True)
                    return
            else:
                await interaction.response.send_message("❌ Could not edit the message.", ephemeral=True)
                return

        await interaction.response.send_message("✅ Reason updated successfully.", ephemeral=True)


# ─────────────────────── DM sub-view ───────────────────────

class DMOptionsView(discord.ui.View):
    def __init__(self, target_id: int, mod_id: int, action: str, guild_name: str):
        super().__init__(timeout=120)
        self.target_id = target_id
        self.mod_id = mod_id
        self.action = action
        self.guild_name = guild_name

    async def _send_dm(self, interaction: discord.Interaction, user_id: int, message: str, label: str) -> None:
        try:
            user = await interaction.client.fetch_user(user_id)
            await user.send(message)
            await interaction.response.send_message(
                f"✅ **{label}** DM sent to **{user}**.", ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Couldn't DM that user — they may have DMs disabled.", ephemeral=True
            )
        except Exception:
            await interaction.response.send_message("❌ Failed to send DM.", ephemeral=True)

    @discord.ui.button(label="Apologize", style=discord.ButtonStyle.secondary, emoji="😔", row=0)
    async def apologize(self, interaction: discord.Interaction, button: discord.ui.Button):
        msg = (
            f"Hi there,\n\n"
            f"We sincerely apologize for the recent moderation action (**{self.action}**) "
            f"taken against you in **{self.guild_name}**. We understand this may have been "
            f"a frustrating experience, and we truly appreciate your patience.\n\n"
            f"If you have any concerns or believe this action was unjust, please don't "
            f"hesitate to open a support ticket — we're here to help.\n\n"
            f"— The **{self.guild_name}** Staff Team"
        )
        await self._send_dm(interaction, self.target_id, msg, "Apologize")

    @discord.ui.button(label="Follow Up", style=discord.ButtonStyle.secondary, emoji="📬", row=0)
    async def follow_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        msg = (
            f"Hi there,\n\n"
            f"We're reaching out to follow up regarding your recent **{self.action}** in "
            f"**{self.guild_name}**. Please take a moment to review our server rules to "
            f"ensure this doesn't happen again.\n\n"
            f"If you believe this action was a mistake or have any questions, feel free to "
            f"open a support ticket — we'll look into it.\n\n"
            f"We hope to see you remain a positive part of our community!\n\n"
            f"— The **{self.guild_name}** Staff Team"
        )
        await self._send_dm(interaction, self.target_id, msg, "Follow Up")

    @discord.ui.button(label="Angry", style=discord.ButtonStyle.danger, emoji="😡", row=1)
    async def angry(self, interaction: discord.Interaction, button: discord.ui.Button):
        msg = (
            f"Hi,\n\n"
            f"A moderation action you recently performed in **{self.guild_name}** has been "
            f"reviewed and found to be unwarranted or improperly handled.\n\n"
            f"Please carefully review the moderation guidelines before taking further action. "
            f"Repeated misuse of moderation permissions may result in your moderator role "
            f"being revoked.\n\n"
            f"— **{self.guild_name}** Management"
        )
        await self._send_dm(interaction, self.mod_id, msg, "Angry")

    @discord.ui.button(label="Good", style=discord.ButtonStyle.success, emoji="👍", row=1)
    async def good(self, interaction: discord.Interaction, button: discord.ui.Button):
        msg = (
            f"Hi,\n\n"
            f"We wanted to take a moment to recognize the recent moderation action you "
            f"handled in **{self.guild_name}**. It was well-judged and helped maintain a "
            f"safe and welcoming environment for everyone.\n\n"
            f"Keep up the excellent work — it truly makes a difference!\n\n"
            f"— **{self.guild_name}** Management"
        )
        await self._send_dm(interaction, self.mod_id, msg, "Good")


# ─────────────────────── Log view (persistent) ───────────────────────

class ChangeReasonButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Change Reason",
            style=discord.ButtonStyle.secondary,
            emoji="✏️",
            custom_id="modlog_change_reason_v1",
        )

    async def callback(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ You need Manage Messages to do this.", ephemeral=True)
            return
        await interaction.response.send_modal(ChangeReasonModal())


class DMUsersButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="DM Users Involved",
            style=discord.ButtonStyle.primary,
            emoji="✉️",
            custom_id="modlog_dm_users_v1",
        )

    async def callback(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ You need Manage Messages to do this.", ephemeral=True)
            return

        embeds = interaction.message.embeds
        if not embeds or not embeds[0].footer or not embeds[0].footer.text:
            await interaction.response.send_message("❌ Couldn't read log data.", ephemeral=True)
            return

        target_id, mod_id, action = parse_footer(embeds[0].footer.text)
        _, action_label, _ = ACTIONS.get(action, ("", action.title(), 0))

        embed = discord.Embed(
            title="✉️ DM Users Involved",
            description="Choose a message type and who to send it to:",
            color=0x5865F2,
        )
        embed.add_field(
            name="👤 For the Member",
            value=(
                "😔 **Apologize** — Send an apology for the moderation action\n"
                "📬 **Follow Up** — Follow up about the action taken"
            ),
            inline=False,
        )
        embed.add_field(
            name="🛡️ For the Moderator",
            value=(
                "😡 **Angry** — Reprimand them for handling it wrongly\n"
                "👍 **Good** — Compliment them for handling it well"
            ),
            inline=False,
        )
        embed.set_footer(text="Only you can see this.")

        view = DMOptionsView(target_id, mod_id, action_label, interaction.guild.name)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class LogView(discord.ui.View):
    """Persistent log view. Pass jump_url when first sending; omit when registering at startup."""

    def __init__(self, jump_url: str = ""):
        super().__init__(timeout=None)
        self.add_item(ChangeReasonButton())
        if jump_url:
            self.add_item(discord.ui.Button(
                label="Jump to Context",
                style=discord.ButtonStyle.link,
                emoji="🔗",
                url=jump_url,
            ))
        self.add_item(DMUsersButton())


# ─────────────────────── Cog ───────────────────────

class ModLog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(LogView())

    # ── Logging helper ─────────────────────────────────

    async def log_action(self, data: dict) -> None:
        """Send a formatted log embed to the guild's configured log channel."""
        guild: discord.Guild | None = self.bot.get_guild(data["guild_id"])
        if not guild:
            return

        settings = get_logging_settings(guild.id)
        channel_id = settings.get("channel_id")
        if not channel_id:
            return

        log_channel: discord.TextChannel | None = guild.get_channel(channel_id)
        if not log_channel:
            return

        action = data["action"]
        emoji, title, color = ACTIONS.get(action, ("📋", action.title(), 0x5865F2))

        embed = discord.Embed(title=f"{emoji} {title}", color=color)
        embed.set_author(
            name=data.get("target_name", "Unknown User"),
            icon_url=data.get("target_avatar") or None,
        )

        target_id = data.get("target_id", 0)
        mod_id = data.get("mod_id", 0)

        embed.add_field(name="👤 User", value=f"<@{target_id}> (`{target_id}`)", inline=True)
        embed.add_field(name="🛡️ Moderator", value=f"<@{mod_id}> (`{mod_id}`)", inline=True)

        if data.get("extra"):
            embed.add_field(name="📌 Details", value=data["extra"], inline=True)

        if data.get("reason"):
            embed.add_field(name="📋 Reason", value=data["reason"], inline=False)

        embed.set_footer(text=build_footer(target_id, mod_id, action))
        embed.timestamp = discord.utils.utcnow()

        jump_url = data.get("jump_url", "")
        view = LogView(jump_url=jump_url)

        webhook_url = settings.get("webhook_url")
        if webhook_url:
            try:
                wh = discord.Webhook.from_url(webhook_url, client=self.bot)
                await wh.send(
                    embed=embed,
                    view=view,
                    username="Mod Logs",
                    avatar_url=str(guild.icon.url) if guild.icon else discord.utils.MISSING,
                    wait=True,
                )
                return
            except Exception:
                pass  # Fall through to regular send

        await log_channel.send(embed=embed, view=view)

    # ── Event: internal mod commands ───────────────────

    @commands.Cog.listener()
    async def on_mod_log(self, data: dict):
        await self.log_action(data)

    # ── Event: audit log (external/other bots) ─────────

    @commands.Cog.listener()
    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry):
        guild = entry.guild
        settings = get_logging_settings(guild.id)

        if not settings.get("channel_id"):
            return
        if not settings.get("include_audit_log"):
            return
        if entry.user_id == guild.me.id:
            return  # Already logged by our command

        user = entry.user  # Who performed the action
        if user and user.bot and not settings.get("include_bots"):
            return

        action_key = AUDIT_ACTION_MAP.get(entry.action)

        # Detect timeouts via member_update
        if entry.action == discord.AuditLogAction.member_update:
            after = getattr(entry.changes.after, "timed_out_until", None)
            before = getattr(entry.changes.before, "timed_out_until", None)
            if after and not before:
                action_key = "mute"
            elif not after and before:
                action_key = "unmute"

        if not action_key:
            return

        target = entry.target
        target_id = target.id if target else 0
        target_name = str(target) if target else "Unknown"

        mod_id = entry.user_id or 0
        mod_name = str(entry.user) if entry.user else "Unknown"
        reason = entry.reason or "No reason provided"

        await self.log_action({
            "guild_id":      guild.id,
            "action":        action_key,
            "target_id":     target_id,
            "target_name":   target_name,
            "target_avatar": None,
            "mod_id":        mod_id,
            "mod_name":      mod_name,
            "reason":        reason,
            "jump_url":      "",
            "extra":         f"Via audit log • by {mod_name}",
        })

    # ── m.loggingsetup wizard ──────────────────────────

    async def _ask(self, ctx: commands.Context, embed: discord.Embed, timeout: int = 60) -> discord.Message | None:
        await ctx.send(embed=embed)
        try:
            return await self.bot.wait_for(
                "message",
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            timed = discord.Embed(
                title="⏰ Setup Timed Out",
                description="You took too long to respond. Run `m.loggingsetup` again to restart.",
                color=0xED4245,
            )
            await ctx.send(embed=timed)
            return None

    async def _try_delete(self, msg: discord.Message) -> None:
        try:
            await msg.delete()
        except (discord.Forbidden, discord.NotFound):
            pass

    @commands.command(name="loggingsetup")
    @commands.guild_only()
    async def loggingsetup(self, ctx: commands.Context):
        """Owner-only: Interactive setup wizard for the mod log"""
        if ctx.author.id != ctx.guild.owner_id:
            await ctx.reply("❌ Only the server owner can use this command.")
            return

        await self._try_delete(ctx.message)

        # ── Step 1 — Log channel ──────────────────────
        q1 = discord.Embed(
            title="📋 Logging Setup — Step 1 of 3",
            description=(
                "**Which channel should moderation logs be sent to?**\n\n"
                "Mention the channel (e.g. `#mod-logs`).\n"
                "This is where all moderation actions will be recorded."
            ),
            color=0x5865F2,
        )
        q1.set_footer(text="You have 60 seconds to respond • Step 1 of 3")

        reply1 = await self._ask(ctx, q1)
        if reply1 is None:
            return

        if not reply1.channel_mentions:
            await ctx.send("❌ No channel mentioned. Please run `m.loggingsetup` again and mention a channel.")
            await self._try_delete(reply1)
            return

        log_channel = reply1.channel_mentions[0]
        await self._try_delete(reply1)

        # ── Step 2 — Webhook ──────────────────────────
        q2 = discord.Embed(
            title="📋 Logging Setup — Step 2 of 3",
            description=(
                "**Should logs be sent via a webhook?**\n\n"
                "🔹 **`yes`** — Logs appear under a custom **\"Mod Logs\"** sender with the server icon "
                "(requires the bot to have Manage Webhooks permission)\n\n"
                "🔸 **`no`** — Logs are sent normally from the bot\n\n"
                "Reply with `yes` or `no`."
            ),
            color=0x5865F2,
        )
        q2.set_footer(text="You have 60 seconds to respond • Step 2 of 3")

        reply2 = await self._ask(ctx, q2)
        if reply2 is None:
            return

        use_webhook = reply2.content.strip().lower() in ("yes", "y")
        await self._try_delete(reply2)

        webhook_url = None
        if use_webhook:
            try:
                wh = await log_channel.create_webhook(
                    name="Mod Logs",
                    avatar=await ctx.guild.icon.read() if ctx.guild.icon else None,
                    reason="m.loggingsetup webhook",
                )
                webhook_url = wh.url
            except discord.Forbidden:
                notice = discord.Embed(
                    title="⚠️ Webhook Warning",
                    description=(
                        "I don't have **Manage Webhooks** permission in that channel. "
                        "Falling back to regular bot messages."
                    ),
                    color=0xFEE75C,
                )
                await ctx.send(embed=notice)
                use_webhook = False

        # ── Step 3 — Include bots + audit log ─────────
        q3 = discord.Embed(
            title="📋 Logging Setup — Step 3 of 3",
            description=(
                "**Should logs include actions from other bots and Discord's audit log?**\n\n"
                "🔹 **`yes`** — Logs everything: actions by other bots, actions done outside "
                "this bot's commands (e.g. manual bans in the server settings)\n\n"
                "🔸 **`no`** — Only log actions performed through this bot's own commands\n\n"
                "Reply with `yes` or `no`."
            ),
            color=0x5865F2,
        )
        q3.set_footer(text="You have 60 seconds to respond • Step 3 of 3")

        reply3 = await self._ask(ctx, q3)
        if reply3 is None:
            return

        include_external = reply3.content.strip().lower() in ("yes", "y")
        await self._try_delete(reply3)

        # ── Save settings ──────────────────────────────
        settings = {
            "channel_id":       log_channel.id,
            "use_webhook":      use_webhook,
            "webhook_url":      webhook_url,
            "include_bots":     include_external,
            "include_audit_log": include_external,
        }
        save_logging_settings(ctx.guild.id, settings)

        # ── Summary embed ──────────────────────────────
        webhook_display = "✅ Webhook (\"Mod Logs\" sender)" if use_webhook else "❌ Regular bot message"
        external_display = "✅ Yes — includes bots & audit log" if include_external else "❌ No — bot commands only"

        summary = discord.Embed(
            title="✅ Logging Setup Complete!",
            description=f"All moderation actions will now be logged to {log_channel.mention}.",
            color=0x57F287,
        )
        summary.add_field(name="📋 Log Channel", value=log_channel.mention, inline=True)
        summary.add_field(name="🔗 Webhook", value=webhook_display, inline=True)
        summary.add_field(name="🌐 External Logs", value=external_display, inline=True)
        summary.add_field(
            name="🔧 What gets logged",
            value=(
                "• `m.kick` `m.ban` `m.unban`\n"
                "• `m.mute` `m.unmute` `m.warn`\n"
                "• `m.slowmode` `m.lock` `m.unlock` `m.purge`"
                + ("\n• Audit log events from any source" if include_external else "")
            ),
            inline=False,
        )
        summary.set_footer(text="Run m.loggingsetup again to reconfigure.")
        await ctx.send(embed=summary)


async def setup(bot: commands.Bot):
    await bot.add_cog(ModLog(bot))
