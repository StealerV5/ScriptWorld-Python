import OpenAI from "openai";
import { Message, TextChannel } from "discord.js";

const openai = new OpenAI({
  baseURL: process.env.AI_INTEGRATIONS_OPENAI_BASE_URL,
  apiKey: process.env.AI_INTEGRATIONS_OPENAI_API_KEY,
});

const SYSTEM_PROMPT = `You are a chill Gen Z guy who's obsessed with Minecraft and lowkey the coolest person in the server. You talk like a real Gen Z dude — use slang like "no cap", "fr fr", "bro", "ngl", "lowkey", "bussin", "W", "L", "goated", "mid", "based", "deadass" naturally. You're super laid back, a little sarcastic, always confident. Bring up Minecraft whenever remotely relevant. Java > Bedrock, no debate. Keep replies VERY short — 1 sentence max, like a quick Discord message. Use emojis frequently — at least 2-3 per message, scattered naturally throughout. Never sound robotic. If asked about moderation commands, mention the "m." prefix. Never break character.`;

const RANDOM_CHAT_CHANCE = 0.06;

const channelHistory = new Map<string, { role: "user" | "assistant"; content: string }[]>();
const MAX_HISTORY = 12;

function getHistory(channelId: string) {
  if (!channelHistory.has(channelId)) {
    channelHistory.set(channelId, []);
  }
  return channelHistory.get(channelId)!;
}

function pushHistory(channelId: string, role: "user" | "assistant", content: string) {
  const history = getHistory(channelId);
  history.push({ role, content });
  if (history.length > MAX_HISTORY) {
    history.splice(0, history.length - MAX_HISTORY);
  }
}

export async function generateReply(
  message: Message,
  trigger: "ping" | "reply" | "random"
): Promise<string | null> {
  const channelId = message.channel.id;
  const history = getHistory(channelId);

  const userContent =
    trigger === "random"
      ? `[Overheard in the chat, chime in naturally if you have something interesting to add]: ${message.author.username}: ${message.content}`
      : `${message.author.username}: ${message.content}`;

  const messages: OpenAI.Chat.ChatCompletionMessageParam[] = [
    { role: "system", content: SYSTEM_PROMPT },
    ...history,
    { role: "user", content: userContent },
  ];

  const response = await openai.chat.completions.create({
    model: "gpt-4o-mini",
    messages,
    max_completion_tokens: 80,
  });

  const raw = response.choices[0]?.message?.content;
  const reply = raw && raw.trim() ? raw.trim() : null;

  if (reply) {
    pushHistory(channelId, "user", userContent);
    pushHistory(channelId, "assistant", reply);
  }

  return reply;
}

export async function handleChatMessage(message: Message): Promise<void> {
  const botUser = message.client.user;
  if (!botUser) return;

  const isPinged = message.mentions.has(botUser);
  const isReply =
    !!message.reference?.messageId &&
    (await message.channel.messages
      .fetch(message.reference.messageId)
      .then((m) => m.author.id === botUser.id)
      .catch(() => false));

  const shouldRespond =
    isPinged || isReply || Math.random() < RANDOM_CHAT_CHANCE;

  if (!shouldRespond) return;

  const trigger: "ping" | "reply" | "random" = isPinged
    ? "ping"
    : isReply
    ? "reply"
    : "random";

  try {
    if (message.channel instanceof TextChannel || message.channel.isThread()) {
      await (message.channel as TextChannel).sendTyping();
    }

    const reply = await generateReply(message, trigger);

    if (!reply) return;

    if (isPinged || isReply) {
      await message.reply(reply);
    } else {
      await message.channel.send(reply);
    }
  } catch (err) {
    console.error("Chat error:", err);
  }
}
