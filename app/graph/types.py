# app/graph/types.py
from __future__ import annotations
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class TraceItem(BaseModel):
    node: str = Field(..., description="Node name in the graph")
    ms: int = Field(..., description="Elapsed milliseconds for this node")
    out: Optional[str] = Field(None, description="Policy decision or short status")
    k: Optional[int] = Field(None, description="Top-k used by retrieval")
    hits: Optional[List[Dict[str, Any]]] = None  # compact evidence (title/score/etc.)

class GraphObj(BaseModel):
    trace: List[TraceItem] = Field(default_factory=list)

class Metrics(BaseModel):
    total_ms: int = 0
    node_ms: Dict[str, int] = Field(default_factory=dict)

class DecisionJSON(BaseModel):
    route: str = "assist"                    # assist | crisis | abstain
    answer: str = ""                         # short assistant reply
    graph: GraphObj = Field(default_factory=GraphObj)
    metrics: Metrics = Field(default_factory=Metrics)
