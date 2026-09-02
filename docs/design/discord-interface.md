# Discord interface

Part of the [design documentation](README.md) for the Tramice721 Discord bot. Section numbers are kept from the original single-file specification so that `§n` references elsewhere in the docs stay meaningful.

## 7. Discord interface `[platform]` `[administration]`



### 7.1 Intents & permissions


| Discord intent    | Required |
| ----------------- | -------- |
| `message_content` | Yes      |
| `members`         | Yes      |
| `guilds`          | Yes      |



| Permission               | Use             |
| ------------------------ | --------------- |
| Send Messages            | replies         |
| Read Message History     | context         |
| Use Slash Commands       | slash cmds      |
| Send Messages in Threads | optional        |
| Mention @everyone        | gated (`ADM-4`) |




### 7.2 Triggers


| Trigger | Pattern                 | Behavior                     |
| ------- | ----------------------- | ---------------------------- |
| Prefix  | `!ai <message>`         | strip prefix, route to agent |
| Mention | `@Tramice721 <message>` | strip mention                |
| Slash   | see §7.3                | structured commands          |


Config key: `triggers.prefix` default `!ai`.

### 7.3 Slash commands


| Command        | Service        | Access | Description                                  |
| -------------- | -------------- | ------ | -------------------------------------------- |
| `/ask`         | agent          | all    | Ask Tramice721 (optional `question` param)   |
| `/summarize`   | governance     | all    | Summarize current channel (optional `hours`) |
| `/volio`       | identity       | all    | List or add a volio entry                    |
| `/mondo`       | ecosystem      | all    | Mondo views: `perso`, `cosmo`, `stats`, `knowledge`, `entity` |
| `/echoes`      | matchmaking    | all    | List unread Échos                            |
| `/mission`     | game           | all    | Publish or view Missions                     |
| `/support`     | game           | all    | Place, withdraw, move, or list HOP influence (confirm) |
| `/vote`        | governance     | all    | View/open votes                              |
| `/event`       | coordination   | all    | Propose or list events                       |
| `/signal`      | governance     | all    | File graduated report                        |
| `/forgetme`    | memory         | all    | Delete user's stored data (retains activity trace) |
| `/norms`       | governance     | all    | Show social norms                            |
| `/my-model`    | administration | all    | Choose personal Ollama model (dropdown)      |
| `/mode`        | persona        | all    | Set conversation mode / harness for channel |
| `/todo`        | coordination   | all    | Shared todo list for the channel             |
| `/identity`    | identity       | all    | List known names or link identities          |
| `/thread`      | platform       | all    | Create a channel thread                      |
| `/poll`        | platform       | all    | Publish a Discord poll                       |
| `/son`         | platform       | all    | List soundboard sounds                       |
| `/reindex`     | administration | admin  | Rebuild RAG index (`scope`: docs, web, or all) |
| `/web-source`  | administration | admin  | **Group:** `add` / `list` / `remove` curated web sources |
| `/model`       | administration | admin  | Swap community default Ollama model          |
| `/set-norm`    | governance     | admin  | Update a social norm                         |
| `/game-week`   | game           | admin  | View or edit weekly game parameters          |
| `/health`      | administration | admin  | Runtime + Discord health snapshot            |
| `/say`         | platform       | admin  | Send TTS message (`features.tts`)            |


**Confirmation pattern:** for mutating game/governance actions, respond with
Discord embed + `✅ Confirmer` / `❌ Annuler` buttons (`discord.ui.View`).

### 7.4 Surface-specific behavior


| Aspect           | Salon                                    | DM                                        |
| ---------------- | ---------------------------------------- | ----------------------------------------- |
| Opening          | Respond to trigger only                  | Well-being check if no precise request    |
| Emoji use        | Encouraged on progress                   | Moderate                                  |
| Mediation        | Only when asked or `/summarize` conflict | Available on "Résolvons un problème" mode |
| Logging          | per channel policy                       | always private tier                       |
| Profile exposure | public/network fields only               | full volio + confidences                  |
