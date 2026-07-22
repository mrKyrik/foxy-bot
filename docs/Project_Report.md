# Kumiho Project Security & Performance Report
**Date:** 2026-07-21
**Prepared by:** Antigravity (Product Manager)

## 1. Recent Commits Overview
The following recent commits have been reviewed during this assessment:
- `450ac30df65efcaa0544f190664a4cbdf9471fab`: feat: PKCE ve state parametresi ile güvenli OAuth implementasyonu
- `ef70291b9fe9f82ffa08568a680b2d157e438022`: Fix UI alert lock on form validation, fix dict rows bug, rename Lumina to Kumiho
- `c97b46a829e538ad1b0d25de9ecef274b3825b22`: Fix bugs: forms UI, Oracle DB, private_voice, logs
- `49193c2bbbceb2a9af223dfbd1e2d89a9114ba52`: Fix form logging and AppLogPage details rendering
- `7881b98bfb8f3e99ee3a2eabdd74b0bbdeebef11`: fix(owner): properly use commands.NotOwner to prevent help command spam

## 2. Identified Vulnerabilities

### 2.1. Hardcoded Database Credentials (Critical)
Both `core/database.py` and `web/api/main.py` contain hardcoded Oracle DB credentials in plaintext:
```python
DB_USER = "admin"
DB_PASSWORD = "$@P%5WCUgMnb"
DB_DSN = "kumihodb_high"
```
**Risk:** If the codebase is exposed or uploaded to a public repository, attackers can directly access and modify the production database.

### 2.2. Weak JWT Secret Fallback (High)
In `web/api/main.py`, the `JWT_SECRET` falls back to a hardcoded string if not found in the environment:
```python
JWT_SECRET = os.getenv("JWT_SECRET", "default_secret_key_change_me")
```
**Risk:** If the `.env` file fails to load or is missing this variable in production, attackers can trivially forge JWT tokens and gain administrative access to the web dashboard.

### 2.3. Overly Permissive CORS Policy (Medium)
The FastAPI backend (`web/api/main.py`) allows cross-origin requests from insecure HTTP endpoints (e.g., `http://152.67.86.27` and `http://kyrik.duckdns.org`).
**Risk:** Man-in-the-Middle (MitM) attacks can intercept traffic, potentially stealing session tokens or manipulating requests.

## 3. Performance Issues

### 3.1. Synchronous Database Calls in Async Context (Severe)
The FastAPI backend uses synchronous Oracle DB connections (`get_db_connection` mapping to `oracledb.connect()`) directly inside dependency functions like `verify_guild_access`.
**Impact:** Since FastAPI runs on an asynchronous event loop, blocking database calls will block the entire event loop. Under heavy load, the API will freeze and fail to handle concurrent requests.

### 3.2. Expensive Query Translations on the Fly (Moderate)
The `SyncOracleCursor` in `web/api/main.py` uses multiple complex Regex operations (`re.sub`) on every single query to translate SQLite syntax to Oracle syntax.
**Impact:** This adds unnecessary CPU overhead for every database transaction.

## 4. Remediation Plan (How to Fix)

### Fixing Hardcoded Credentials
- **Action:** Remove `DB_PASSWORD`, `DB_USER`, and `DB_DSN` from the source code. Store these values in the `.env` file. Update the code to use `os.environ.get("DB_PASSWORD")`.
- **Action:** Rotate the Oracle DB password immediately since it has already been committed to the repository.

### Fixing JWT Secret Fallback
- **Action:** Remove the default fallback value. Instead, enforce its presence during application startup:
  ```python
  JWT_SECRET = os.getenv("JWT_SECRET")
  if not JWT_SECRET:
      raise RuntimeError("JWT_SECRET must be set in environment variables.")
  ```

### Restricting CORS
- **Action:** Remove HTTP endpoints from the `allow_origins` list in production. Ensure only `https://kyrik.duckdns.org` is allowed, keeping `http://localhost` only if conditionally enabled for development.

### Fixing Synchronous DB Calls
- **Action:** Replace the synchronous DB connections in `web/api/main.py` with the asynchronous connection pool (`oracledb.create_pool_async`), similar to what is used in `core/database.py`. Ensure all FastAPI dependencies and route handlers that interact with the database are defined with `async def` and `await` their database operations.

### Optimizing Query Translations
- **Action:** Standardize the database schema to Oracle natively or use an ORM (like SQLAlchemy) or a query builder to abstract the SQL dialect, rather than using heavy Regex substitutions at runtime.
