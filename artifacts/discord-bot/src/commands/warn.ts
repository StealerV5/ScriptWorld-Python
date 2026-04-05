import { Message, Client, PermissionFlagsBits, EmbedBuilder } from "discord.js";
import type { Command } from "../types";

const warnings: Map<string, { reason: string; mod: string; at: number }[]> = new Map();

export function getWarnings(userId: string) {
  return warnings.get(userId) ?? [];
}

export function addWarning(userId: string, reason: string, mod: string) {
  const list = warnings.get(userId) ?? [];
  list.push({ reason, mod, at: Date.now() });
  warnings.set(userId, list);
  return list.length;
}

const command: Command = {
  name: "warn",
  description: "Warn a member",
  usage: "m.warn <@user> [reason]",
  async execute(message: Message, args: string[], _client: Client) {
    if (!message.member?.permissions.has(PermissionFlagsBits.ManageMessages)) {
      await message.reply("You need the **Manage Messages** permission.");
      return;
    }
    const target = message.mentions.members?.first();
    if (!target) {
      await message.reply("Please mention a user to warn.");
      return;
    }
    const reason = args.slice(1).join(" ") || "No reason provided";
    const count = addWarning(target.id, reason, message.author.tag);

    try {
      await target.user.send(
        `⚠️ You have been warned in **${message.guild?.name}**.\nReason: ${reason}\nTotal warnings: ${count}`
      );
    } catch {
    }

    const embed = new EmbedBuilder()
      .setColor(0xffff00)
      .setTitle("Member Warned")
      .addFields(
        { name: "User", value: `${target.user.tag} (${target.id})`, inline: true },
        { name: "Moderator", value: message.author.tag, inline: true },
        { name: "Total Warnings", value: `${count}`, inline: true },
        { name: "Reason", value: reason }
      )
      .setTimestamp();
    await message.reply({ embeds: [embed] });
  },
};

export default command;
