import { Message, Client, EmbedBuilder } from "discord.js";
import type { Command } from "../types";
import { getWarnings } from "./warn";

const command: Command = {
  name: "warnings",
  aliases: ["warns"],
  description: "View warnings for a user",
  usage: "m.warnings [@user]",
  async execute(message: Message, _args: string[], _client: Client) {
    const target = message.mentions.users.first() ?? message.author;
    const list = getWarnings(target.id);

    const embed = new EmbedBuilder()
      .setColor(0xffff00)
      .setTitle(`Warnings for ${target.tag}`)
      .setDescription(
        list.length === 0
          ? "No warnings on record."
          : list
              .map(
                (w, i) =>
                  `**${i + 1}.** ${w.reason} — by ${w.mod} <t:${Math.floor(w.at / 1000)}:R>`
              )
              .join("\n")
      )
      .setFooter({ text: `Total: ${list.length}` })
      .setTimestamp();

    await message.reply({ embeds: [embed] });
  },
};

export default command;
