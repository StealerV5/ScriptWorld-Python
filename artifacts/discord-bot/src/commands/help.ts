import { Message, Client, EmbedBuilder } from "discord.js";
import { readdirSync } from "fs";
import { join } from "path";
import type { Command } from "../types";

const command: Command = {
  name: "help",
  aliases: ["h", "commands"],
  description: "Shows a list of all commands",
  usage: "m.help [command]",
  async execute(message: Message, args: string[], _client: Client) {
    const commandFiles = readdirSync(join(__dirname)).filter(
      (f) => f.endsWith(".ts") || f.endsWith(".js")
    );

    if (args[0]) {
      const targetFile = commandFiles.find((f) => f.replace(/\.(ts|js)$/, "") === args[0].toLowerCase());
      if (!targetFile) {
        await message.reply(`No command named \`${args[0]}\` found.`);
        return;
      }
      const cmd: Command = require(join(__dirname, targetFile)).default;
      const embed = new EmbedBuilder()
        .setColor(0x5865f2)
        .setTitle(`Command: m.${cmd.name}`)
        .setDescription(cmd.description)
        .addFields(
          { name: "Usage", value: `\`${cmd.usage ?? `m.${cmd.name}`}\`` },
          { name: "Aliases", value: cmd.aliases?.map((a) => `\`${a}\``).join(", ") ?? "None" }
        );
      await message.reply({ embeds: [embed] });
      return;
    }

    const commands: Command[] = commandFiles
      .map((f) => require(join(__dirname, f)).default)
      .filter(Boolean);

    const modCmds = commands.filter((c) =>
      ["kick", "ban", "unban", "mute", "unmute", "warn", "warnings", "purge", "slowmode", "lock", "unlock"].includes(c.name)
    );
    const chatCmds = commands.filter((c) =>
      !modCmds.includes(c) && c.name !== "help"
    );

    const embed = new EmbedBuilder()
      .setColor(0x5865f2)
      .setTitle("Bot Commands — Prefix: `m.`")
      .setDescription("Use `m.help <command>` for details on a specific command.")
      .addFields(
        {
          name: "💬 Chat",
          value: chatCmds.map((c) => `\`m.${c.name}\` — ${c.description}`).join("\n") || "None",
        },
        {
          name: "🔨 Moderation",
          value: modCmds.map((c) => `\`m.${c.name}\` — ${c.description}`).join("\n") || "None",
        }
      )
      .setFooter({ text: "[] = optional, <> = required" });

    await message.reply({ embeds: [embed] });
  },
};

export default command;
