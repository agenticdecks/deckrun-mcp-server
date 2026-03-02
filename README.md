# Deckrun Free — MCP Server

Generate PDF slide decks from Markdown using any MCP-compatible AI client.
**Free. No authentication required.**

- **API:** `https://free.agenticdecks.com/free/generate`
- **Max:** 10 slides, 50 KB Markdown
- **Output:** Public PDF URL, valid 90 days

## Install

### Via Smithery (easiest — auto-configures your client)

```bash
# Claude Desktop
npx @smithery/cli install @agenticdecks/deckrun-free --client claude

# Cursor
npx @smithery/cli install @agenticdecks/deckrun-free --client cursor

# VS Code (GitHub Copilot)
npx @smithery/cli install @agenticdecks/deckrun-free --client vscode

# OpenAI Codex CLI
npx @smithery/cli install @agenticdecks/deckrun-free --client codex
```

Server page: https://smithery.ai/servers/agenticdecks/deckrun-free

### Google Antigravity

Add to `~/.gemini/antigravity/mcp_config.json` (no local Python install needed):

```json
{
  "mcpServers": {
    "deckrun-free": {
      "serverUrl": "https://free.agenticdecks.com/mcp/"
    }
  }
}
```

### Manual install

```bash
pip install mcp requests
```

## Manual Setup

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "deckrun-free": {
      "command": "python",
      "args": ["/path/to/deckrun_mcp_server.py"]
    }
  }
}
```

Restart Claude Desktop. Then ask: *"Create a 6-slide deck on quantum computing."*

### Cursor

Edit `.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global):

```json
{
  "mcpServers": {
    "deckrun-free": {
      "command": "python",
      "args": ["/path/to/deckrun_mcp_server.py"]
    }
  }
}
```

### VS Code (GitHub Copilot)

In `.vscode/settings.json`:

```json
{
  "github.copilot.chat.mcp.servers": {
    "deckrun-free": {
      "command": "python",
      "args": ["/path/to/deckrun_mcp_server.py"]
    }
  }
}
```

## Tools

| Tool | Description |
|------|-------------|
| `get_slide_format` | Fetches live Deckrun slide format spec. Call this first. |
| `generate_slide_deck` | Converts Deckrun Markdown to PDF. Returns `url`, `slides`, `warnings`. |

## Resources

| URI | Content |
|-----|---------|
| `deckrun-free://skill` | OpenClaw/ClawHub skill YAML for agent registries |
| `deckrun-free://openapi` | Live OpenAPI spec for `/free/generate` |

## How it works

```
Claude (in your IDE)
  → calls get_slide_format  → fetches live schema from agenticdecks.com
  → writes Deckrun Markdown in context window
  → calls generate_slide_deck(markdown)
      → POST https://free.agenticdecks.com/free/generate
      ← {"url": "...", "slides": 6, "warnings": [], "schema_version": "deckrun.v1"}
  ← "Your PDF is ready: https://..."
```

## Links

- [agenticdecks.com](https://agenticdecks.com) — product overview
- [free.agenticdecks.com](https://free.agenticdecks.com) — web UI
- [API spec](https://free.agenticdecks.com/.well-known/openapi.yaml)
- [Community / paid plans](https://github.com/agenticdecks/community)
