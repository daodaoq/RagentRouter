"""Route rule CRUD API."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import RouteRule, gen_id
from schemas import RuleIn, RuleOut, RuleUpdateIn

router = APIRouter(prefix="/api/rules", tags=["Rules"])


@router.get("/", response_model=list[RuleOut])
def list_rules(db: Session = Depends(get_db)):
    """List all routing rules, ordered by priority."""
    rules = db.query(RouteRule).order_by(RouteRule.priority.desc()).all()
    return [RuleOut.model_validate(r) for r in rules]


@router.post("/", response_model=RuleOut, status_code=201)
def create_rule(body: RuleIn, db: Session = Depends(get_db)):
    """Create a new routing rule."""
    rule = RouteRule(
        id=gen_id(),
        name=body.name,
        description=body.description,
        keywords=body.keywords,
        target_model=body.target_model,
        priority=body.priority,
        enabled=1 if body.enabled else 0,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return RuleOut.model_validate(rule)


@router.put("/{rule_id}", response_model=RuleOut)
def update_rule(rule_id: str, body: RuleUpdateIn, db: Session = Depends(get_db)):
    """Update an existing routing rule."""
    rule = db.query(RouteRule).filter(RouteRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    update_data = body.model_dump(exclude_unset=True)
    if "enabled" in update_data:
        update_data["enabled"] = 1 if update_data["enabled"] else 0

    for key, value in update_data.items():
        setattr(rule, key, value)

    db.commit()
    db.refresh(rule)
    return RuleOut.model_validate(rule)


@router.delete("/{rule_id}", status_code=204)
def delete_rule(rule_id: str, db: Session = Depends(get_db)):
    """Delete a routing rule."""
    rule = db.query(RouteRule).filter(RouteRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()
