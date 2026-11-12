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