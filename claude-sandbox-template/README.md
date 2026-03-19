# Claude Code Sandbox — Repeatable Workflow

A drop-in `.devcontainer/` setup for running `claude --dangerously-skip-permissions` safely in an isolated container. Works with VS Code Dev Containers + OrbStack (or Docker Desktop).

## Prerequisites

- **VS Code** with the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
- **OrbStack** (recommended) or **Docker Desktop** as the container runtime
- **Claude Code subscription** (Pro, Max, or Team)

## Setup (one-time)

1. **Copy the `.devcontainer/` folder** into the root of your git repository:

   ```bash
   cp -r /path/to/claude-sandbox-template/.devcontainer /path/to/your-repo/
   ```

2. **Open your repo in VS Code.** You'll see a prompt: _"Reopen in Container"_ — click it. Or use the command palette: `Dev Containers: Reopen in Container`.

3. **First launch takes a few minutes** (building the image, installing Claude Code, configuring the firewall). Subsequent launches reuse the cached image and are fast.

4. **Authenticate Claude Code** (first time per container volume):

   ```bash
   claude login
   ```

## The Repeatable Workflow

Every time you have a goal or objective, follow this loop:

### Step 1: Checkpoint

```bash
git add -A && git commit -m "checkpoint: before claude run"
```

The setup script does this automatically on container creation, but it's good practice to do it manually before each new goal too.

### Step 2: Give Claude your goal

```bash
# Interactive mode (you can steer it as it works)
claude --dangerously-skip-permissions

# Or pass a one-shot goal with -p
claude --dangerously-skip-permissions -p "Your specific goal here"
```

**Tips for writing good goals:**

- Be specific: _"Add input validation to all API endpoints in src/routes/"_ not _"improve the code"_
- Include constraints: _"Use Zod for validation, don't change the existing test structure"_
- Mention what to test: _"Run the existing test suite after changes and fix any failures"_

### Step 3: Review

```bash
git diff                  # see what changed
git log --oneline         # see commit history
# run your test suite
npm test                  # or pytest, cargo test, etc.
```

### Step 4: Accept or rollback

```bash
# Happy with the result:
git add -A && git commit -m "feat: description of what claude did"

# Not happy — nuke everything back to checkpoint:
git reset --hard HEAD
# or to a specific checkpoint:
git stash list
git stash apply stash@{0}
```

### Step 5: Repeat

Go back to Step 1 with your next goal.

## Customization

### Adding more whitelisted domains

Edit `.devcontainer/init-firewall.sh` and add domains to the `ALLOWED_DOMAINS` array. For example, if your project needs access to a private npm registry:

```bash
ALLOWED_DOMAINS=(
  # ... existing domains ...
  "your-registry.example.com"
)
```

### Adding project-specific tools

Edit `.devcontainer/Dockerfile` to install additional tools:

```dockerfile
# Example: add Python for a mixed project
RUN apt-get update && apt-get install -y python3 python3-pip
```

### Adding a CLAUDE.md for project context

Create a `CLAUDE.md` in your repo root. Claude Code reads this automatically to understand your project:

```markdown
# Project Context

This is a Node.js REST API using Express + TypeScript.
Tests are in `__tests__/` and use Jest.
Always run `npm run lint && npm test` after making changes.
```

### Disabling specific tools (belt-and-suspenders)

Even inside the container, you can restrict what Claude Code can do. Create `.claude/settings.local.json`:

```json
{
  "disallowedTools": ["rm", "mv"]
}
```

## Security Model

| Layer | What it does |
|-------|-------------|
| **Container isolation** | Claude can't touch your host filesystem, SSH keys, browser cookies, or other projects |
| **Network firewall** | Outbound traffic blocked except Anthropic API, GitHub, npm — prevents data exfiltration to arbitrary servers |
| **Git checkpoints** | One command to undo everything Claude did |
| **Non-root user** | Claude runs as `node` user, not root |
| **Disposable** | Rebuild the container from scratch any time: `Dev Containers: Rebuild Container` |

### What this does NOT protect against

- Exfiltration via whitelisted channels (e.g., pushing secrets to a GitHub repo Claude has access to)
- Malicious content in untrusted repos you open in the container
- Claude modifying `.env` files or other secrets _within_ the mounted workspace

**Rule of thumb:** Only open trusted repositories in this container.

## Troubleshooting

**Firewall fails to initialize:**
Your container runtime may need `NET_ADMIN` capability. Add to `devcontainer.json`:
```json
"runArgs": ["--cap-add=NET_ADMIN"]
```

**Claude Code not found after rebuild:**
The npm install of Claude Code is now deprecated. If you see warnings, switch to:
```bash
curl -fsSL https://claude.ai/install.sh | sh
```
and update the Dockerfile accordingly.

**OrbStack vs Docker Desktop:**
Both work. OrbStack is lighter and faster on macOS, especially Apple Silicon. The devcontainer spec is runtime-agnostic.
