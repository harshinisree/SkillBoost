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