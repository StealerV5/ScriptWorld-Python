import { Message, Client, PermissionFlagsBits, EmbedBuilder } from "discord.js";
import type { Command } from "../types";

const command: Command = {
  name: "kick",
  description: "Kick a member from the server",
  usage: "m.kick <@user> [reason]",
  async execute(message: Message, args: string[], _client: Client) {
    if (!message.member?.permissions.has(PermissionFlagsBits.KickMembers)) {
      await message.reply("You need the **Kick Members** permission.");
      return;
    }
    const target = message.mentions.members?.first();
    if (!target) {
      await message.reply("Please mention a user to kick.");
      return;
    }
    if (!target.kickable) {
      await message.reply("I cannot kick that user (they may have a higher role than me).");
      return;
    }
    const reason = args.slice(1).join(" ") || "No reason provided";
    await target.kick(reason);
    const embed = new EmbedBuilder()
      .setColor(0xffa500)
      .setTitle("Member Kicked")
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
