import { Client, GatewayIntentBits, Partials, Collection } from "discord.js";
import { readdirSync } from "fs";
import { join } from "path";
import type { Command } from "./types";
import { handleChatMessage } from "./chat";

const PREFIX = "m.";

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMembers,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
    GatewayIntentBits.GuildMessageReactions,
    GatewayIntentBits.GuildModeration,
  ],
  partials: [Partials.Message, Partials.Channel, Partials.Reaction],
});

const commands = new Collection<string, Command>();

const commandFiles = readdirSync(join(__dirname, "commands")).filter((f) =>
  f.endsWith(".ts") || f.endsWith(".js")
);

for (const file of commandFiles) {
  const command: Command = require(join(__dirname, "commands", file)).default;
  if (command && command.name) {
    commands.set(command.name, command);
  }
}

const eventFiles = readdirSync(join(__dirname, "events")).filter((f) =>
  f.endsWith(".ts") || f.endsWith(".js")
);

for (const file of eventFiles) {
  const event = require(join(__dirname, "events", file)).default;
  if (event.once) {
    client.once(event.name, (...args: unknown[]) => event.execute(...args));
  } else {
    client.on(event.name, (...args: unknown[]) => event.execute(...args));
  }
}

client.on("messageCreate", async (message) => {
  if (message.author.bot) return;

  if (!message.content.startsWith(PREFIX)) {
    await handleChatMessage(message);
    return;
  }

  const args = message.content.slice(PREFIX.length).trim().split(/\s+/);
  const commandName = args.shift()?.toLowerCase();

  if (!commandName) return;

  const command =
    commands.get(commandName) ??
    commands.find((c) => c.aliases?.includes(commandName));

  if (!command) {
    await message.reply(`Unknown command. Try \`${PREFIX}help\` for a list of commands.`);
    return;
  }

  try {
    await command.execute(message, args, client);
  } catch (err) {
    console.error(`Error running command ${commandName}:`, err);
    await message.reply("An error occurred while running that command.");
  }
});

const token = process.env.DISCORD_BOT_TOKEN;
if (!token) {
  console.error("DISCORD_BOT_TOKEN is not set.");
  process.exit(1);
}

client.login(token);
