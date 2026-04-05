import { Message, Client, PermissionFlagsBits, EmbedBuilder } from "discord.js";
import type { Command } from "../types";

const command: Command = {
  name: "unmute",
  aliases: ["untimeout"],
  description: "Remove a timeout from a member",
  usage: "m.unmute <@user>",
  async execute(message: Message, _args: string[], _client: Client) {
    if (!message.member?.permissions.has(PermissionFlagsBits.ModerateMembers)) {
      await message.reply("You need the **Moderate Members** permission.");
      return;
    }
    const target = message.mentions.members?.first();
    if (!target) {
      await message.reply("Please mention a user to unmute.");
      return;
    }
    if (!target.moderatable) {
      await message.reply("I cannot unmute that user.");
      return;
    }
    await target.timeout(null);
    const embed = new EmbedBuilder()
      .setColor(0x00ff00)
      .setTitle("Member Unmuted")
      .addFields(
        { name: "User", value: `${target.user.tag} (${target.id})`, inline: true },
        { name: "Moderator", value: message.author.tag, inline: true }
      )
      .setTimestamp();
    await message.reply({ embeds: [embed] });
  },
};

export default command;
