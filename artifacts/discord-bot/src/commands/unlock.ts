import { Message, Client, PermissionFlagsBits, TextChannel } from "discord.js";
import type { Command } from "../types";

const command: Command = {
  name: "unlock",
  description: "Unlock the current channel",
  usage: "m.unlock",
  async execute(message: Message, _args: string[], _client: Client) {
    if (!message.member?.permissions.has(PermissionFlagsBits.ManageChannels)) {
      await message.reply("You need the **Manage Channels** permission.");
      return;
    }
    if (!(message.channel instanceof TextChannel)) {
      await message.reply("This can only be used in a text channel.");
      return;
    }
    const everyoneRole = message.guild?.roles.everyone;
    if (!everyoneRole) return;

    await message.channel.permissionOverwrites.edit(everyoneRole, {
      SendMessages: null,
    });
    await message.reply("🔓 Channel unlocked. Everyone can send messages again.");
  },
};

export default command;
