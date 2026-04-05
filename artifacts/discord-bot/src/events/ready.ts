import { Client, Events } from "discord.js";

export default {
  name: Events.ClientReady,
  once: true,
  async execute(client: Client) {
    console.log(`✅ Logged in as ${client.user?.tag}`);
    console.log(`Serving ${client.guilds.cache.size} guild(s).`);
    client.user?.setActivity("m.help | Moderation & Chat");
  },
};
