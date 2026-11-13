# SkillBoost

![CI](https://github.com/harshinisree/SkillBoost/actions/workflows/ci.yml/badge.svg)

   ## API

   | Method | Path | Who | Success | Errors |
   |---|---|---|---|---|
   | GET | /health | Public | 200 | none |
   | POST | /auth/register | Public | 201 | 400, 409 |
   | POST | /auth/login | Public | 200 with token | 400, 401, 403 |
   | GET | /admin/pending | Admin | 200 | 401, 403 |
   | POST | `/admin/approve/<id>` | Admin | 200 | 401, 403, 404 |
   | POST | /courses | Staff | 201 | 400, 401, 403 |
   | PUT | `/courses/<id>` | Staff, owner only | 200 | 400, 401, 403, 404 |
   | DELETE | `/courses/<id>` | Staff, owner only | 204 | 401, 403, 404 |
   | GET | /courses | Any approved user | 200, paginated | 400, 401 |
   | POST | /enrollments | Student | 201 | 400, 401, 403, 404, 409 |
   | DELETE | `/enrollments/<course_id>` | Student | 204 | 401, 403, 404 |
   | GET | /enrollments/me | Student | 200 | 401, 403 |
      ## Capacity-safe enrollment

   **Problem.** A course has a fixed number of seats. If many students enroll at the same moment, a naive "count the seats, then insert" lets several of them see the same free seat, and the course is oversold.

   **Approach.** Enrolling runs in one transaction that:
   1. locks the course row with `SELECT ... FOR UPDATE`, so requests for the same course take turns;
   2. checks for a duplicate and counts taken seats with locking reads, which always see the latest committed rows (a plain read under MySQL's default REPEATABLE READ would use a stale snapshot taken before the request waited for the lock);
   3. inserts the enrollment and commits, which releases the lock.

   The UNIQUE (student, course) constraint is a second safety net for a double-click.

   **Proof.** `test_us6b_ten_students_racing_for_three_seats` sends 10 enroll requests at the same instant, each on its own connection, for a course with 3 seats.

   | Version | Students enrolled (3 seats) |
   |---|---|
   | No locks | 9, then 6: oversold |
   | Course row locked, plain seat count | 10: oversold every run |
   | Course row locked and locking seat count (final) | 3, in 10 of 10 runs |