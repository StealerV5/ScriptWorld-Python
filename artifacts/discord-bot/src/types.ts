import { Client, Message } from "discord.js";

export interface Command {
  name: string;
  aliases?: string[];
  description: string;
  usage?: string;
  execute(message: Message, args: string[], client: Client): Promise<void>;
}
