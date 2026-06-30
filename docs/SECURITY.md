# Web Security Guide - Meridian Signal Service

This document provides security best practices and guidelines for developing, deploying, and maintaining the Meridian Signal Service. All contributors and operators must follow these guidelines to ensure the safety and integrity of the platform and user data.

## Table of Contents

1. [Security Principles](#security-principles)
2. [Authentication & Authorization](#authentication--authorization)
3. [Data Protection](#data-protection)
4. [API Security](#api-security)
5. [Infrastructure Security](#infrastructure-security)
6. [Development Security](#development-security)
7. [Incident Response](#incident-response)
8. [Security Checklist](#security-checklist)

---

## Security Principles

All security decisions in Meridian Signal Service should be guided by these core principles:

### 1. **Least Privilege**
- Grant users and services only the minimum permissions needed
- Use role-based access control (RBAC)
- Regularly audit and revoke unnecessary permissions
- Example: Database users should NOT have superuser privileges

### 2. **Defense in Depth**
- Implement multiple layers of security controls
- Don't rely on a single security mechanism
- Combine authentication, authorization, encryption, monitoring, and logging

### 3. **Secure by Default**
- Assume all input is malicious until proven otherwise
- Fail securely (deny by default, allow explicitly)
- Use strong defaults for timeouts, session lengths, and permissions

### 4. **Never Trust User Input**
- Validate all data from users, APIs, and external services
- Use type checking and schema validation (Pydantic)
- Sanitize output to prevent injection attacks

### 5. **Defense Against Common Attacks**
- SQL Injection: Use parameterized queries (SQLAlchemy with Pydantic models)
- Cross-Site Scripting (XSS): Sanitize output, use Content-Security-Policy headers
- Cross-Site Request Forgery (CSRF): Use CSRF tokens for state-changing operations
- Brute Force: Implement rate limiting on authentication endpoints
- Man-in-the-Middle (MITM): Use HTTPS/TLS everywhere

---

## Authentication & Authorization

### JWT Token Management

The service uses JWT (JSON Web Tokens) for stateless authentication. Follow these guidelines:

#### Token Configuration
```python
# In your config/settings.py or equivalent:

JWT_SIGNING_KEY = os.getenv("JWT_SIGNING_KEY")  # Must be strong and random
JWT_ALGORITHM = "HS256"  # or RS256 for production
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 15  # Short-lived access tokens
JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7     # Refresh tokens expire in 7 days

# Ensure JWT_SIGNING_KEY is:
# - At least 32 characters (for HS256)
# - Cryptographically random
# - Rotated regularly (implement key rotation strategy)
# - Never committed to version control
```

#### Token Best Practices
```python
# ✅ GOOD: Use short-lived access tokens with refresh token flow
from datetime import datetime, timedelta, timezone
from jose import jwt

def create_tokens(user_id: str):
    """Create access and refresh tokens."""
    
    # Access token (short-lived)
    access_payload = {
        "sub": user_id,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        "iat": datetime.now(timezone.utc)
    }
    access_token = jwt.encode(access_payload, JWT_SIGNING_KEY, algorithm=JWT_ALGORITHM)
    
    # Refresh token (longer-lived, stored securely)
    refresh_payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "iat": datetime.now(timezone.utc)
    }
    refresh_token = jwt.encode(refresh_payload, JWT_SIGNING_KEY, algorithm=JWT_ALGORITHM)
    
    return access_token, refresh_token

# ❌ BAD: Long-lived tokens without refresh mechanism
# exp: datetime.now() + timedelta(days=365)  # Too long!
```

### Password Security

If the service handles password-based authentication:

```python
from passlib.context import CryptContext

# ✅ Use secure password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

# Password requirements:
# - Minimum 12 characters
# - At least one uppercase letter
# - At least one lowercase letter
# - At least one number
# - At least one special character

PASSWORD_MIN_LENGTH = 12
PASSWORD_REQUIREMENTS_REGEX = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{12,}$"
```

### Role-Based Access Control (RBAC)

```python
from enum import Enum

class Role(str, Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    USER = "user"
    GUEST = "guest"

class User(BaseModel):
    id: str
    email: str
    role: Role
    permissions: list[str]

# ✅ Use role-based route protection
from fastapi import Depends, HTTPException, status

def require_role(required_role: Role):
    """Dependency to enforce role requirements."""
    async def check_role(current_user: User = Depends(get_current_user)):
        if current_user.role not in [required_role, Role.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return check_role

@router.get("/admin/users")
async def get_all_users(current_user: User = Depends(require_role(Role.ADMIN))):
    """Only admins can access this endpoint."""
    # Implementation
    pass
```

---

## Data Protection

### Encryption in Transit

```python
# ✅ HTTPS/TLS is mandatory for all endpoints
# In production, always use HTTPS with a valid certificate

# In FastAPI, enforce HTTPS:
from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

app = FastAPI()
app.add_middleware(HTTPSRedirectMiddleware)

# Use strict security headers:
from fastapi.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Enable browser XSS filter
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'"
        
        # HSTS (HTTP Strict Transport Security)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response

app.add_middleware(SecurityHeadersMiddleware)
```

### Encryption at Rest

```python
# ✅ Encrypt sensitive data in the database

from cryptography.fernet import Fernet
import os

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")  # Generate with: Fernet.generate_key()
cipher = Fernet(ENCRYPTION_KEY)

def encrypt_data(data: str) -> str:
    """Encrypt sensitive data."""
    return cipher.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    """Decrypt sensitive data."""
    return cipher.decrypt(encrypted_data.encode()).decode()

# Use in SQLAlchemy models:
from sqlalchemy import Column, String
from sqlalchemy.types import TypeDecorator

class EncryptedString(TypeDecorator):
    """A type that encrypts data before storing in database."""
    impl = String
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return encrypt_data(value)
    
    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return decrypt_data(value)

class APIKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))
    key_hash = Column(String)  # Hash only, never store plaintext
    encrypted_key = Column(EncryptedString)  # For recovery only
```

### Secret Management

```bash
# ✅ DO: Use environment variables or secret managers
export DATABASE_URL="postgres://user:pass@localhost/db"
export REDIS_URL="redis://localhost:6379/0"
export JWT_SIGNING_KEY="your-strong-random-key-here"
export ENCRYPTION_KEY="your-fernet-key-here"

# ❌ DON'T: Commit secrets to version control
# Never do this:
# DATABASE_URL = "postgres://user:pass@localhost/db"  # Hardcoded!
# API_KEY = "sk-1234567890abcdef"  # Exposed!

# ✅ For production (Fly.io):
fly secrets set DATABASE_URL="..."
fly secrets set JWT_SIGNING_KEY="..."

# ✅ For local development:
# 1. Copy .env.example to .env
# 2. Edit .env with your local values
# 3. Load with python-dotenv: from dotenv import load_dotenv; load_dotenv()
```

---

## API Security

### Input Validation

```python
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional

class CreateListingRequest(BaseModel):
    """Validate all incoming data strictly."""
    
    # String validation
    address: str = Field(..., min_length=1, max_length=255)
    city: str = Field(..., min_length=1, max_length=100)
    
    # Email validation
    contact_email: EmailStr
    
    # Numeric validation
    price: float = Field(..., gt=0, lt=1e10)  # Must be positive
    
    # Optional fields with defaults
    description: Optional[str] = Field(None, max_length=5000)
    
    # Custom validation
    @validator('address')
    def address_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Address cannot be empty')
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "address": "123 Main St",
                "city": "New York",
                "contact_email": "user@example.com",
                "price": 250000.00,
                "description": "Beautiful 3-bedroom home"
            }
        }

# ✅ FastAPI automatically validates with Pydantic
@router.post("/listings")
async def create_listing(listing: CreateListingRequest):
    # FastAPI returns 422 if validation fails
    # Invalid data is rejected automatically
    pass
```

### SQL Injection Prevention

```python
# ✅ GOOD: Use SQLAlchemy ORM (parameterized queries)
from sqlalchemy import select

async def get_listing_by_id(listing_id: str, db: AsyncSession):
    result = await db.execute(
        select(Listing).where(Listing.id == listing_id)  # Parameterized!
    )
    return result.scalar_one_or_none()

# ❌ BAD: String concatenation (SQL injection risk!)
# query = f"SELECT * FROM listings WHERE id = '{listing_id}'"  # NEVER!

# ✅ GOOD: If you must use raw SQL, use parameters
raw_query = "SELECT * FROM listings WHERE id = :listing_id"
result = await db.execute(raw_query, {"listing_id": listing_id})
```

### Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Apply rate limiting to sensitive endpoints
@router.post("/login")
@limiter.limit("5/minute")  # Max 5 login attempts per minute
async def login(credentials: LoginRequest, request: Request):
    # Implementation
    pass

@router.post("/register")
@limiter.limit("3/hour")  # Max 3 registrations per hour per IP
async def register(user_data: CreateUserRequest, request: Request):
    # Implementation
    pass

@router.get("/api/listings")
@limiter.limit("100/minute")  # Standard API rate limit
async def list_listings(skip: int = 0, limit: int = 10):
    # Implementation
    pass
```

### CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

# ✅ GOOD: Specify exact origins
allowed_origins = [
    "https://meridian.example.com",
    "https://app.meridian.example.com",
    "https://admin.meridian.example.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Specific origins only!
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=3600,
)

# ❌ BAD: Allow all origins
# allow_origins=["*"]  # Security risk!
```

### API Error Handling

```python
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

# ✅ GOOD: Generic error messages in production
@router.get("/listings/{listing_id}")
async def get_listing(listing_id: str, db: AsyncSession):
    try:
        listing = await get_listing_by_id(listing_id, db)
        if not listing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Listing not found"  # Generic message
            )
        return listing
    except Exception as e:
        # Log the full error internally
        logger.error(f"Error retrieving listing {listing_id}: {str(e)}")
        # Return generic error to user
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"  # Don't expose details
        )

# ❌ BAD: Expose sensitive information
# detail=f"Database connection failed: {str(e)}"  # Too detailed!
# detail="Error: KeyError: 'api_key' in auth.py line 42"  # Stack trace!
```

---

## Infrastructure Security

### Database Security

```yaml
# docker-compose.yml example with security settings

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}  # Strong random password
      POSTGRES_DB: meridian_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    # ✅ Security improvements:
    # 1. Use unprivileged postgres user (default)
    # 2. Mount as read-only where possible
    # 3. Don't expose to public network
    # 4. Use strong password
    # 5. Enable SSL connections in production

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}  # Require password
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    # ✅ Security improvements:
    # 1. Require password for Redis
    # 2. Don't expose to public network
    # 3. Use Redis ACL in Redis 6+
    # 4. Enable SSL for remote connections

volumes:
  postgres_data:
  redis_data:
```

### Container Security

```dockerfile
# Dockerfile - Security best practices

FROM python:3.12-slim

# ✅ Run as non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy only necessary files
COPY pyproject.toml poetry.lock ./
RUN pip install --no-cache-dir poetry && \
    poetry install --no-root --no-dev

COPY meridian/ ./meridian/

# Change ownership to appuser
RUN chown -R appuser:appuser /app

USER appuser

# ✅ Don't run as root
# ❌ BAD: USER root

EXPOSE 8000

CMD ["poetry", "run", "meridian-api"]
```

### Fly.io Deployment Security

```toml
# deploy/fly.toml - Security configuration

[app]
kill_signal = "SIGINT"
kill_timeout = 5

[build]
builder = "heroku"

[env]
# Environment variables for secrets (use `fly secrets set` instead of hardcoding)
PORT = "8000"

[http_service]
internal_port = 8000
force_https = true  # ✅ Force HTTPS in production

[[http_service.checks]]
grace_period = "5s"
interval = "30s"
method = "GET"
path = "/healthz"
timeout = "5s"
type = "http"

# Set secrets with:
# fly secrets set DATABASE_URL="..."
# fly secrets set JWT_SIGNING_KEY="..."
# fly secrets set ENCRYPTION_KEY="..."
```

### Network Security

```python
# Implement security headers in FastAPI

from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        # Prevent clickjacking attacks
        response.headers["X-Frame-Options"] = "DENY"
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Enable browser XSS filter
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Content Security Policy (prevent inline scripts, etc.)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'"
        )
        
        # HTTP Strict Transport Security (require HTTPS for 1 year)
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )
        
        # Referrer Policy (don't leak referrer info)
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy (disable unnecessary features)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=()"
        )
        
        return response

app.add_middleware(SecurityHeadersMiddleware)
```

---

## Development Security

### Dependency Management

```bash
# ✅ Keep dependencies updated
poetry update --dry-run  # Preview updates
poetry update            # Apply updates

# ✅ Scan for known vulnerabilities
pip install safety
safety check

# OR use GitHub Dependabot
# Enable in GitHub: Settings > Code security and analysis > Dependabot

# ✅ Pin exact versions in production
poetry lock --no-update
```

### Secret Scanning

```bash
# ✅ Enable GitHub secret scanning
# Settings > Code security and analysis > Secret scanning > Enable

# ✅ Use local git hooks to prevent accidental commits
# Create .git/hooks/pre-commit:

#!/bin/bash
git diff --cached --name-only | while read FILE; do
    if git show :$FILE | grep -E "(password|api_key|secret|token)" 2>/dev/null; then
        echo "ERROR: Potential secret found in $FILE"
        exit 1
    fi
done

# Make executable: chmod +x .git/hooks/pre-commit
```

### Code Review Security

When reviewing PRs, check for:

- [ ] No hardcoded secrets or credentials
- [ ] All user input is validated
- [ ] SQL queries are parameterized
- [ ] Authentication/authorization checks are in place
- [ ] Error messages don't expose sensitive info
- [ ] Dependencies are up-to-date
- [ ] Security headers are implemented
- [ ] Logging includes security events
- [ ] Rate limiting is applied where needed
- [ ] CORS is properly configured

### Testing Security

```python
# tests/test_security.py - Security-focused tests

import pytest
from fastapi.testclient import TestClient

@pytest.mark.security
def test_authentication_required():
    """Verify protected endpoints require authentication."""
    response = client.get("/api/listings")
    assert response.status_code == 401

@pytest.mark.security
def test_sql_injection_protection():
    """Verify SQL injection is prevented."""
    response = client.get("/api/listings/1' OR '1'='1")
    assert response.status_code == 404  # Should not inject

@pytest.mark.security
def test_cors_headers():
    """Verify CORS headers are correct."""
    response = client.get("/api/listings")
    # Should NOT have "Access-Control-Allow-Origin: *"
    assert response.headers.get("Access-Control-Allow-Origin") != "*"

@pytest.mark.security
def test_https_redirect():
    """Verify HTTP is redirected to HTTPS."""
    # Test that service requires HTTPS in production

@pytest.mark.security
def test_rate_limiting():
    """Verify rate limiting works."""
    for i in range(10):
        response = client.post("/login", json={"email": "test@example.com", "password": "wrong"})
    assert response.status_code == 429  # Too many requests

@pytest.mark.security
def test_password_requirements():
    """Verify password policy is enforced."""
    weak_passwords = [
        "short",
        "NoNumbers!",
        "noupppercase123!",
        "NOLOWERCASE123!",
    ]
    for password in weak_passwords:
        response = client.post("/register", json={
            "email": "user@example.com",
            "password": password
        })
        assert response.status_code == 422
```

---

## Incident Response

### Security Incident Procedure

If a security issue is discovered:

1. **Assess the severity**
   - Is production affected? Is data exposed?
   - How many users are impacted?
   - What is the exposure timeline?

2. **Contain the incident**
   - Isolate affected systems if necessary
   - Revoke compromised credentials
   - Rotate secrets
   - Block malicious IPs if relevant

3. **Investigate the root cause**
   - Review logs and audit trails
   - Determine how the breach occurred
   - Check for lateral movement

4. **Remediate**
   - Fix the underlying vulnerability
   - Apply patches
   - Deploy fixes to production

5. **Notify stakeholders**
   - Inform affected users
   - Provide remediation steps
   - Follow legal/compliance requirements

6. **Document and learn**
   - Write post-mortem
   - Update security procedures
   - Implement preventive measures

### Reporting a Vulnerability

If you discover a security vulnerability:

1. **DO NOT** create a public GitHub issue
2. **DO** email security@example.com with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if known)
3. We will respond within 24 hours

---

## Security Checklist

### Before Deployment

- [ ] All secrets are stored in environment variables (not in code)
- [ ] HTTPS/TLS is enforced
- [ ] Database password is strong (16+ characters, random)
- [ ] JWT signing key is strong (32+ characters)
- [ ] CORS is configured for specific origins only
- [ ] Rate limiting is enabled
- [ ] Security headers are implemented
- [ ] Error messages are generic (no stack traces to users)
- [ ] Input validation is comprehensive
- [ ] Authentication and authorization are tested
- [ ] Dependencies are up-to-date and scanned
- [ ] Database user has minimal required permissions
- [ ] Secrets scanning is enabled in GitHub
- [ ] Logging includes security events
- [ ] All tests pass, including security tests
- [ ] Backup and recovery procedures are documented
- [ ] Monitoring and alerting are configured

### Ongoing

- [ ] Review and rotate JWT signing keys monthly
- [ ] Monitor for and apply security updates
- [ ] Conduct regular security audits
- [ ] Review access logs for suspicious activity
- [ ] Test incident response procedures quarterly
- [ ] Keep security documentation up-to-date
- [ ] Conduct team security training annually

---

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Pydantic Validation](https://docs.pydantic.dev/)
- [SQLAlchemy Security](https://docs.sqlalchemy.org/en/20/orm/tutorial.html)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [Fly.io Security](https://fly.io/docs/security/)

---

## Questions or Concerns?

If you have security questions or concerns, please reach out to the security team or create a private security discussion in the repository.

**Last Updated**: June 30, 2026
