"""Dashboard analytics API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from schemas import (
    CostOverviewOut,
    ModelDistributionOut,
    ModelDistributionItem,
    RecentRoutesOut,
    RecentRouteItem,
    CostTrendOut,
    CostTrendPoint,
)
from services.analytics import (
    get_cost_overview,
    get_model_distribution,
    get_recent_routes,
    get_cost_trend,
)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/overview", response_model=CostOverviewOut)
def overview(db: Session = Depends(get_db)):
    """Get cost overview stats."""
    data = get_cost_overview(db)
    return CostOverviewOut(**data)


@router.get("/model-distribution", response_model=ModelDistributionOut)
def model_distribution(db: Session = Depends(get_db)):
    """Get model usage distribution for pie chart."""
    items = get_model_distribution(db)
    return ModelDistributionOut(
        items=[ModelDistributionItem(**it) for it in items]
    )


@router.get("/recent-routes", response_model=RecentRoutesOut)
def recent_routes(limit: int = Query(default=20, le=100), db: Session = Depends(get_db)):
    """Get recent routing decisions."""
    items = get_recent_routes(db, limit=limit)
    return RecentRoutesOut(
        items=[RecentRouteItem(**it) for it in items]
    )


@router.get("/cost-trend", response_model=CostTrendOut)
def cost_trend(days: int = Query(default=7, le=90), db: Session = Depends(get_db)):
    """Get daily cost trend."""
    points = get_cost_trend(db, days=days)
    return CostTrendOut(
        points=[CostTrendPoint(**p) for p in points]
    )
