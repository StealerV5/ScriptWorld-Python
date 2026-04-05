import { Message, Client, EmbedBuilder } from "discord.js";
import { readdirSync } from "fs";
import { join } from "path";
import type { Command } from "../types";

const MOD_COMMANDS = ["kick", "ban", "unban", "mute", "unmute", "warn", "warnings", "purge", "slowmode", "lock", "unlock"];

const command: Command = {
  name: "cmds",
  aliases: ["commands"],
  description: "List all available commands",
  usage: "m.cmds",
  async execute(message: Message, _args: string[], _client: Client) {
    const files = readdirSync(join(__dirname)).filter((f) =>
      f.endsWith(".ts") || f.endsWith(".js")
    );

    const all: Command[] = files
      .map((f) => {
        try { return require(join(__dirname, f)).default; } catch { return null; }
      })
      .filter((c): c is Command => !!c?.name);

    const chat = all.filter((c) => !MOD_COMMANDS.includes(c.name));
    const mod  = all.filter((c) => MOD_COMMANDS.includes(c.name));

    const fmt = (c: Command) =>
      `**\`${c.usage ?? `m.${c.name}`}\`**\n${c.description}`;

    const embed = new EmbedBuilder()
      .setColor(0x5865f2)
      .setTitle("📋 Command List")
      .setDescription("Prefix: **`m.`**  •  Use `m.help <command>` for more details on any command.")
      .addFields(
        {
          name: "💬 Chat & Utility",
          value: chat.map(fmt).join("\n\n"),
        },
        {
          name: "🔨 Moderation",
          value: mod.map(fmt).join("\n\n"),
        }
      )
      .setFooter({ text: "[] = optional  •  <> = required" })
      .setTimestamp();

    await message.reply({ embeds: [embed] });
  },
};

export default command;
