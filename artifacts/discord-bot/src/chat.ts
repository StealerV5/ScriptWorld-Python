import OpenAI from "openai";
import { Message, TextChannel } from "discord.js";

const openai = new OpenAI({
  baseURL: process.env.AI_INTEGRATIONS_OPENAI_BASE_URL,
  apiKey: process.env.AI_INTEGRATIONS_OPENAI_API_KEY,
});

const SYSTEM_PROMPT = `You are a friendly, witty Discord bot. You are helpful, occasionally funny, and feel like a real member of the server. Keep your replies concise — usually 1-3 sentences. Don't use excessive emojis. Don't start every message the same way. Vary your tone: sometimes casual, sometimes helpful, always genuine. If asked about moderation commands, mention the "m." prefix. Never break character or reveal you are an AI model by a specific company.`;

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
): Promise<string> {
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
    model: "gpt-5-mini",
    messages,
    max_completion_tokens: 300,
  });

  const reply = response.choices[0]?.message?.content ?? "...";

  pushHistory(channelId, "user", userContent);
  pushHistory(channelId, "assistant", reply);

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

    if (isPinged || isReply) {
      await message.reply(reply);
    } else {
      await message.channel.send(reply);
    }
  } catch (err) {
    console.error("Chat error:", err);
  }
}
