import { Message, Client, PermissionFlagsBits } from "discord.js";
import type { Command } from "../types";

const command: Command = {
  name: "purge",
  aliases: ["clear", "clean"],
  description: "Delete a number of messages (1–100)",
  usage: "m.purge <amount>",
  async execute(message: Message, args: string[], _client: Client) {
    if (!message.member?.permissions.has(PermissionFlagsBits.ManageMessages)) {
      await message.reply("You need the **Manage Messages** permission.");
      return;
    }
    const amount = parseInt(args[0]);
    if (isNaN(amount) || amount < 1 || amount > 100) {
      await message.reply("Please provide a number between 1 and 100.");
      return;
    }
    if (!message.channel.isTextBased() || message.channel.isDMBased()) {
      await message.reply("This command can only be used in a server text channel.");
      return;
    }
    await message.delete().catch(() => null);
    const deleted = await (message.channel as import("discord.js").TextChannel).bulkDelete(amount, true);
    const notice = await message.channel.send(`🗑️ Deleted **${deleted.size}** messages.`);
    setTimeout(() => notice.delete().catch(() => null), 4000);
  },
};

export default command;
