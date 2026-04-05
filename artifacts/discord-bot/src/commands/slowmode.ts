import { Message, Client, PermissionFlagsBits, TextChannel } from "discord.js";
import type { Command } from "../types";

const command: Command = {
  name: "slowmode",
  aliases: ["slow"],
  description: "Set slowmode for a channel (0 to disable, max 21600s)",
  usage: "m.slowmode <seconds>",
  async execute(message: Message, args: string[], _client: Client) {
    if (!message.member?.permissions.has(PermissionFlagsBits.ManageChannels)) {
      await message.reply("You need the **Manage Channels** permission.");
      return;
    }
    const seconds = parseInt(args[0]);
    if (isNaN(seconds) || seconds < 0 || seconds > 21600) {
      await message.reply("Please provide a number between 0 and 21600 seconds.");
      return;
    }
    if (!(message.channel instanceof TextChannel)) {
      await message.reply("This can only be used in a text channel.");
      return;
    }
    await message.channel.setRateLimitPerUser(seconds);
    if (seconds === 0) {
      await message.reply("✅ Slowmode disabled.");
    } else {
      await message.reply(`✅ Slowmode set to **${seconds} second(s)**.`);
    }
  },
};

export default command;
