# Solopreneur Operating System — Notion Template Kit

A connected workspace for running a one-person business. Seven linked pages and
databases cover clients, projects, money, marketing, goals, and reusable templates.
This document is the complete specification: every page, every property, every view,
plain-English formula logic, example rows, a 15-minute build guide, and CSV headers
you can import directly into Notion.

> **How to use this file.** Read the build guide once, then create the databases in
> order. Where a column is a Notion *formula* or *rollup*, the exact logic is written
> in words so you can type it yourself — no copy-paste magic required.

---

## 0. Map of the system

```
🏠 Dashboard (page)
├── 👥 Clients / CRM            (database)
├── ✅ Projects & Tasks         (database)  ── relates to → Clients
├── 💰 Income & Expenses        (database)  ── relates to → Clients, Projects
├── 📣 Content & Marketing      (database)  ── relates to → Projects
├── 🎯 Goals & Weekly Review    (database + template)
└── 🗂️ Templates Library        (page with 3 reusable docs)
```

Relations to set up (do these after all databases exist):

| From | Property | To | Why |
|---|---|---|---|
| Projects & Tasks | `Client` | Clients / CRM | See all work per client |
| Income & Expenses | `Client` | Clients / CRM | Revenue per client |
| Income & Expenses | `Project` | Projects & Tasks | Profitability per project |
| Content & Marketing | `Related Project` | Projects & Tasks | Link promo to delivery |

---

## 1. 🏠 Dashboard

**Purpose.** One screen you open every morning. It does not store data; it surfaces
the most relevant slices of the other databases through *linked views*, plus a few
manual notes.

**Build as.** A normal Notion page (not a database). Add blocks in this order:

1. **Heading:** "This week" — a callout block for your single focus sentence.
2. **Linked view of Projects & Tasks** → filter `Status` is `In progress` OR `Due` is within the next 7 days; sort by `Due` ascending. View type: Table or Board.
3. **Linked view of Clients / CRM** → filter `Status` is `Active`; sort by `Next touch` ascending.
4. **Linked view of Income & Expenses** → filter `Date` is this month; show `Type`, `Amount`, `Category`. Add a board grouped by `Type` to eyeball in vs. out.
5. **Linked view of Content & Marketing** → filter `Status` is not `Published`; sort by `Publish date` ascending.
6. **Toggle: "Links"** — bookmarks to Goals & Weekly Review and the Templates Library.

> Linked views always reflect live data, so the dashboard never goes stale.

---

## 2. 👥 Clients / CRM

**Purpose.** Track every person or company you work with, where they are in your
pipeline, and when to follow up. Replaces a messy spreadsheet of contacts.

**Properties.**

| Property | Type | Notes |
|---|---|---|
| `Name` | Title | Company or person label |
| `Status` | Select | `Lead`, `Contacted`, `Proposal sent`, `Active`, `Paused`, `Closed-won`, `Closed-lost` |
| `Contact` | Text | Email or handle |
| `Source` | Select | `Referral`, `Inbound`, `Outbound`, `Marketplace`, `Repeat` |
| `Tier` | Select | `A`, `B`, `C` — your priority sense, not a judgment of the person |
| `Next touch` | Date | When to follow up next |
| `Notes` | Text | Free context |
| `Projects` | Relation → Projects & Tasks | Auto-fills from the project side |
| `Revenue (rollup)` | Rollup | From `Income & Expenses` relation: **Sum** of `Amount` where type is income. In words: roll up the linked income rows and add their amounts. |
| `Created` | Created time | Auto |

**Recommended views.**

- **Pipeline (Board):** group by `Status`. Drag cards as deals move.
- **Follow-ups (Table):** filter `Next touch` is on or before today, sort ascending. Your daily call list.
- **Active clients (Table):** filter `Status` is `Active`.

**Example rows.**

| Name | Status | Source | Tier | Next touch | Notes |
|---|---|---|---|---|---|
| Northwind Studio | Active | Referral | A | 2026-07-02 | Monthly retainer, prefers email |
| Maple & Co. | Proposal sent | Inbound | B | 2026-06-26 | Sent proposal v2, awaiting reply |
| J. Rivera (freelance) | Lead | Marketplace | C | 2026-06-25 | Found via portfolio, small one-off |

---

## 3. ✅ Projects & Tasks

**Purpose.** Hold both projects and the tasks under them in one database, so you see
the deadline picture without juggling two tools. Use a `Type` field to separate the
two levels, and a self-relation for parent/child if you want sub-tasks.

**Properties.**

| Property | Type | Notes |
|---|---|---|
| `Name` | Title | Project or task name |
| `Type` | Select | `Project`, `Task` |
| `Status` | Status | `Not started`, `In progress`, `Blocked`, `Review`, `Done` |
| `Client` | Relation → Clients / CRM | Who it's for |
| `Priority` | Select | `High`, `Medium`, `Low` |
| `Due` | Date | Deadline |
| `Estimate (hrs)` | Number | Rough time guess |
| `Parent item` | Relation (self) | Optional: link a task to its project |
| `Progress` | Formula | See logic below |
| `Days left` | Formula | See logic below |
| `Done` | Checkbox | Quick complete toggle (optional, mirrors `Status` = Done) |

**Formula logic in words.**

- `Days left`: number of days from today to `Due`. In words: *subtract today's date from the `Due` date and express it in days.* If empty, show nothing. (Notion: `dateBetween(prop("Due"), now(), "days")`.)
- `Progress`: a simple text flag. In words: *if `Status` is Done show "✅"; else if `Days left` is negative show "⚠️ overdue"; else if `Days left` is 2 or fewer show "⏰ soon"; else show "—".*

**Recommended views.**

- **By status (Board):** group by `Status`. Default working view.
- **By deadline (Table):** filter `Status` is not `Done`; sort `Due` ascending. Add `Days left` and `Progress`.
- **Calendar:** by `Due`, to see the month at a glance.
- **Projects only (Table):** filter `Type` is `Project`.

**Example rows.**

| Name | Type | Status | Client | Priority | Due | Estimate (hrs) |
|---|---|---|---|---|---|---|
| Website refresh | Project | In progress | Northwind Studio | High | 2026-07-10 | 24 |
| └ Draft homepage copy | Task | In progress | Northwind Studio | High | 2026-06-27 | 4 |
| Logo variations | Task | Not started | Maple & Co. | Medium | 2026-07-01 | 3 |

---

## 4. 💰 Income & Expenses

**Purpose.** A single ledger for money in and out. One row per transaction. Monthly
rollups let you see whether the month was net positive without a spreadsheet.

**Properties.**

| Property | Type | Notes |
|---|---|---|
| `Description` | Title | What it was |
| `Type` | Select | `Income`, `Expense` |
| `Amount` | Number | Always a positive number; `Type` carries the sign |
| `Date` | Date | Transaction date |
| `Category` | Select | Income: `Project`, `Retainer`, `Product`. Expense: `Software`, `Contractor`, `Fees`, `Equipment`, `Other` |
| `Client` | Relation → Clients / CRM | Optional |
| `Project` | Relation → Projects & Tasks | Optional |
| `Month` | Formula | Year-month text for grouping (see below) |
| `Signed amount` | Formula | `Amount` for income, negative `Amount` for expense (see below) |
| `Paid` | Checkbox | Cleared / received |

**Formula logic in words.**

- `Month`: *take the `Date`, format it as "YYYY-MM"* so all transactions in the same month share a label. (Notion: `formatDate(prop("Date"), "YYYY-MM")`.)
- `Signed amount`: *if `Type` is Income, use `Amount` as-is; if `Type` is Expense, use `Amount` multiplied by −1.* This lets a single column sum to a true net figure.

**Monthly rollup (how to read the month).**

Create a **Table view grouped by `Month`**. Notion shows per-group subtotals at the
bottom of a column: set `Signed amount` to **Sum**. Each month's group footer is your
net profit/loss for that month. For separate in/out totals, add two more views:
filter `Type` is `Income` (sum `Amount` = gross income) and `Type` is `Expense`
(sum `Amount` = total costs).

**Recommended views.**

- **Ledger (Table):** sort `Date` descending — the running log.
- **Monthly (Table):** group by `Month`, sum `Signed amount`.
- **This month (Board):** filter `Date` is this month, group by `Type`.

**Example rows.**

| Description | Type | Amount | Date | Category | Paid |
|---|---|---|---|---|---|
| Website refresh — deposit | Income | 1200 | 2026-06-15 | Project | ✓ |
| Design software subscription | Expense | 22 | 2026-06-01 | Software | ✓ |
| Retainer — Northwind Studio | Income | 800 | 2026-06-05 | Retainer | ✓ |

---

## 5. 📣 Content & Marketing

**Purpose.** Plan and track what you publish to attract clients — posts, newsletters,
portfolio pieces. Stops the "what do I post this week" stall.

**Properties.**

| Property | Type | Notes |
|---|---|---|
| `Title` | Title | Working headline |
| `Channel` | Select | `Newsletter`, `Blog`, `Social`, `Portfolio`, `Other` |
| `Status` | Status | `Idea`, `Drafting`, `Scheduled`, `Published` |
| `Publish date` | Date | Target or actual |
| `Format` | Select | `Post`, `Thread`, `Article`, `Video`, `Image` |
| `Goal` | Select | `Awareness`, `Leads`, `Authority`, `Nurture` |
| `Related Project` | Relation → Projects & Tasks | Tie promo to delivery |
| `Link` | URL | Where it lives once live |
| `Notes` | Text | Hook, angle, CTA |

**Recommended views.**

- **Calendar:** by `Publish date` — the editorial calendar.
- **Pipeline (Board):** group by `Status`.
- **By channel (Table):** group by `Channel`.

**Example rows.**

| Title | Channel | Status | Publish date | Format | Goal |
|---|---|---|---|---|---|
| 3 questions I ask before any project | Social | Scheduled | 2026-06-25 | Post | Authority |
| Monthly recap + one lesson | Newsletter | Drafting | 2026-06-30 | Article | Nurture |
| Before/after: website refresh | Portfolio | Idea | 2026-07-12 | Image | Leads |

---

## 6. 🎯 Goals & Weekly Review

**Purpose.** Keep quarterly goals visible and run a short, repeatable weekly review so
the system stays honest. Two parts: a small **Goals** database and a **Weekly Review**
page template.

### 6a. Goals (database)

| Property | Type | Notes |
|---|---|---|
| `Goal` | Title | The outcome |
| `Horizon` | Select | `Quarter`, `Month`, `Year` |
| `Metric` | Text | How you'll know (e.g., "3 new active clients") |
| `Target` | Number | The number to hit |
| `Current` | Number | Update manually during review |
| `Progress` | Formula | *Divide `Current` by `Target`; if `Target` is 0 show 0; format as a percent.* (Notion: `prop("Current") / prop("Target")`, set the property to show as a bar or percent.) |
| `Status` | Select | `On track`, `At risk`, `Done`, `Dropped` |
| `Review date` | Date | When last reviewed |

**Example rows.**

| Goal | Horizon | Metric | Target | Current | Status |
|---|---|---|---|---|---|
| Reach 3 active retainer clients | Quarter | Active retainers | 3 | 1 | On track |
| Publish weekly for the quarter | Quarter | Posts published | 13 | 4 | On track |
| Net profit ≥ baseline each month | Month | Net positive months | 3 | 2 | At risk |

### 6b. Weekly Review (page template)

Make this a **template button** or a database template you duplicate each Friday.
Fixed structure:

```
## Week of ____ to ____

### 1. Numbers (60 seconds)
- Net this week (from Income & Expenses, This-month view): ____
- Tasks completed: ____   |  Tasks slipped: ____
- New leads added: ____   |  Content published: ____

### 2. What worked / what didn't
- Worked: 
- Didn't: 

### 3. Goals check
- Open Goals DB. Update `Current` and `Status` on each goal.

### 4. Next week's ONE focus
- The single sentence that goes in the Dashboard "This week" callout: 

### 5. Follow-ups to schedule
- Open Clients → set `Next touch` on anyone overdue.
```

---

## 7. 🗂️ Templates Library

**Purpose.** Reusable text you'd otherwise rewrite. Keep as three sub-pages (or
database entries) you duplicate when needed. All placeholders are in `[brackets]`.

### 7a. Proposal (short form)

```
Subject: Proposal — [project name]

Hi [client first name],

Thanks for the conversation about [problem in their words]. Here's how I'd approach it.

Scope
- [Deliverable 1]
- [Deliverable 2]
- [Deliverable 3]

Out of scope (so we're aligned)
- [Anything explicitly excluded]

Timeline
- Start: [date]  |  Draft/review: [date]  |  Final: [date]

Investment
- [Amount] — [payment terms, e.g., 50% to start, 50% on delivery]

How we'd work
- [Cadence: e.g., one update per week, one round of revisions included]

If this looks right, reply "approved" and I'll send the start details.

[Your name]
```

### 7b. Invoice note (cover text, not a legal invoice)

```
Invoice [number] — [your name / business name]
Bill to: [client]
Date: [date]   |   Due: [date / terms]

Description                         Amount
[Deliverable or milestone]          [amount]
[Deliverable or milestone]          [amount]
-----------------------------------------
Total due                           [amount]

Payment: [method / details]
Reference: [project name]

Note: This is a payment summary. Check local requirements for formal invoicing
and tax handling that apply to you.
```

### 7c. Meeting notes

```
## [Client / topic] — [date]

Attendees: 
Goal of this call: 

### Notes
- 

### Decisions
- 

### Action items
- [ ] [Owner] — [action] — due [date]   (also add to Projects & Tasks)

### Follow-up
- Next touch: [date]  (update in Clients / CRM)
```

---

## 8. How to build this in Notion in 15 minutes

> Times are rough. Do it in order — relations need the databases to exist first.

1. **(1 min) Create a parent page** named "Solopreneur OS". Everything lives inside it.
2. **(2 min) Clients / CRM.** Inside the parent, type `/table` → **Table — Full page**. Rename it. Add the properties from §2 (Select options can be added as you type the first value). Paste the 3 example rows.
3. **(3 min) Projects & Tasks.** New full-page database (§3). Add properties. For `Client`, choose **Relation** and point it at Clients / CRM. Add the two formulas (`Days left`, `Progress`) using the plain-English logic — Notion shows a formula editor; type the expression noted in parentheses.
4. **(3 min) Income & Expenses.** New full-page database (§4). Add properties, the `Client` and `Project` relations, and the `Month` + `Signed amount` formulas.
5. **(2 min) Content & Marketing.** New full-page database (§5). Add the `Related Project` relation.
6. **(2 min) Goals.** New database (§6a) with the `Progress` formula. Then make the **Weekly Review** template (§6b): create a database template or a `/template button` containing the fixed structure.
7. **(1 min) Templates Library.** New page (§7) with three toggles or sub-pages holding the proposal, invoice note, and meeting notes text.
8. **(1 min) Dashboard.** New page at the top of the parent (§1). Add **linked views** (`/linked view of database`) of each database and apply the filters listed.
9. **Add the rollups last.** On Clients / CRM, add `Revenue (rollup)` once the Income relation exists. Set view subtotals (Sum) where noted.

When you're done, drag the Dashboard to the top of the sidebar and pin the parent page.

---

## 9. CSV-importable headers

Notion can create a database from a CSV (`Import` → `CSV`). Use these headers, then
add relations/formulas/rollups afterward (those don't import from CSV). Each block
below is one file.

**clients.csv**
```
Name,Status,Contact,Source,Tier,Next touch,Notes
Northwind Studio,Active,hello@example.com,Referral,A,2026-07-02,Monthly retainer
Maple & Co.,Proposal sent,team@example.com,Inbound,B,2026-06-26,Awaiting reply
J. Rivera,Lead,jr@example.com,Marketplace,C,2026-06-25,Small one-off
```

**projects_tasks.csv**
```
Name,Type,Status,Priority,Due,Estimate (hrs)
Website refresh,Project,In progress,High,2026-07-10,24
Draft homepage copy,Task,In progress,High,2026-06-27,4
Logo variations,Task,Not started,Medium,2026-07-01,3
```

**income_expenses.csv**
```
Description,Type,Amount,Date,Category,Paid
Website refresh — deposit,Income,1200,2026-06-15,Project,Yes
Design software subscription,Expense,22,2026-06-01,Software,Yes
Retainer — Northwind Studio,Income,800,2026-06-05,Retainer,Yes
```

**content_marketing.csv**
```
Title,Channel,Status,Publish date,Format,Goal
3 questions I ask before any project,Social,Scheduled,2026-06-25,Post,Authority
Monthly recap + one lesson,Newsletter,Drafting,2026-06-30,Article,Nurture
Before/after website refresh,Portfolio,Idea,2026-07-12,Image,Leads
```

**goals.csv**
```
Goal,Horizon,Metric,Target,Current,Status
Reach 3 active retainer clients,Quarter,Active retainers,3,1,On track
Publish weekly for the quarter,Quarter,Posts published,13,4,On track
Net profit at or above baseline,Month,Net positive months,3,2,At risk
```

---

## 10. Notes & honest caveats

- This is a structure, not advice. Adapt fields to how you actually work; delete what you don't use.
- The invoice template is a cover note, not a legal/tax document. Confirm what formal invoicing and tax rules apply where you operate.
- Formulas are written for the current Notion formula editor; if Notion's syntax changes, the plain-English logic still tells you what each field should do.
- No outcomes are promised. A template organizes work; the work is still yours.
