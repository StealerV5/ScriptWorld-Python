import { Message, Client, PermissionFlagsBits, EmbedBuilder } from "discord.js";
import type { Command } from "../types";

const command: Command = {
  name: "unban",
  description: "Unban a user by their ID",
  usage: "m.unban <userID> [reason]",
  async execute(message: Message, args: string[], _client: Client) {
    if (!message.member?.permissions.has(PermissionFlagsBits.BanMembers)) {
      await message.reply("You need the **Ban Members** permission.");
      return;
    }
    const userId = args[0];
    if (!userId) {
      await message.reply("Please provide the user ID to unban.");
      return;
    }
    const reason = args.slice(1).join(" ") || "No reason provided";
    try {
      const unbanned = await message.guild?.bans.remove(userId, reason);
      const embed = new EmbedBuilder()
        .setColor(0x00ff00)
        .setTitle("User Unbanned")
        .addFields(
          { name: "User", value: unbanned ? `${unbanned.tag} (${unbanned.id})` : userId, inline: true },
          { name: "Moderator", value: message.author.tag, inline: true },
          { name: "Reason", value: reason }
        )
        .setTimestamp();
      await message.reply({ embeds: [embed] });
    } catch {
      await message.reply("Could not unban that user. Are they actually banned?");
    }
  },
};

export default command;
