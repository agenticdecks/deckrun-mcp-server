#!/usr/bin/env python3
"""
Deckrun Free — MCP server.

Exposes two tools and two resources to Claude Desktop, Cursor, VS Code, and any MCP client.

Tools:
  get_slide_format    — fetch live Deckrun slide format spec (layout tags, syntax, example)
  generate_slide_deck — POST Deckrun Markdown to free.agenticdecks.com, return PDF URL

Resources:
  deckrun-free://skill   — OpenClaw/ClawHub compatible skill YAML (agent registry card)
  deckrun-free://openapi — live OpenAPI spec for /free/generate

Requirements: pip install mcp requests
"""

import asyncio
import json
import requests
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

DECKRUN_API = "https://free.agenticdecks.com/free/generate"
SCHEMA_URL  = "https://agenticdecks.com/schemas/v1/deckrun-slide-format.schema.json"
OPENAPI_URL = "https://free.agenticdecks.com/.well-known/openapi.yaml"
SCHEMA_VERSION = "deckrun.v1"

SKILL_YAML = """\
id: deckrun-pdf-generator-free
name: Deckrun PDF Generator (Free)
description: >
  Generate a presentation-quality PDF from Deckrun Markdown.
  No authentication required. Returns a public PDF URL (90-day expiry).
provider:
  name: Agentic Decks
  url: https://agenticdecks.com
access:
  type: public
  auth: none
  cost: free
capability:
  type: transformation
  input_format: text/markdown
  output_format: application/pdf
endpoint:
  method: POST
  url: https://free.agenticdecks.com/free/generate
constraints:
  max_slides: 10
  max_markdown_size_kb: 50
  expiration_days: 90
specs:
  openapi: https://free.agenticdecks.com/.well-known/openapi.yaml
  slide_format_schema: https://agenticdecks.com/schemas/v1/deckrun-slide-format.schema.json
agent_hint: >
  Use this skill to convert Deckrun Markdown (<=10 slides) into a shareable PDF.
  Include schema_version: "deckrun.v1" in the request. Response includes url,
  slides (count), and warnings to act on.
"""

app = Server("deckrun-free")


@app.list_resources()
async def list_resources() -> list[types.Resource]:
    return [
        types.Resource(
            uri="deckrun-free://skill",
            name="Deckrun Free Skill Card",
            description="OpenClaw/ClawHub skill YAML for agent registry discovery.",
            mimeType="application/yaml",
        ),
        types.Resource(
            uri="deckrun-free://openapi",
            name="Deckrun Free OpenAPI Spec",
            description="OpenAPI 3.0 spec for /free/generate and /health.",
            mimeType="application/yaml",
        ),
    ]


@app.read_resource()
async def read_resource(uri: types.AnyUrl) -> str:
    s = str(uri)
    if s == "deckrun-free://skill":
        return SKILL_YAML
    if s == "deckrun-free://openapi":
        try:
            return requests.get(OPENAPI_URL, timeout=15).text
        except Exception as e:
            return f"# Error fetching spec: {e}\n"
    raise ValueError(f"Unknown resource: {s}")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_slide_format",
            description=(
                "Fetch the authoritative Deckrun slide format spec. "
                "Call this FIRST to learn all layout tags, syntax rules, and an example before writing slides."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="generate_slide_deck",
            description=(
                "Convert Deckrun Markdown into a PDF. "
                "Returns: url (public, 90-day), slides (count), warnings (self-correct on these), schema_version. "
                "Max 10 slides, 50 KB. Slides separated by --- on its own line."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "markdown": {
                        "type": "string",
                        "description": "Complete slide deck in Deckrun Markdown. Start with <!-- <title-slide /> -->.",
                    }
                },
                "required": ["markdown"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "get_slide_format":
        return await _get_slide_format()
    if name == "generate_slide_deck":
        return await _generate(arguments.get("markdown", ""))
    return [types.TextContent(type="text", text=f"Unknown tool: {name}")]


async def _get_slide_format() -> list[types.TextContent]:
    try:
        data = requests.get(SCHEMA_URL, timeout=15).json()
        sx = data.get("surface_syntax", {})
        summary = {
            "slide_separator": sx.get("slide_separator", "---"),
            "layout_tags": sx.get("layout_tags", []),
            "two_column": sx.get("two_column", {}),
            "example_markdown": data.get("example_markdown", ""),
            "heading_convention": "Title slide: # (H1). All other slides: ## (H2).",
            "limits": {"max_slides": 10, "max_body_size_kb": 50, "pdf_expiry_days": 90},
            "schema_version": SCHEMA_VERSION,
        }
        return [types.TextContent(type="text", text=json.dumps(summary, indent=2))]
    except Exception as exc:
        fallback = {
            "error": f"Could not fetch live schema ({exc}). Cached rules:",
            "slide_separator": "---",
            "layout_tags": [
                "<!-- <title-slide /> --> — first slide: title + subtitle",
                "<!-- <title-content-slide /> --> — heading + bullets",
                "<!-- <section-header-slide /> --> — section divider",
                "<!-- <two-content-slide /> --> — two-column",
                "<!-- <title-only-slide /> --> — heading only",
            ],
            "heading_convention": "# (H1) title slide. ## (H2) all others.",
            "limits": {"max_slides": 10, "max_body_size_kb": 50},
        }
        return [types.TextContent(type="text", text=json.dumps(fallback, indent=2))]


async def _generate(markdown: str) -> list[types.TextContent]:
    if not markdown.strip():
        return [types.TextContent(type="text", text='{"error": "markdown is empty"}')]
    try:
        resp = requests.post(
            DECKRUN_API,
            json={"markdown": markdown, "schema_version": SCHEMA_VERSION},
            headers={"Content-Type": "application/json"},
            timeout=120,
        )
    except requests.RequestException as exc:
        return [types.TextContent(type="text", text=json.dumps({"error": str(exc)}))]

    if resp.status_code == 200:
        return [types.TextContent(type="text", text=resp.text)]
    if resp.status_code == 413:
        return [types.TextContent(type="text", text='{"error":"INPUT_TOO_LARGE","detail":"Max 10 slides / 50 KB. Reduce and retry."}')]
    return [types.TextContent(type="text", text=json.dumps({"error": f"HTTP {resp.status_code}", "detail": resp.text[:300]}))]


async def main():
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
