import { Message, Client } from "discord.js";
import type { Command } from "../types";

const command: Command = {
  name: "ping",
  aliases: ["pong"],
  description: "Check the bot's latency",
  usage: "m.ping",
  async execute(message: Message, _args: string[], client: Client) {
    const sent = await message.reply("Pinging...");
    const latency = sent.createdTimestamp - message.createdTimestamp;
    const apiLatency = Math.round(client.ws.ping);
    await sent.edit(
      `🏓 Pong! Roundtrip: **${latency}ms** | API: **${apiLatency}ms**`
    );
  },
};

export default command;
