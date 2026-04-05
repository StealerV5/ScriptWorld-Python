import { Message, Client, EmbedBuilder } from "discord.js";
import type { Command } from "../types";

const command: Command = {
  name: "serverinfo",
  aliases: ["si", "server"],
  description: "Get info about the server",
  usage: "m.serverinfo",
  async execute(message: Message, _args: string[], _client: Client) {
    const guild = message.guild;
    if (!guild) {
      await message.reply("This command can only be used in a server.");
      return;
    }

    await guild.fetch();

    const embed = new EmbedBuilder()
      .setColor(0x5865f2)
      .setAuthor({ name: guild.name, iconURL: guild.iconURL() ?? undefined })
      .setThumbnail(guild.iconURL({ size: 256 }))
      .addFields(
        { name: "ID", value: guild.id, inline: true },
        { name: "Owner", value: `<@${guild.ownerId}>`, inline: true },
        { name: "Members", value: `${guild.memberCount}`, inline: true },
        { name: "Channels", value: `${guild.channels.cache.size}`, inline: true },
        { name: "Roles", value: `${guild.roles.cache.size}`, inline: true },
        { name: "Boosts", value: `${guild.premiumSubscriptionCount ?? 0} (Tier ${guild.premiumTier})`, inline: true },
        {
          name: "Created",
          value: `<t:${Math.floor(guild.createdAt.getTime() / 1000)}:F>`,
        }
      )
      .setFooter({ text: `Requested by ${message.author.tag}` })
      .setTimestamp();

    await message.reply({ embeds: [embed] });
  },
};

export default command;
