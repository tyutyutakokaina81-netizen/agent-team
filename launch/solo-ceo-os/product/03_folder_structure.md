# The Folder & Memory Structure

This is what gives each officer its own memory. Recreate it in your workspace
(local folders, a Notion space, or a Claude/ChatGPT project).

```
my-company/
├── company_operating_system.md   ← the rulebook (file 01)
│
├── context/                      ← YOUR primary source of truth
│   ├── diary/                    ← daily notes & observations
│   ├── ideas/                    ← concepts, future plans
│   └── references/               ← external material, research
│
├── CMO/   (Marketing)
│   ├── _log.md                   ← work log + active tasks  ← THE MEMORY
│   ├── prompt.md                 ← the role prompt (file 02)
│   ├── research/                 ← drafts, investigations
│   └── outputs/                  ← finished deliverables
│
├── CPO/   (Product)        ├── _log.md ├── prompt.md ├── research/ ├── outputs/
├── CFO/   (Finance)        ├── _log.md ├── prompt.md ├── research/ ├── outputs/
├── CSO/   (Sales)          ├── _log.md ├── prompt.md ├── research/ ├── outputs/
├── CDO/   (Tech)           ├── _log.md ├── prompt.md ├── research/ ├── outputs/
├── CAO/   (Analytics)      ├── _log.md ├── prompt.md ├── research/ ├── outputs/
│
└── projects/                     ← cross-officer work
    └── _index.md                 ← list of all projects
```

## The two rules that make memory work

1. **Drafts go in `research/`. Finished work goes in `outputs/`.**
   Name every file with a date prefix: `YYYY-MM-DD_name.md`.

2. **Every `_log.md` is a ledger.** After any task, the officer appends a row:

   ```
   | Date | File | Type | Summary | Status |
   ```

   Tasks aren't deleted when done — their status changes to "done." The owner
   and every officer can read the whole history at a glance.

## Why this matters

Without `_log.md`, your AI starts from zero every session. With it, each
officer reads its own history first and builds on it. That single habit is what
makes the system compound over months instead of resetting every morning.
