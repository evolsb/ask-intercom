# AI Documentation Maintenance Guide

> **Instructions for AI agents on keeping docs updated** - optimized for solo vibe coding

## 🎯 Core Principles

1. **Update in place** - Modify existing docs rather than creating new ones
2. **One source of truth** - Don't duplicate information across files
3. **Preserve decisions** - Archive completed work as reference, don't delete
4. **Match the energy** - Update based on natural development flow, not artificial timelines

## 📝 Daily/Session Updates (Low friction)

### After Each Coding Session
Update these files based on what actually happened:

#### 1. `docs/planning/current-focus.md`
```markdown
🔄 **Working on**: [What you actually worked on]
🎯 **Next**: [What feels right to do next]  
🚧 **Blocked on**: [Any real blockers or just "nothing - ready to code!"]
```

#### 2. Current Phase Progress Files
**For MCP work**: `docs/implementation/phase-0.5-mcp/progress.md`  
**For Web work**: `docs/implementation/phase-0.5-web/progress.md`

Update the **"Current Vibe"** section:
- What did you work on?
- What's next?
- Any discoveries or blockers?
- Energy level check

#### 3. Current Phase Tasks Files  
**For MCP**: `docs/implementation/phase-0.5-mcp/tasks.md`  
**For Web**: `docs/implementation/phase-0.5-web/tasks.md`

- Mark completed tasks with ✅
- Add new discovered tasks
- Move blocked tasks to appropriate energy level
- Note any complexity changes

## 🔄 Progress Tracking Patterns

### Task Status Updates
```markdown
## ✅ Recently Completed
- ✅ [What you just finished]
- ✅ [Other recent wins]

## 🔄 Currently Working On  
- [Active task with current status]

## 🎯 Next Session Plans
- [What feels right to tackle next]
- [Alternative if energy is different]
```

### Energy-Based Notes
```markdown
## ⚡ Energy & Context
- **High energy tasks**: [What needs deep focus]
- **Medium energy tasks**: [What needs steady work]  
- **Low energy tasks**: [What's good for tired sessions]
- **Parallel option**: [Switch to other track when wanting variety]
```

## 🚀 When Switching Between Tracks

### MCP ↔ Web Development
When switching between parallel tracks, update:

1. **`docs/planning/current-focus.md`** - Note the track switch and why
2. **Previous track progress file** - Save your place clearly
3. **New track progress file** - Note what you're picking up

Example:
```markdown
## 🔄 Track Switch
**Switching from**: MCP research (felt stuck on library selection)
**Switching to**: Web frontend (want to build something visual)
**Context saved**: MCP library options documented in progress.md
```

## 📊 Bigger Updates (When phases change)

### Completing a Phase or Major Milestone
1. **Mark completion** in `docs/planning/roadmap.md`
2. **Archive progress** in phase overview (mark as complete)
3. **Update next-up** if the next phase is now better defined
4. **Reflect in current-focus** what the new priority is

### Adding New Phases or Major Features
1. **Create phase folder** using template structure
2. **Add to roadmap** with rough timeline
3. **Link from current-focus** if it's the new priority
4. **Update index.md** navigation

## 🎮 Vibe-Coding Specific Patterns

### Flexible Timeline Updates
Instead of "Week 1, Week 2":
```markdown
## Recent Progress
- **Yesterday**: [What you did]
- **Today**: [What you're working on]  
- **Next**: [What feels right to do next]
- **Someday**: [Longer-term plans]
```

### Energy Level Matching
```markdown
## Current Session Energy
- 🟢 High: [Deep architecture work, complex features]
- 🟡 Medium: [Steady implementation, testing]
- 🔴 Low: [Documentation, cleanup, config]
- 🎮 Variety: [Switch tracks for different challenges]
```

### Discovery-Driven Updates
When you discover something new:
```markdown
## Discovered Along the Way
- [New insight about technical approach]
- [Unexpected complexity or simplicity]
- [Better way to do something]
- [New idea for future phases]
```

## 🚫 Anti-Patterns to Avoid

- ❌ Creating detailed plans for phases 6+ months out
- ❌ Updating roadmap timelines without updating current progress
- ❌ Creating new files instead of updating existing ones
- ❌ Writing "what should happen" instead of "what actually happened"
- ❌ Forcing artificial timeline pressure

## 📂 File Update Hierarchy

### Always Update (After each session)
1. `docs/planning/current-focus.md` - Current status
2. Relevant phase progress file - What you worked on

### Sometimes Update (When things change)
3. Relevant phase tasks file - Mark completed, add discovered
4. `docs/planning/roadmap.md` - If timeline or priority shifts

### Rarely Update (Major changes only)
5. Phase overview files - Only when scope or goals change
6. `docs/index.md` - Only when navigation structure changes

## 🎯 Success Indicators

Good documentation maintenance feels like:
- ✅ Easy to pick up where you left off after a break
- ✅ Clear what the current priority is
- ✅ Progress is visible and motivating
- ✅ Decisions are preserved with context
- ✅ New contributors can understand current state

---

*Remember: Documentation should support your coding flow, not interrupt it. Update what's useful, skip what's not.*
