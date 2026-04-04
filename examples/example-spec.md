"""Example SPEC for testing the pipeline."""

# Example Feature Specification

## Feature: User Authentication System

### Goal
Implement a JWT-based authentication system with user registration and login endpoints.

### Scope

**IN**:
- User registration (email, password)
- User login (email, password)
- JWT token generation and validation
- Password hashing
- Token refresh mechanism
- PostgreSQL persistence

**OUT**:
- OAuth/social login (future phase)
- Multi-factor authentication
- Password recovery flow
- Session management (using JWT, not sessions)

### Constraints

**Stack**:
- FastAPI for HTTP layer
- SQLAlchemy ORM for database
- Pydantic for validation
- PyJWT for token handling
- bcrypt for password hashing
- PostgreSQL 14+

**Performance**:
- Registration endpoint: <500ms
- Login endpoint: <500ms
- Token validation: <10ms

**Security**:
- Passwords hashed with bcrypt (cost=12)
- Tokens signed with RS256
- No hardcoded secrets
- Rate limiting on auth endpoints (per IP)
- HTTPS only in production

### Acceptance Criteria

- [ ] User registration creates user in DB with hashed password
- [ ] Login returns valid JWT token
- [ ] Token contains user ID and email
- [ ] Token expires after 24 hours
- [ ] Refresh endpoint returns new token
- [ ] Invalid token raises 401 Unauthorized
- [ ] Expired token raises 401 with "expired" message
- [ ] Duplicate email on registration raises 409 Conflict
- [ ] All endpoints have unit tests (90%+ coverage)

### Open Questions

1. **Token expiration duration**: Currently 24 hours, is that acceptable?
2. **Refresh token rotation**: Should we use separate refresh tokens?
3. **Rate limiting implementation**: Use Redis or in-memory cache?
4. **Email validation**: Confirm email before activation or allow immediate login?

### Architecture Decisions

- **JWT over sessions**: Stateless, scales better
- **RS256 signing**: Public key verification for microservices
- **bcrypt over other hashing**: Industry standard, slow by design

### Dependencies

- Existing database connection pool (from config.py)
- Email validation utility (from utils.validators)
- Rate limiter (to be implemented or external service)

### Timeline & Priority

- **Priority**: P0 (blocking feature)
- **Size**: M (2-3 sprints)
- **Dependencies**: Config module (blocking)

---

## Example: How This Feeds the Pipeline

After normalization, this spec would be passed to:

1. **Architecture Stage**: Design module structure (auth service, models, routes)
2. **Decomposition**: Break into tasks:
   - T001: User model + migration
   - T002: Password hashing service
   - T003: JWT token generation
   - T004: Register endpoint
   - T005: Login endpoint
   - T006: Token validation middleware
   - T007: Refresh endpoint

3. **TDD**: Write tests for each task
4. **Implementation**: Generate code per task with test-driven iteration
5. **Review**: Verify all acceptance criteria met

---

## Using This Example

Copy this content to:
```
artifacts/SPEC.md
```

Then run:
```bash
python -m src.cli run --spec artifacts/SPEC.md
```

The pipeline will:
1. Normalize the spec (human review)
2. Design the architecture
3. Decompose into tasks
4. Generate tests
5. Implement features
6. Run final review

Each stage has human checkpoints where approval is required before proceeding.
