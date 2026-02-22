from fastapi import FastAPI
from fastapi.responses import JSONResponse

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.rate_limit import RateLimitMiddleware

app = FastAPI(
    title="InvisID API",
    description="Leak Attribution System for Sensitive Images",
    version="1.0.0",
)

# Add security headers
app.add_middleware(SecurityHeadersMiddleware)

# Add rate limiting
app.add_middleware(RateLimitMiddleware)


@app.get("/")
async def root():
    return {"message": "InvisID API", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
