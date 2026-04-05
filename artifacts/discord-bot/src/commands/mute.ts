import { Message, Client, PermissionFlagsBits, EmbedBuilder } from "discord.js";
import type { Command } from "../types";

function parseDuration(str: string): number | null {
  const match = str.match(/^(\d+)(s|m|h|d)$/i);
  if (!match) return null;
  const value = parseInt(match[1]);
  const unit = match[2].toLowerCase();
  const multipliers: Record<string, number> = { s: 1, m: 60, h: 3600, d: 86400 };
  return value * multipliers[unit] * 1000;
}

const command: Command = {
  name: "mute",
  aliases: ["timeout"],
  description: "Timeout (mute) a member. Duration: 10s, 5m, 2h, 1d",
  usage: "m.mute <@user> <duration> [reason]",
  async execute(message: Message, args: string[], _client: Client) {
    if (!message.member?.permissions.has(PermissionFlagsBits.ModerateMembers)) {
      await message.reply("You need the **Moderate Members** permission.");
      return;
    }
    const target = message.mentions.members?.first();
    if (!target) {
      await message.reply("Please mention a user to mute.");
      return;
    }
    const durationStr = args[1];
    if (!durationStr) {
      await message.reply("Please provide a duration (e.g. `10m`, `1h`, `2d`).");
      return;
    }
    const duration = parseDuration(durationStr);
    if (!duration) {
      await message.reply("Invalid duration format. Use: `10s`, `5m`, `2h`, `1d`");
      return;
    }
    if (duration > 28 * 24 * 60 * 60 * 1000) {
      await message.reply("Max timeout duration is 28 days.");
      return;
    }
    if (!target.moderatable) {
      await message.reply("I cannot timeout that user.");
      return;
    }
    const reason = args.slice(2).join(" ") || "No reason provided";
    await target.timeout(duration, reason);
    const until = new Date(Date.now() + duration);
    const embed = new EmbedBuilder()
      .setColor(0xffa500)
      .setTitle("Member Muted (Timeout)")
      .addFields(
        { name: "User", value: `${target.user.tag} (${target.id})`, inline: true },
        { name: "Moderator", value: message.author.tag, inline: true },
        { name: "Duration", value: durationStr, inline: true },
        { name: "Expires", value: `<t:${Math.floor(until.getTime() / 1000)}:R>` },
        { name: "Reason", value: reason }
      )
      .setTimestamp();
    await message.reply({ embeds: [embed] });
  },
};

export default command;
