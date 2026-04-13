---
name: skill-builder
description: >
  Create, improve, or extend Claude Code skills. Use whenever the user says
  "create a skill for X", "make a skill that does Y", "build a new skill",
  "improve this skill", or asks to automate a recurring workflow as a skill.
  Triggers on: "/skill-builder", "create a skill", "make a skill", "build a
  new skill", "write a skill", "automate this workflow as a skill".
  Also triggers when the user does the same thing repeatedly and a skill would help.
compatibility: [file-read, file-write, agent-spawn]
---

# skill-builder

Create and improve Claude Code skills. A skill is a reusable workflow that encodes
how to handle a recurring task — so Claude does it the right way every time,
without being told twice.

## When to Use

- User wants to automate a recurring workflow as a callable skill
- User says "create a skill for X"
- User is doing the same task repeatedly and a skill would save re-explaining it
- An existing skill has gaps or could be sharper

## What a Skill Is

A skill is a `.md` file with YAML frontmatter that encodes:
1. **When to trigger** — description + triggers so Claude knows when to use it
2. **How to execute** — step-by-step instructions
3. **What output to produce** — clear success criteria

Skills live in `C:\Users\Charlie\.claude\skills\`.

## Workflow

### Phase 1 — Capture Intent

Before writing anything, understand:
1. What does the skill do? (one sentence)
2. When should it trigger? (what does the user say to invoke it?)
3. What's the output? (a file? a report? code? a decision?)
4. Are there any dependencies? (specific tools, files, environment)

Check if a similar skill already exists before creating a new one:
```
Search existing skills: glob for *.md in ~/.claude/skills/
Check for overlapping intent before creating a new skill
```

### Phase 2 — Draft the Skill

Create `~/.claude/skills/[skill-name].md` with this structure:

```markdown
---
name: [skill-name]
description: >
  [2-4 sentences: what it does, when it triggers, what it produces.
  Be specific. Include example trigger phrases. This is the primary
  triggering mechanism — spend time on it.]
compatibility: [list of required tools, e.g., file-read, agent-spawn]
---

# [Skill Title]

## What This Skill Does
[One paragraph. Be concrete — not "does code review" but
"reviews a Python codebase for security, quality, and bugs,
then fixes what it can automatically."]

## When to Use
[Bulleted list of trigger scenarios. Include both formal and
casual phrasings the user might use.]

## Pre-Conditions
[Any files that must exist, tools required, environment setup]

## Step-by-Step Workflow

### Step 1 — [Name]
[What to do first. Be specific about inputs and outputs.]

### Step 2 — [Name]
[What to do next.]

## Agent Patterns
[If spawning MiniMax agents: include the prompt template here]

## Important Rules
- [Rule 1 — and WHY it matters]
- [Rule 2]

## Output Format
[Exact format for the final output. Include templates
or examples if applicable.]

## Related Skills
[Other skills this composes with or relates to]
```

### Phase 3 — Evaluate and Improve

Ask yourself:
- Does the description trigger correctly? (would Claude know to use this?)
- Are the steps specific enough to execute without ambiguity?
- Is the output format clearly defined?
- Are there edge cases not covered?
- Are the WHY explanations included? (not just WHAT)

Common gaps:
- No exit condition — when does the skill stop?
- Too vague to act on — "review the code" vs "find and fix bare except:"
- Missing error handling — what if something fails mid-workflow?
- No output format — the skill produces something but it's not defined

## Pre-Built Patterns

### Pattern: MiniMax Execution Skill

For skills that do development work:

```markdown
## Step 1 — Pre-Read Files (Opus)
Read all relevant files ONCE. Pass content directly to agents.

## Step 2 — Spawn MiniMax Agents
Spawn parallel agents using minimax-dev-workflow.
One agent per file. Never two agents on the same file.

## Step 3 — Aggregate Results
Collect agent outputs, synthesize a final report.
```

### Pattern: Research + Execute Hybrid

```markdown
## Phase 1 — Parallel Research
Agent(R1, {prompt: "Research [aspect A]"})
Agent(R2, {prompt: "Research [aspect B]"})

// Phase 2 — Opus synthesizes findings

## Phase 3 — Parallel Execution
Agent(E1, {prompt: "Execute based on R1 findings"})
Agent(E2, {prompt: "Execute based on R2 findings"})
```

### Pattern: Skill That Creates Other Skills

```markdown
## Step 1 — Capture the workflow
Understand the recurring task. Ask: what does the user do repeatedly?

## Step 2 — Extract the steps
Convert the workflow into numbered, unambiguous steps.

## Step 3 — Write the skill file
Follow the template above. Include trigger phrases.

## Step 4 — Validate
Test the skill with 2-3 realistic prompts.
Fix gaps. Check the description triggers correctly.
```

## How to Write Good Triggers

The `description` field in frontmatter is the primary triggering mechanism.
Write triggers like this:

**Bad:** "Reviews code." (too vague, won't trigger reliably)
**Good:** "Reviews Python code for security issues, bugs, and code quality. Triggers when user says 'review my code', 'audit X', 'check Y for bugs', or '/code-review'." (specific, includes phrases)

Include:
- What the skill does
- Exact phrases a user might use
- Slash commands if applicable
- What NOT to confuse it with

## Writing Style

- Use imperative mood ("Read the file", not "Reading the file")
- Explain WHY, not just WHAT ("Prevents redundant file I/O" not just "Pre-read once")
- Be concrete, not abstract — "find and fix bare except:" not "improve error handling"
- Include edge cases — "If X fails, do Y, not Z"
- Name things well — function names, file paths, variable names all belong in the skill

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Too vague to act on | Concrete steps with specific inputs/outputs |
| No exit condition | Define when the skill is DONE |
| No output format | Show exact template or example |
| No error handling | "If X fails → do Y" for each step |
| Over-triggering | Narrow description with specific phrases |
| Under-triggering | Pushy description with adjacent use cases |

## Testing a New Skill

Once drafted, test it with 2–3 realistic prompts:
1. Spawn a MiniMax agent with the skill instructions
2. Run the agent on a real task
3. Check: did it do the right thing? Was the output clear?
4. Fix gaps in the skill based on what went wrong

## Improving Existing Skills

Same process, but start by reading the existing skill first:
1. Read the existing skill file
2. Identify the specific gap or improvement needed
3. Make the targeted fix
4. Re-test with the same prompts

## Skill File Location

Always save to: `C:\Users\Charlie\.claude\skills\[skill-name].md`

Use kebab-case for names: `code-review`, `bug-fix`, `test-generator`
One skill per file.
