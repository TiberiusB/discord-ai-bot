# Agent tools and MCP servers

Part of the [design documentation](README.md) for the Tramice721 Discord bot. Section numbers are kept from the original single-file specification so that `§n` references elsewhere in the docs stay meaningful.

## 6. Agent tools & MCP servers



### 6.1 LangChain tools (agent-facing)


| Tool name               | Service             | Milestone |
| ----------------------- | ------------------- | --------- |
| `search_knowledge`      | KnowledgeService    | M3        |
| `get_trammer_profile`   | IdentityService     | M4        |
| `update_volio`          | IdentityService     | M4        |
| `find_matches`          | MatchmakingService  | M4        |
| `list_echoes`           | MatchmakingService  | M4        |
| `propose_event`         | CoordinationService | M4        |
| `list_mondo`            | EcosystemService    | M4        |
| `get_entity`            | EcosystemService    | M4        |
| `get_game_week`         | GameService         | M5        |
| `place_hops`            | GameService         | M5        |
| `publish_mission`       | GameService         | M5        |
| `summarize_channel`     | GovernanceService   | M4        |
| `create_vote`           | GovernanceService   | M5        |
| `get_server_overview`   | MCP discord_helper  | M4        |
| `get_guild_metadata`    | MCP discord_helper  | P15       |
| `fetch_channel_history` | MCP discord_helper  | M4        |


Each tool schema includes: `name`, `description` (French-friendly), typed
`parameters`, and `requires_confirmation: bool` where human approval is needed
(`place_hops`, `propose_event`, `create_vote`, `cast_ballot`).

### 6.2 MCP: `discord_helper` `[platform]` `[ecosystem-mapping]`

```python
@mcp.tool()
def get_server_overview(guild_id: str) -> dict:
    """Channel list, member count, recent activity stats."""

@mcp.tool()
def get_guild_metadata() -> dict:
    """Guild name, channel list, roles summary (from live Discord + config allowlists)."""

@mcp.tool()
def fetch_channel_history(channel_id: str, limit: int = 50,
                          since_iso: str | None = None) -> list[dict]:
    """Recent messages from SQLite log (not live Discord API unless needed)."""
```

Transport: **stdio**. Launch via `mcp_servers/mcp_config.py`.

### 6.3 MCP: `rag_server` `[knowledge]`

```python
@mcp.tool()
def semantic_search_docs(query: str, collection: str = "docs", k: int = 5) -> list[dict]:
    """Vector search over Chroma. collection: docs | web | history | all (docs+web)."""
```



### 6.4 MCP: fetch (optional, live) vs curated web RAG `[knowledge]`

**Curated web RAG (implemented):** admins register seed URLs via `/web-source add`; the bot crawls and embeds into Chroma `web`. This is the primary path for LaTramice.net and other trusted sites (KNW-3).

**Optional live fetch (not enabled by default):** read-only `uvx mcp-server-fetch` when `features.web_fetch: true`. Gated by `fetch_allowlist` if `rag.web.require_allowlist: true`. Separate from curated ingest — do not enable both for the same use case unless intentional.
