# Project Context Documentation

**Navigation guide for humans and AI agents working on this project.**

## Quick Start

**New to the project?** Start here: [`onboarding/START_HERE.md`](onboarding/START_HERE.md)

**Returning to work?** Check [`status/current-focus.md`](status/current-focus.md) for active work.

## Documentation Structure

```
context/
├── onboarding/          Entry point and quick start guides
├── architecture/        System design and technical decisions
├── design/             Feature and component design documents
├── requirements/       Feature specifications and requirements
├── specifications/     Formal technical specifications for implementation
├── status/             Project roadmap and progress tracking
├── research/           Investigation findings and API research
├── roles/              Agent role definitions and workflows
└── sessions/           Work session logs and notes
```

## Directory Guide

### 📚 `onboarding/` - Getting Started

Entry point documentation for understanding the project quickly.

**When to use:** First time working on the project, or returning after time away.

**Typical files:**
- `START_HERE.md` - Primary entry point with current status and quick context
- `quick-start-guide.md` - How to use the system

---

### 🏗️ `architecture/` - System Architecture

High-level system design, architectural decisions, and rationale.

**When to create:** When making architectural decisions, designing system components, or documenting technical patterns.

**When to read:** Before making structural changes, adding major features, or when understanding system design.

**Typical files:**
- `overview.md` - High-level architecture overview
- `database-design.md` - Database/schema design decisions
- `reviews/` - Periodic architecture reviews and audits

---

### 🎨 `design/` - Feature & Component Design

Design documents for specific features and components.

**When to create:** When designing a new feature or major component before implementation.

**When to read:** Before implementing a feature to understand the design.

---

### 📋 `requirements/` - Feature Requirements

Specifications and requirements for features.

**When to create:** When defining what a feature should do, user stories, acceptance criteria.

**When to read:** Before starting feature work to understand requirements.

---

### 📐 `specifications/` - Formal Technical Specifications

Detailed technical specifications for implementation agents and developers.

**When to create:** After design is approved and before implementation begins.

**When to read:** When implementing a feature - provides exact API contracts, data models, business rules, and validation requirements.

**Typical files:**
- API specifications (endpoints, schemas, error codes)
- Data models (TypeScript, JSON Schema, SQL)
- Interface contracts and state machines
- Business logic rules
- Performance and security specifications

**Flow:** requirements → design → specifications → implementation

---

### 📊 `status/` - Progress & Planning

Current project state, roadmap, and work tracking.

**Typical files:**
- `roadmap.md` - Long-term project roadmap
- `backlog.md` - Backlog of features and improvements
- `current-focus.md` - Current work and immediate next steps
- `completed/` - Archive of completed work

**When to update:**
- Update `current-focus.md` as work progresses
- Move docs to `completed/` when work is merged to main

---

### 🔬 `research/` - Investigation & Research

Research findings, API investigations, and exploratory work.

**When to create:** When investigating APIs, libraries, or approaches before making decisions.

**When to read:** When evaluating similar technical decisions.

---

### 🎭 `roles/` - Agent Role Definitions

Role definitions for specialized AI agents with tailored workflows and responsibilities.

**When to use:** At the start of a session to assign an agent a specific role (architect, implementer, researcher, etc.).

**Typical files:**
- `README.md` - Guide to using roles
- `role-architect.md` - Software architect role
- `role-implementer.md` - Code implementer role
- `role-researcher.md` - Research specialist role
- Additional custom roles as needed

**How to use:** `"You are the [role]. Read roles/role-[name].md and follow that workflow."`

---

### 📝 `sessions/` - Work Session Logs

Session-by-session work logs organized by month.

**Structure:** `sessions/YYYY-MM/MM-DD-description.md`

**When to create:** At the end of each work session to document what was accomplished.

**Naming convention:** `MM-DD-description.md` where description is a short keyword for the work.

---

## For AI Agents: Session Workflow

### Starting a New Session

1. **Read the entry point:** [`onboarding/START_HERE.md`](onboarding/START_HERE.md)
2. **Check current focus:** [`status/current-focus.md`](status/current-focus.md)
3. **Review relevant design docs** from `architecture/` or `design/`
4. **Understand the goal** for this session from the user

### During a Session

- **Keep notes** of decisions, discoveries, and work completed
- **Update status** in `status/current-focus.md` as major milestones are reached
- **Create design docs** in `design/` if designing something new
- **Reference existing docs** by relative path when explaining decisions

### Ending a Session

**The user will start new sessions**, but you should prepare by documenting your work.

1. **Create a session log** in `sessions/YYYY-MM/MM-DD-description.md` with:
   - What was accomplished
   - Key decisions made
   - Issues encountered
   - Next steps

2. **Update `status/current-focus.md`** with:
   - Completed work
   - Current state
   - Clear next steps for the next session

3. **Archive completed work** if a feature/refactor is done:
   - Move relevant design/status docs to `status/completed/`
   - Update `roadmap.md` or `backlog.md` as needed

### Creating New Documents

| Document Type | Location | Naming |
|--------------|----------|--------|
| Architecture decision | `architecture/` | `kebab-case.md` |
| Feature design | `design/` | `kebab-case.md` |
| Feature requirements | `requirements/` | `kebab-case.md` |
| Research findings | `research/` | `kebab-case.md` |
| Session notes | `sessions/YYYY-MM/` | `MM-DD-description.md` |
| Completed work archive | `status/completed/` | `kebab-case.md` |

**Always use kebab-case** for filenames (lowercase with hyphens).

---

## Document Lifecycle

```
┌─────────────────┐
│ New Feature     │
│ Request         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│ requirements/   │─────▶│ design/          │
│ What to build   │      │ How to build it  │
└─────────────────┘      └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ Implementation   │
                         │ (track in        │
                         │ sessions/)       │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ Merge to main    │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ Move to          │
                         │ status/completed/│
                         └──────────────────┘
```

---

## Key Principles

1. **Single source of truth** - Don't duplicate information across documents
2. **Link, don't copy** - Reference other docs with relative links
3. **Keep current** - Update docs as decisions change
4. **Archive completed work** - Move to `completed/` when merged to main
5. **Session-based workflow** - Document work at the end of each session
6. **Self-documenting structure** - The directory structure should guide where things go

---

## Maintenance

**The structure maintains itself when you:**
- Put docs in the right category
- Use consistent naming (kebab-case)
- Archive completed work
- Update status docs as you go
- Create session logs at the end of sessions

**No additional maintenance needed** - the system is designed to be self-sustaining.
