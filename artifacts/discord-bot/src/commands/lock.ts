import { Message, Client, PermissionFlagsBits, TextChannel, OverwriteType } from "discord.js";
import type { Command } from "../types";

const command: Command = {
  name: "lock",
  description: "Lock the current channel (prevent @everyone from sending messages)",
  usage: "m.lock",
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
      SendMessages: false,
    });
    await message.reply("🔒 Channel locked. Only moderators can send messages.");
  },
};

export default command;
