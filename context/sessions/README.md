# Session Logs

Work session logs organized chronologically by month.

## Structure

```
sessions/
├── 2025-01/
│   ├── 01-15-initial-setup.md
│   └── 01-20-auth-implementation.md
├── 2025-02/
│   └── 02-03-database-migration.md
└── README.md (this file)
```

## Naming Convention

**Format:** `YYYY-MM/MM-DD-description.md`

- `YYYY-MM/` - Month directory
- `MM-DD` - Day of month
- `description` - Short keyword describing the work (kebab-case)

**Examples:**
- `2025-01/01-15-initial-setup.md`
- `2025-02/02-10-api-refactor.md`
- `2025-03/03-05-bug-fixes.md`

## What to Include in Session Logs

Each session log should capture:

1. **What was accomplished** - Concrete deliverables and changes
2. **Key decisions made** - Important choices and their rationale
3. **Issues encountered** - Blockers, bugs, or challenges faced
4. **Next steps** - Clear actions for the next session

## Example Session Log

```markdown
# Session: Initial Database Setup - 2025-01-15

## Accomplished
- Created initial database schema with users, posts, and comments tables
- Set up migration system using [tool]
- Implemented connection pooling

## Key Decisions
- Chose PostgreSQL over MySQL for better JSON support
- Used UUID for primary keys to avoid collision in distributed system

## Issues Encountered
- Connection timeout issues with default pool settings
- Resolved by increasing max_connections to 100

## Next Steps
- Add indexes for common query patterns
- Implement database seeding script
- Write integration tests for repository layer
```

## Tips

- **Create session logs at the end of each session** while the work is fresh
- **Be specific** about what was done, not just general descriptions
- **Document decisions** with rationale so future you understands why
- **Link to relevant docs** in other directories (design/, architecture/, etc.)
- **Keep it concise** but informative
