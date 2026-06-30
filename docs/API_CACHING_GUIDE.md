# Efficient API Caching Guide

## Overview

This guide provides best practices for implementing efficient API caching for the Meridian Signal Service, with specific focus on GitHub API interactions, rate limiting, and response time optimization.

**Key Goals:**
- Maximize cache hit rates to minimize API calls
- Respect GitHub API rate limits (60 requests/hour for unauthenticated, 5,000 for authenticated)
- Maintain data freshness for market signals and listings
- Reduce response latency for clients

---

## 1. Understanding API Rate Limits

### GitHub API Rate Limits

GitHub enforces rate limits on all API requests:

| Metric | Unauthenticated | Authenticated |
|--------|-----------------|---------------|
| Requests/hour | 60 | 5,000 |
| Reset Window | 1 hour | 1 hour |
| Search API | 10/min | 30/min |

**Key Headers to Monitor:**
- `X-RateLimit-Limit`: Maximum requests per hour
- `X-RateLimit-Remaining`: Requests remaining in current window
- `X-RateLimit-Reset`: Unix timestamp when the limit resets

### Meridian Signal Service Rate Limit Strategy

Your service integrates with external data sources. Rate limiting considerations:

1. **External API Dependency**: Your service likely fetches property data, market data, and other signals
2. **Cascading Impact**: Rate limit on upstream API → degraded service availability
3. **Distributed Requests**: Multiple consumers hitting your API → amplified upstream load

**Example Scenario:**
```
100 clients requesting market reports
→ 100 requests to upstream market data API
→ Hit rate limit within minutes
→ Service degradation across all consumers
```

---

## 2. Caching Architecture

### Multi-Layer Caching Strategy

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌──────────────────────────┐
│  CDN / Browser Cache     │ ← HTTP Caching (Edge)
│  (HTTP Cache Headers)    │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│  Application Cache       │ ← Redis / In-Memory
│  (FastAPI Middleware)    │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│  Database Cache          │ ← SQLAlchemy Query Cache
│  (ORM Level)             │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│  Upstream APIs           │ ← Rate Limited!
│  (GitHub, Market Data)   │
└──────────────────────────┘
```

### Layer 1: HTTP Caching (Edge)

**Use HTTP cache headers for client-side and CDN caching:**

```python
from fastapi import FastAPI, Response
from datetime import timedelta

@router.get("/v1/market-reports/latest")
async def get_latest_report(
    geography: str,
    geo_type: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> MarketReport:
    """Get the latest market report for a geography."""
    service = MarketReportService(db)
    report = await service.get_latest_report(geography=geography, geo_type=geo_type)
    
    if not report:
        raise HTTPException(status_code=404, detail="No market report found")
    
    # Market reports: Cache for 1 hour (stable data)
    response.headers["Cache-Control"] = "public, max-age=3600"
    response.headers["ETag"] = f'"{report.id}-{report.updated_at.isoformat()}"'
    
    return report
```

**Cache-Control Header Patterns:**

| Resource | Strategy | Rationale |
|----------|----------|-----------|
| Market Reports | `public, max-age=3600` | Stable, not user-specific |
| Listings | `public, max-age=300` | Updated frequently |
| Signals | `private, max-age=60` | Real-time, user-specific |
| Comps | `public, max-age=1800` | Computation intensive |

### Layer 2: Application-Level Caching (Redis)

**Your service already has Redis configured. Use it strategically:**

```python
from redis.asyncio import Redis
from functools import wraps
import json
from datetime import timedelta

class CacheStrategy:
    """Define cache strategies for different endpoints."""
    
    # Cache TTL in seconds
    MARKET_REPORT_TTL = 3600  # 1 hour
    LISTING_TTL = 300         # 5 minutes
    SIGNAL_LOG_TTL = 60       # 1 minute
    COMP_RESULT_TTL = 1800    # 30 minutes

async def cache_get(
    redis_client: Redis,
    key: str,
) -> dict | None:
    """Get value from cache."""
    value = await redis_client.get(key)
    if value:
        return json.loads(value)
    return None

async def cache_set(
    redis_client: Redis,
    key: str,
    value: dict,
    ttl: int,
) -> None:
    """Set value in cache with TTL."""
    await redis_client.setex(
        key,
        ttl,
        json.dumps(value)
    )

def make_cache_key(*args, **kwargs) -> str:
    """Generate consistent cache keys."""
    parts = list(args) + [f"{k}={v}" for k, v in sorted(kwargs.items())]
    return ":".join(str(p) for p in parts)
```

**Example: Market Reports with Caching**

```python
@router.get("/v1/market-reports/latest")
async def get_latest_report(
    geography: str,
    geo_type: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
) -> MarketReport:
    """Get the latest market report for a geography."""
    
    # Step 1: Check cache
    cache_key = make_cache_key("report", geography, geo_type)
    cached = await cache_get(redis_client, cache_key)
    if cached:
        response.headers["X-Cache"] = "HIT"
        response.headers["Cache-Control"] = "public, max-age=3600"
        return cached
    
    # Step 2: Query database
    service = MarketReportService(db)
    report = await service.get_latest_report(geography=geography, geo_type=geo_type)
    
    if not report:
        raise HTTPException(status_code=404, detail="No market report found")
    
    # Step 3: Cache the result
    report_dict = report.dict()
    await cache_set(
        redis_client,
        cache_key,
        report_dict,
        CacheStrategy.MARKET_REPORT_TTL
    )
    
    response.headers["X-Cache"] = "MISS"
    response.headers["Cache-Control"] = "public, max-age=3600"
    return report
```

### Layer 3: Database Query Caching

**SQLAlchemy provides query caching for repetitive queries:**

```python
from sqlalchemy.orm import selectinload
from sqlalchemy.pool import NullPool
from functools import lru_cache

@lru_cache(maxsize=128)
async def get_signal_definitions(db: AsyncSession) -> list[SignalDefinition]:
    """Cache signal definitions (rarely change)."""
    stmt = select(SignalDefinition)
    result = await db.execute(stmt)
    return result.scalars().all()

# In your router:
@router.get("/v1/signals")
async def list_signal_definitions(
    db: AsyncSession = Depends(get_db),
) -> list[SignalDefinitionResponse]:
    """List all signal definitions with query caching."""
    definitions = await get_signal_definitions(db)
    return [SignalDefinitionResponse.from_orm(d) for d in definitions]
```

---

## 3. Cache Invalidation Strategies

### Challenge: Keeping Cache Fresh

Cache invalidation is notoriously difficult. Choose the right strategy based on your use case:

### Strategy 1: Time-Based Invalidation (TTL)

**Best for:** Stable data that doesn't change frequently

```python
# Market reports: Safe to cache for 1 hour
# Signals: Cache for 1 minute (real-time criticality)

CacheStrategy.MARKET_REPORT_TTL = 3600   # 1 hour
CacheStrategy.SIGNAL_LOG_TTL = 60        # 1 minute
```

**Pros:** Simple, predictable, no coordination needed
**Cons:** Stale data during TTL, must balance between freshness and cache benefit

### Strategy 2: Event-Based Invalidation

**Best for:** Data that changes unpredictably**

```python
async def refresh_report(
    request: MarketReportRefreshRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
) -> MarketReport:
    """Refresh market report and invalidate cache."""
    service = MarketReportService(db)
    report = await service.refresh_report(
        geography=request.geography,
        geo_type=request.geo_type.value,
        as_of=request.as_of,
    )
    
    # Invalidate related caches
    cache_key = make_cache_key("report", request.geography, request.geo_type.value)
    await redis_client.delete(cache_key)
    
    return report
```

### Strategy 3: Hybrid: TTL + Event-Based

**Best for:** Critical data requiring both freshness and performance**

```python
async def create_comp_job(
    request: CompRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
) -> CompJobResponse:
    """Create a comp job and invalidate related caches."""
    repo = CompRepository(db)
    job = await repo.create_job(request.subject_listing_id)
    
    # Trigger async computation
    compute_comps_task.delay(
        str(job.id), str(request.subject_listing_id), request.limit
    )
    
    # Invalidate comp cache for this listing
    cache_pattern = f"comps:{request.subject_listing_id}:*"
    keys = await redis_client.keys(cache_pattern)
    if keys:
        await redis_client.delete(*keys)
    
    # Also cache the job itself (short TTL for polling)
    await cache_set(
        redis_client,
        f"comp_job:{job.id}",
        job.dict(),
        300  # 5 minutes
    )
    
    return CompJobResponse.from_orm(job)
```

### Cache Warming

**Proactively load frequently-accessed data:**

```python
async def warm_caches(redis_client: Redis, db: AsyncSession) -> None:
    """Warm common caches on startup."""
    
    # 1. Cache all signal definitions (rarely change)
    signal_repo = SignalRepository(db)
    signals = await signal_repo.get_all()
    for signal in signals:
        cache_key = f"signal:{signal.id}"
        await cache_set(redis_client, cache_key, signal.dict(), 86400)  # 24 hours
    
    # 2. Cache latest market reports for top geographies
    top_geographies = ["US", "CA", "NYC", "LA"]
    for geo in top_geographies:
        cache_key = f"report:{geo}:latest"
        service = MarketReportService(db)
        report = await service.get_latest_report(geography=geo, geo_type="METRO")
        if report:
            await cache_set(redis_client, cache_key, report.dict(), 3600)

# Run on startup
@app.on_event("startup")
async def startup():
    redis_client = await get_redis()
    async with get_async_session_factory()() as db:
        await warm_caches(redis_client, db)
```

---

## 4. GitHub API Integration with Caching

If your service integrates with GitHub's REST or GraphQL APIs, implement these patterns:

### Rate Limit-Aware Client

```python
import httpx
from datetime import datetime, timedelta

class GitHubClient:
    """GitHub API client with rate limit awareness."""
    
    def __init__(self, token: str):
        self.token = token
        self.rate_limit_remaining = 5000
        self.rate_limit_reset = datetime.now()
    
    async def fetch_with_caching(
        self,
        url: str,
        redis_client: Redis,
        cache_ttl: int = 3600,
    ) -> dict:
        """Fetch GitHub API with caching."""
        
        # Step 1: Check cache
        cached = await cache_get(redis_client, f"github:{url}")
        if cached:
            return cached
        
        # Step 2: Check if we have rate limit capacity
        if self.rate_limit_remaining < 100:
            raise Exception(f"GitHub API rate limit low: {self.rate_limit_remaining} remaining")
        
        # Step 3: Make API call
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"Authorization": f"token {self.token}"},
            )
            response.raise_for_status()
            
            # Step 4: Update rate limit info
            self.rate_limit_remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
            reset_timestamp = int(response.headers.get("X-RateLimit-Reset", 0))
            self.rate_limit_reset = datetime.fromtimestamp(reset_timestamp)
            
            # Step 5: Cache and return
            data = response.json()
            await cache_set(redis_client, f"github:{url}", data, cache_ttl)
            return data
```

### Batch Requests to Reduce API Calls

```python
async def get_multiple_listings(
    listing_ids: list[str],
    redis_client: Redis,
    github_client: GitHubClient,
) -> list[dict]:
    """Fetch multiple listings, batching GitHub API requests."""
    
    results = []
    uncached_ids = []
    
    # Step 1: Get from cache
    for listing_id in listing_ids:
        cached = await cache_get(redis_client, f"listing:{listing_id}")
        if cached:
            results.append(cached)
        else:
            uncached_ids.append(listing_id)
    
    # Step 2: Batch fetch uncached listings (instead of N individual requests)
    if uncached_ids:
        # Assuming GitHub GraphQL API supports batch queries
        batch_query = """
        query {
            %s
        }
        """ % ",".join([
            f'listing_{lid}: repository(owner:"meridian", name:"{lid}") {{ ... }}'
            for lid in uncached_ids
        ])
        
        batch_results = await github_client.fetch_with_caching(
            "https://api.github.com/graphql",
            redis_client,
        )
        
        # Cache each result
        for lid, data in zip(uncached_ids, batch_results):
            await cache_set(redis_client, f"listing:{lid}", data, 3600)
            results.append(data)
    
    return results
```

---

## 5. Monitoring & Metrics

### Cache Metrics to Track

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class CacheMetrics:
    """Track cache performance."""
    
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size_bytes: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate hit rate percentage."""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0
    
    def record_hit(self) -> None:
        self.hits += 1
    
    def record_miss(self) -> None:
        self.misses += 1

# In your middleware:
cache_metrics = CacheMetrics()

@app.middleware("http")
async def cache_metrics_middleware(request: Request, call_next):
    """Track cache metrics."""
    response = await call_next(request)
    
    if response.headers.get("X-Cache") == "HIT":
        cache_metrics.record_hit()
    elif response.headers.get("X-Cache") == "MISS":
        cache_metrics.record_miss()
    
    return response

@router.get("/v1/metrics/cache")
async def get_cache_metrics(redis_client: Redis = Depends(get_redis)):
    """Expose cache metrics for monitoring."""
    info = await redis_client.info("stats")
    return {
        "hits": cache_metrics.hits,
        "misses": cache_metrics.misses,
        "hit_rate": cache_metrics.hit_rate,
        "redis_keys": info.get("db0", {}).get("keys", 0),
    }
```

### Logging Cache Operations

```python
import logging

logger = logging.getLogger(__name__)

async def cache_get_with_logging(
    redis_client: Redis,
    key: str,
) -> dict | None:
    """Get from cache with logging."""
    value = await redis_client.get(key)
    
    if value:
        logger.info(f"Cache HIT: {key}", extra={"cache_key": key, "hit": True})
        return json.loads(value)
    else:
        logger.info(f"Cache MISS: {key}", extra={"cache_key": key, "hit": False})
        return None
```

---

## 6. Best Practices Summary

### ✅ DO:

1. **Use Cache Headers Strategically**
   - `Cache-Control: public, max-age=3600` for stable data
   - `Cache-Control: private, max-age=60` for real-time data
   - Include `ETag` for conditional requests

2. **Implement Multi-Layer Caching**
   - HTTP layer (CDN, browsers)
   - Application layer (Redis)
   - Database layer (query caching)

3. **Monitor Cache Performance**
   - Track hit rates
   - Alert on rate limit approaching
   - Log cache invalidation events

4. **Batch API Requests**
   - Combine multiple queries into one request
   - Use GraphQL for complex, multi-resource queries
   - Reduce number of upstream API calls

5. **Cache Warm on Startup**
   - Preload frequently-accessed data
   - Avoid cold start cache misses
   - Reduce initial API calls

### ❌ DON'T:

1. **Cache Without TTL**
   - Always set expiration times
   - Avoid indefinite cache staleness

2. **Cache Sensitive Data**
   - Don't cache user tokens or secrets
   - Be careful with user-specific data
   - Respect user privacy in cache keys

3. **Ignore Rate Limit Headers**
   - Always read `X-RateLimit-Remaining`
   - Implement backoff strategies
   - Alert before hitting limits

4. **Cache Everything**
   - Real-time data should have short TTLs
   - Hot paths benefit most from caching
   - Profile first, cache later

5. **Forget Cache Invalidation**
   - Have a clear invalidation strategy
   - Document when caches get cleared
   - Test invalidation logic

---

## 7. Implementation Checklist

- [ ] Add Redis client to dependency injection
- [ ] Create `CacheStrategy` class with TTL constants
- [ ] Implement `cache_get()` and `cache_set()` helpers
- [ ] Add `make_cache_key()` for consistent key generation
- [ ] Wrap frequently-called endpoints with caching
- [ ] Add `X-Cache` headers for visibility
- [ ] Implement cache invalidation for mutation endpoints (POST, PUT, DELETE)
- [ ] Set up cache warming on startup
- [ ] Add cache metrics endpoint
- [ ] Implement rate limit monitoring
- [ ] Add logging for cache operations
- [ ] Test cache TTL expiration
- [ ] Document cache strategy for each endpoint
- [ ] Set up monitoring dashboards for cache hit rate

---

## 8. Example: Complete Cached Endpoint

```python
@router.get("/v1/listings/{listing_id}")
async def get_listing(
    listing_id: UUID,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
) -> ListingResponse:
    """Get a listing by ID with full caching strategy."""
    
    cache_key = f"listing:{listing_id}"
    
    # Step 1: Check Redis cache
    cached = await cache_get(redis_client, cache_key)
    if cached:
        response.headers["X-Cache"] = "HIT"
        response.headers["Cache-Control"] = "public, max-age=300"
        response.headers["ETag"] = f'"{cache_key}"'
        return cached
    
    # Step 2: Query database
    repo = ListingRepository(db)
    listing = await repo.get_by_id(listing_id)
    
    if not listing:
        response.headers["Cache-Control"] = "public, max-age=60"
        raise HTTPException(status_code=404, detail="Listing not found")
    
    # Step 3: Cache result
    listing_dict = ListingResponse.from_orm(listing).dict()
    await cache_set(
        redis_client,
        cache_key,
        listing_dict,
        CacheStrategy.LISTING_TTL
    )
    
    # Step 4: Set response headers
    response.headers["X-Cache"] = "MISS"
    response.headers["Cache-Control"] = "public, max-age=300"
    response.headers["ETag"] = f'"{cache_key}"'
    
    return listing_dict
```

---

## References

- [GitHub REST API Rate Limiting](https://docs.github.com/en/rest/overview/resources-in-the-rest-api?apiVersion=2022-11-28#rate-limiting)
- [GitHub GraphQL API Rate Limiting](https://docs.github.com/en/graphql/overview/rate-limits-and-node-limits)
- [Redis Caching Best Practices](https://redis.io/topics/client-side-caching)
- [HTTP Caching Specifications (RFC 7234)](https://tools.ietf.org/html/rfc7234)
- [FastAPI Response Headers](https://fastapi.tiangolo.com/advanced/response-headers/)
