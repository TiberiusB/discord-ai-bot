"""Lightweight dataclasses / typed structures shared across services.

These mirror the SQLite rows (spec §4) but keep the service layer decoupled
from raw ``sqlite3.Row`` objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Surface = Literal["salon", "dm"]
VolioKind = Literal["search", "interest", "talent", "offer", "request", "placement"]
Visibility = Literal["private", "network", "public"]
EntityKind = Literal["enterprise", "quest", "mission", "event", "place", "idea"]
RsvpStatus = Literal["invited", "accepted", "declined"]
VoteChoice = Literal["yes", "no", "abstain"]


@dataclass
class DiscordMessageSnapshot:
    """A message captured from Discord for the community-memory log."""

    guild_id: str | None
    channel_id: str
    user_id: str
    user_name: str | None
    is_dm: bool
    content: str
    created_at: str


@dataclass
class Trammer:
    discord_user_id: str
    display_name: str | None = None
    locale: str = "fr"
    sponsor_id: str | None = None
    trust_score: float = 0.0
    hop_balance: float = 0.0
    is_tramicien: bool = False
    created_at: str | None = None
    updated_at: str | None = None


@dataclass
class Volio:
    id: int
    trammer_id: str
    kind: str
    label: str
    details: str | None = None
    visibility: str = "network"
    active: bool = True
    created_at: str | None = None


@dataclass
class Echo:
    id: int
    trammer_id: str
    source_id: str | None
    match_type: str
    summary: str
    read: bool = False
    created_at: str | None = None


@dataclass
class ProposedMatch:
    trammer_id: str
    other_id: str
    match_type: str
    score: float
    rationale: str


@dataclass
class Entity:
    id: str
    kind: str
    owner_id: str
    title: str
    description: str | None = None
    phase: str = "draft"
    transparency: float = 0.5
    hop_requested: float = 0.0
    hop_allocated: float = 0.0
    location: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None


@dataclass
class Event:
    id: str
    organizer_id: str
    title: str
    starts_at: str | None = None
    duration_min: int | None = None
    location: str | None = None
    min_attendees: int = 1
    max_attendees: int | None = None
    status: str = "proposed"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None


@dataclass
class Team:
    id: str
    name: str | None
    member_ids: list[str] = field(default_factory=list)
    created_at: str | None = None


@dataclass
class GameWeek:
    week_id: str
    starts_at: str
    invest_end: str
    hop_created: float = 0.0
    growth_factor: float = 1.20
    influence_min: float = 5.0
    influence_max: float = 100.0
    aum_per_trammer: float = 5.0
    status: str = "open"


@dataclass
class Placement:
    week_id: str
    trammer_id: str
    entity_id: str
    hop_amount: float
    placed_at: str | None = None


@dataclass
class Vote:
    id: str
    title: str
    description: str | None
    threshold: float
    created_by: str
    status: str = "open"
    closes_at: str | None = None
    created_at: str | None = None


@dataclass
class RetrievalChunk:
    text: str
    source: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GroundedAnswer:
    answer: str
    sources: list[RetrievalChunk] = field(default_factory=list)


@dataclass
class Summary:
    title: str
    body: str
    message_count: int = 0
    period: str | None = None
