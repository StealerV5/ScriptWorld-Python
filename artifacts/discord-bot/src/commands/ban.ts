import { Message, Client, PermissionFlagsBits, EmbedBuilder } from "discord.js";
import type { Command } from "../types";

const command: Command = {
  name: "ban",
  description: "Ban a member from the server",
  usage: "m.ban <@user> [reason]",
  async execute(message: Message, args: string[], _client: Client) {
    if (!message.member?.permissions.has(PermissionFlagsBits.BanMembers)) {
      await message.reply("You need the **Ban Members** permission.");
      return;
    }
    const target = message.mentions.members?.first();
    if (!target) {
      await message.reply("Please mention a user to ban.");
      return;
    }
    if (!target.bannable) {
      await message.reply("I cannot ban that user (they may have a higher role than me).");
      return;
    }
    const reason = args.slice(1).join(" ") || "No reason provided";
    await target.ban({ reason, deleteMessageSeconds: 60 * 60 * 24 });
    const embed = new EmbedBuilder()
      .setColor(0xff0000)
      .setTitle("Member Banned")
      .addFields(
        { name: "User", value: `${target.user.tag} (${target.id})`, inline: true },
        { name: "Moderator", value: message.author.tag, inline: true },
        { name: "Reason", value: reason }
      )
      .setTimestamp();
    await message.reply({ embeds: [embed] });
  },
};

export default command;
