# Company Rules (`company.md`)

This is the shared rulebook every executive follows. It defines how your AI company
is organized, how work is reported, where files live, and how roles collaborate.
Read this before delegating any task. Adapt the specifics to your business — but keep
the structure.

---

## 1. Directory structure

```
your-business/
├── context/               ← YOUR primary source of truth
│   ├── diary/             ← daily notes, observations
│   ├── ideas/             ← concepts, future plans
│   └── references/        ← external material, research
├── projects/              ← cross-functional work (2+ roles involved)
│   └── _index.md          ← project registry
├── CMO/                   ← Marketing
│   ├── _index.md          ← output log + active tasks
│   ├── research/          ← drafts, investigation
│   └── outputs/           ← finished deliverables
├── CPO/  ... (same 3-part structure)
├── CFO/  ...
├── CSO/  ...
├── CDO/  ...
└── CAO/  ...
```

Every role folder has the same three parts: `_index.md` (a ledger), `research/`
(work in progress), `outputs/` (finished work).

---

## 2. Reporting rules

- Finish every task with **Point → Detail → Next action**.
- Separate **fact** from **opinion / inference** (see §7).
- Confirm important decisions and changes with the CEO (you) before acting.
- Anything that leaves the building — sending email, posting publicly, issuing an
  invoice — requires your explicit approval first.

---

## 3. Where outputs live

| Role | Drafts | Finished |
|------|--------|----------|
| CMO (Marketing) | `CMO/research/` | `CMO/outputs/` |
| CPO (Product)   | `CPO/research/` | `CPO/outputs/` |
| CFO (Finance)   | `CFO/research/` | `CFO/outputs/` |
| CSO (Sales)     | `CSO/research/` | `CSO/outputs/` |
| CDO (Tech/Ops)  | `CDO/research/` | `CDO/outputs/` |
| CAO (Analytics) | `CAO/research/` | `CAO/outputs/` |
| Cross-functional | `projects/<name>/` | same |

**File naming:** prefix with the date — `YYYY-MM-DD_name.md`. Drafts go in
`research/`, finished work in `outputs/`. Log every file you create or update in
that role's `_index.md`.

---

## 4. `_index.md` — the ledger

Each role's `_index.md` is its ledger. Rules:

- Add a row every time you create or update a deliverable.
- Don't delete finished tasks — change their status to "Done."
- Leave hand-off notes for other roles as needed.

Suggested table:

```markdown
| Date | File | Type | Summary | Status |
```

---

## 5. Spinning up a new executive (CDO's authority)

The CDO may create a new role **without asking** when ALL of these are true:

1. A task fits none of the existing roles.
2. The same kind of task will recur.
3. The role name and responsibilities can be defined clearly.
4. When in doubt, use an existing role — don't inflate the org chart.

**Procedure:** create `NewRole/_index.md`, `NewRole/prompt.md`, `NewRole/research/`,
`NewRole/outputs/`; update this file's directory + output tables; then tell the CEO
"I've added a new role."

**Naming:** use the C?O pattern (CHO = HR, CLO = Legal, CXO = Customer Experience).

---

## 6. Using `context/`

| Folder | What goes here |
|--------|----------------|
| `context/diary/` | daily notes, feelings, observations |
| `context/ideas/` | ideas, plans, future concepts |
| `context/references/` | reference material, book notes, external info |

Every executive reads `context/` before starting, to understand your intent and
background. Mark stale material with `[ARCHIVED]` at the top of the file.

---

## 7. Fact vs. opinion

**State as fact:** numbers (revenue, traffic, customers), events that happened,
terms of an agreement, cited sources.

**Mark as opinion / inference:** analysis ("this suggests..."), proposals
("it may be effective to..."), forecasts ("this is likely to...").

Example:
```
[FACT] YouTube subscribers grew by 1,200 last month.
[ANALYSIS] Likely driven by posting twice a week instead of once.
[PROPOSAL] Keep the cadence next month and measure the effect.
```

---

## 8. How work flows between roles

```
CEO (context/)
  ├─→ CSO   collects customer needs → feeds CMO & CPO
  ├─→ CMO   plans content & reach   → aligns with CPO
  ├─→ CPO   designs the offer       → checks pricing with CFO
  ├─→ CFO   runs finance/admin      → hands contracts to CSO
  ├─→ CAO   analyzes what worked    → feeds every role
  └─→ CDO   builds tools & prompts  → supports everyone
```

Rules for collaboration:
- If you use another role's output, note the source in your own `_index.md`.
- Any task with 2+ roles active goes into `projects/`.
- Hand off via files, not verbally — the next role should be able to pick it up cold.

---

## 9. Role responsibilities (at a glance)

- **CMO** — content, launches, social, landing pages, brand voice.
- **CPO** — products, courses, deliverables, structure, clarity.
- **CFO** — pricing, invoices, contracts, numbers, risk.
- **CSO** — customer dialogue, proposals, pipeline, objections.
- **CDO** — automation, prompts, tooling, spinning up new roles.
- **CAO** — analytics, hypotheses, "why did this work," experiment design.
