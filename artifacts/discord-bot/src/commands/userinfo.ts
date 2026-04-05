import { Message, Client, EmbedBuilder } from "discord.js";
import type { Command } from "../types";

const command: Command = {
  name: "userinfo",
  aliases: ["ui", "whois"],
  description: "Get info about a user",
  usage: "m.userinfo [@user]",
  async execute(message: Message, _args: string[], _client: Client) {
    const target =
      message.mentions.members?.first() ?? message.member;

    if (!target) {
      await message.reply("Could not find that user.");
      return;
    }

    const user = target.user;
    const joinedAt = target.joinedAt
      ? `<t:${Math.floor(target.joinedAt.getTime() / 1000)}:F>`
      : "Unknown";
    const createdAt = `<t:${Math.floor(user.createdAt.getTime() / 1000)}:F>`;

    const roles = target.roles.cache
      .filter((r) => r.id !== message.guild?.id)
      .map((r) => r.toString())
      .join(", ") || "None";

    const embed = new EmbedBuilder()
      .setColor(target.displayHexColor === "#000000" ? 0x5865f2 : (target.displayHexColor as `#${string}`))
      .setAuthor({ name: user.tag, iconURL: user.displayAvatarURL() })
      .setThumbnail(user.displayAvatarURL({ size: 256 }))
      .addFields(
        { name: "ID", value: user.id, inline: true },
        { name: "Nickname", value: target.nickname ?? "None", inline: true },
        { name: "Bot?", value: user.bot ? "Yes" : "No", inline: true },
        { name: "Account Created", value: createdAt },
        { name: "Joined Server", value: joinedAt },
        { name: `Roles (${target.roles.cache.size - 1})`, value: roles.length > 1024 ? roles.slice(0, 1021) + "..." : roles }
      )
      .setFooter({ text: `Requested by ${message.author.tag}` })
      .setTimestamp();

    await message.reply({ embeds: [embed] });
  },
};

export default command;
