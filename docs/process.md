## Working agreement

Nothing merges without a linked issue, green CI, and every acceptance criterion ticked.

**Definition of Done (every issue)**

- [ ] Every acceptance criterion is a passing test, and test names start with the story ID
- [ ] CI is green (pytest and ruff)
- [ ] The PR description shows real test output, including the 401, 403, 409 cases
- [ ] README API table and docs are updated if endpoints changed
- [ ] Merged by PR, branch deleted

**Conventions**

| Item | Rule |
| --- | --- |
| Branches | One per issue: `feature/us6-enroll`, `task/t0-ci`, `fix/login-pending-403`. `main` is protected: PR plus green CI required |
| Commits | `type(scope): what and why (#issue)`, for example `feat(enroll): block enrollment when course is full (#12)`. Types: feat, fix, test, docs, chore, refactor |
| Labels | `story`, `task`, `bug`, `docs`, `stretch` |
| Milestones | Sprint 0 to Sprint 4; the description holds the sprint goal and dates |
| Board | To Do, In Progress, In Review, Done. At most 2 items In Progress (assumed) |
| PR body | `Closes #id`, what changed, how it was tested (paste output), AC checklist |

**Sprint ritual:** at the start, write the goal and dates in the milestone. At the end, add a demo note (a Swagger screenshot) and a 3-line retro to `docs/retro.md`: what worked, what did not, what changes.