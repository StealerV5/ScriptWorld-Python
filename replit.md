# Workspace

## Overview

pnpm workspace monorepo using TypeScript. Each package manages its own dependencies.

## Stack

- **Monorepo tool**: pnpm workspaces
- **Node.js version**: 24
- **Package manager**: pnpm
- **TypeScript version**: 5.9
- **API framework**: Express 5
- **Database**: PostgreSQL + Drizzle ORM
- **Validation**: Zod (`zod/v4`), `drizzle-zod`
- **API codegen**: Orval (from OpenAPI spec)
- **Build**: esbuild (CJS bundle)

## Key Commands

- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- `pnpm --filter @workspace/api-server run dev` — run API server locally
- `pnpm --filter @workspace/discord-bot run dev` — run Discord bot locally

## Discord Bot (`artifacts/discord-bot`)

A Discord chatbot and moderation bot with prefix `m.` — written in **Python 3.12** using `discord.py`.

**Structure:**
- `bot.py` — entry point, loads cogs, error handling
- `cogs/general.py` — chat & utility commands
- `cogs/moderation.py` — moderation commands
- `cogs/chat.py` — AI chatbot (gpt-4o-mini, Replit AI integration)

### Commands

**Chat / Utility:**
- `m.ping` — Check bot latency
- `m.help [command]` — Show all commands or details for one
- `m.userinfo [@user]` — Show info about a user
- `m.serverinfo` — Show server info
- `m.avatar [@user]` — Show a user's avatar
- `m.say <message>` — Make the bot say something (Manage Messages required)

**Moderation:**
- `m.kick <@user> [reason]` — Kick a member
- `m.ban <@user> [reason]` — Ban a member
- `m.unban <userID> [reason]` — Unban by user ID
- `m.mute <@user> <duration> [reason]` — Timeout a member (e.g. `10m`, `2h`, `1d`)
- `m.unmute <@user>` — Remove a timeout
- `m.warn <@user> [reason]` — Warn a member (sends DM)
- `m.warnings [@user]` — View warnings for a user
- `m.purge <1-100>` — Bulk delete messages
- `m.slowmode <seconds>` — Set channel slowmode (0 to disable)
- `m.lock` — Lock channel (prevent @everyone from sending)
- `m.unlock` — Unlock channel

### Environment Variables
- `DISCORD_BOT_TOKEN` — Bot token from Discord Developer Portal (stored as secret)

See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details.
