   # Sprint retros

   ## Sprint 0 (goal: ready to code)
   - **Worked:** CI went green with a real MySQL container on the first run; one script created the labels, milestones, and 22 issues.
   - **Did not work:** database URL mistakes (placeholder user, unencoded @ in the password) cost time; the docs folder was first named `doc`.
   - **Change:** run pytest locally before every commit and check folder names against the design doc.

   ## Sprint 1 (goal: register, approve, log in)
   - **Worked:** all 4 issues delivered with tests first; 71 tests pass on MySQL; real demo of the full approval flow.
   - **Did not work:** a test-setup bug only showed on MySQL (stale data from transaction isolation); one branch was made from an out-of-date main.
   - **Change:** always Fetch and Pull main before creating a branch; put Closes #N in the PR description, not the title.