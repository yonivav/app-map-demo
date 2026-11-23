# Keeping the map current automatically

Two parts; `install.sh --auto --map <folder> [--agent <name>]` in the app-map repo does both.

1. **The agent, while coding.** Append [../assets/agents-rule.md](../assets/agents-rule.md),
   with `MAP_DIR` replaced by the map's folder, to `AGENTS.md` and `CLAUDE.md` at the repo root
   (and `GEMINI.md` if there is one). Every agent then updates the map in the same change as
   the code.
2. **Every pull request.** Copy into `.github/workflows/`, with `MAP_DIR` set:
   - [../assets/app-map-check.yml](../assets/app-map-check.yml): builds and verifies the map,
     and writes `app-map changes` into the PR's summary.
   - [../assets/app-map-update.yml](../assets/app-map-update.yml): when `app-map changes
     --exit-code` says the map is behind, an AI agent updates it and commits it to the PR's
     branch. `AGENT` picks Claude Code, Codex, Gemini CLI, Cursor or Copilot; the file lists
     each one's repository secret.

Screenshots stay manual: they need a simulator.
