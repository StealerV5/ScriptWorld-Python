import { Message, Client, EmbedBuilder } from "discord.js";
import type { Command } from "../types";

const command: Command = {
  name: "avatar",
  aliases: ["av", "pfp"],
  description: "Get a user's avatar",
  usage: "m.avatar [@user]",
  async execute(message: Message, _args: string[], _client: Client) {
    const target =
      message.mentions.users.first() ?? message.author;

    const embed = new EmbedBuilder()
      .setColor(0x5865f2)
      .setTitle(`${target.username}'s Avatar`)
      .setImage(target.displayAvatarURL({ size: 1024 }))
      .setURL(target.displayAvatarURL({ size: 1024 }));

    await message.reply({ embeds: [embed] });
  },
};

export default command;
