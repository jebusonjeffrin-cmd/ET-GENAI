from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_graph_store

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/equipment/{tag}")
async def equipment_360(tag: str, graph_store=Depends(get_graph_store)) -> dict:
    return graph_store.get_equipment_360(tag)


@router.get("/stats")
async def graph_stats(graph_store=Depends(get_graph_store)) -> dict:
    return graph_store.stats()
