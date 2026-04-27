from fastapi import APIRouter

from app.api.v1 import (
    applications,
    auth,
    dashboard,
    generation,
    health,
    job_descriptions,
    observability,
    profile,
    resumes,
)

prefix = '/v1'

api_router = APIRouter()
api_router.include_router(health.router, prefix=prefix, tags=["health"])
api_router.include_router(observability.router, prefix=prefix, tags=["observability"])
api_router.include_router(auth.router, prefix=f"{prefix}/auth", tags=["auth"])
api_router.include_router(profile.router, prefix=prefix, tags=["profile"])
api_router.include_router(dashboard.router, prefix=prefix, tags=["dashboard"])
api_router.include_router(applications.router, prefix=prefix, tags=["applications"])
api_router.include_router(resumes.router, prefix=prefix, tags=["resumes"])
api_router.include_router(job_descriptions.router, prefix=prefix, tags=["job_descriptions"])
api_router.include_router(generation.router, prefix=prefix, tags=["generation"])
