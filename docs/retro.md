# Sprint retros

## Sprint 0 (goal: ready to code)
- **Worked:** CI went green with a real MySQL container on the first run; one script created the labels, milestones, and 22 issues.
- **Did not work:** database URL mistakes (placeholder user, unencoded @ in the password) cost time; the docs folder was first named `doc`.
- **Change:** run pytest locally before every commit and check folder names against the design doc.

## Sprint 1 (goal: register, approve, log in)
- **Worked:** all 4 issues delivered with tests first; 71 tests pass on MySQL; real demo of the full approval flow.
- **Did not work:** a test-setup bug only showed on MySQL (stale data from transaction isolation); one branch was made from an out-of-date main.
- **Change:** always Fetch and Pull main before creating a branch; put Closes #N in the PR description, not the title.

## Sprint 2 (goal: courses and enrollment)
- **Worked:** US4 to US7 delivered; 142 tests; tests now guard against N+1 queries and prove the database's own safety nets (UNIQUE, foreign key, CHECK).
- **Did not work:** one branch was made before the previous story was merged; a stale server returned 405; the test run now takes over 2 minutes.
- **Change:** check the History tab before every branch; run the server with --debug; make tests faster with a cheaper bcrypt setting (T4-8).

## Sprint 3 (goal: seat limits that hold under concurrency)
- **Worked:** the race test (10 students, 3 seats) caught a real bug: locking the course row alone still oversold, because REPEATABLE READ served a stale snapshot. Fixed with locking reads; 10/10 runs pass.
- **Did not work:** the design doc's plan was wrong in a way only a real concurrency test on MySQL could reveal.
- **Change:** prove critical rules with tests that fail when the protection is removed, not just tests that pass.


## Sprint 4 (goal: production-ready)
- **Worked:** 10 tasks delivered: error format, rate limit and CORS, JSON logging, audit log, indexes with an EXPLAIN report, Swagger docs and seed data, Docker Compose, quality gates, migrations, and the final README. 227 tests, 98% coverage; ruff and mypy run in CI.
- **Did not work:** the request logger crashed after a database error (found by a test and fixed with a rollback); the generated migration needed manual fixes before it would run on MySQL; a full test run took over 2 minutes until bcrypt was made cheaper in tests (now about 45 seconds).
- **Change:** read generated code like any other code before committing it. The live deploy was deferred: free hosting sleeps when idle, and the repo already runs with one command.
