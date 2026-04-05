import { Message, Client, PermissionFlagsBits } from "discord.js";
import type { Command } from "../types";

const command: Command = {
  name: "say",
  description: "Make the bot say something (mods only)",
  usage: "m.say <message>",
  async execute(message: Message, args: string[], _client: Client) {
    if (!message.member?.permissions.has(PermissionFlagsBits.ManageMessages)) {
      await message.reply("You need the **Manage Messages** permission to use this command.");
      return;
    }
    if (!args.length) {
      await message.reply("Please provide a message to say.");
      return;
    }
    await message.delete().catch(() => null);
    await message.channel.send(args.join(" "));
  },
};

export default command;
