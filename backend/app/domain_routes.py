"""
backend.app.domain_routes
=========================
FastAPI router implementing the AI-derived Domain Profile and Blueprint
Compiler API (steering contract v1.1).

Endpoints
---------
POST   /api/domains/derive                  -- derive draft domain profile candidates
GET    /api/domains/{domain_profile_id}     -- fetch a domain profile
PATCH  /api/domains/{domain_profile_id}     -- edit a draft profile (rejected if confirmed)
POST   /api/domains/{domain_profile_id}/confirm -- confirm a draft profile
POST   /api/blueprints/compile              -- compile blueprint (requires confirmed domain)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ui_blueprint.domain.compiler import BlueprintCompileError, compileBlueprintFromMedia
from ui_blueprint.domain.derivation import StubDomainDerivationProvider
from ui_blueprint.domain.ir import (
    CaptureStep,
    DomainProfile,
    ProfileExporter,
    ProfileValidator,
)
from ui_blueprint.domain.ir import DOMAIN_STATUS_CONFIRMED, DOMAIN_STATUS_DRAFT
from ui_blueprint.domain.store import DomainProfileStore, InMemoryDomainProfileStore

router = APIRouter(prefix="/api")

# ---------------------------------------------------------------------------
# Module-level store (replaced per-app in tests via dependency override or
# direct attribute assignment on this module)
# ---------------------------------------------------------------------------

_store: DomainProfileStore = InMemoryDomainProfileStore()


def get_store() -> DomainProfileStore:
    """Return the active DomainProfileStore (overridable in tests)."""
    return _store


def set_store(store: DomainProfileStore) -> None:
    """Replace the active store (for testing or multi-tenant setups)."""
    global _store
    _store = store


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_provider = StubDomainDerivationProvider()


def _now_rfc3339() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_profile(domain_profile_id: str) -> DomainProfile:
    profile = get_store().get(domain_profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Domain profile '{domain_profile_id}' not found")
    return profile


# ---------------------------------------------------------------------------
# POST /api/domains/derive
# ---------------------------------------------------------------------------


@router.post("/domains/derive", status_code=200)
async def derive_domain_profiles(body: dict[str, Any]) -> JSONResponse:
    """
    Derive one or more draft DomainProfile candidates from media input.

    Request body::

        {
          "media": {
            "media_id": "vid_001",
            "media_type": "video",
            "uri": "...",        // optional
            "metadata": {}       // optional
          },
          "options": {
            "max_candidates": 3, // optional, default 3
            "hint": "cabinet drawer assembly"  // optional free-text hint
          }
        }

    The returned candidates are persisted as draft profiles.
    No profile is auto-confirmed.
    """
    media: dict[str, Any] = body.get("media", {})
    options: dict[str, Any] = body.get("options", {})

    media_id: str = media.get("media_id", "unknown")
    hint: str = options.get("hint", "")
    max_candidates: int = int(options.get("max_candidates", 3))

    # Build the media_input dict that the derivation provider expects.
    media_input: dict[str, Any] = {
        "media_id": media_id,
        "media_type": media.get("media_type", "other"),
        "hint": hint,
        "metadata": media.get("metadata", {}),
    }

    candidates = _provider.derive(media_input, max_candidates=max_candidates)

    # Persist each candidate as a draft.
    store = get_store()
    for profile in candidates:
        store.save(profile)

    warnings: list[str] = []
    if not hint:
        warnings.append(
            "No hint provided; results may be less accurate. "
            "Pass 'options.hint' with a brief description of the media content."
        )

    return JSONResponse(
        content={
            "candidates": [
                {
                    "domain_profile_id": p.id,
                    "status": p.status,
                    "name": p.name,
                    "schema_version": p.schema_version,
                    "summary": p.notes,
                }
                for p in candidates
            ],
            "warnings": warnings,
        }
    )


# ---------------------------------------------------------------------------
# GET /api/domains/{domain_profile_id}
# ---------------------------------------------------------------------------


@router.get("/domains/{domain_profile_id}", status_code=200)
def get_domain_profile(domain_profile_id: str) -> JSONResponse:
    """Return the full DomainProfile for the given id."""
    profile = _require_profile(domain_profile_id)
    return JSONResponse(content={"domain_profile": profile.to_dict()})


# ---------------------------------------------------------------------------
# PATCH /api/domains/{domain_profile_id}
# ---------------------------------------------------------------------------


@router.patch("/domains/{domain_profile_id}", status_code=200)
async def patch_domain_profile(domain_profile_id: str, body: dict[str, Any]) -> JSONResponse:
    """
    Edit a draft DomainProfile.

    Rejected with 409 if the profile is not in ``draft`` status.

    Request body::

        {
          "patch": {
            "name": "...",             // optional
            "capture_protocol": [...], // optional
            "validators": [...],       // optional
            "exporters": [...],        // optional
            "notes": "..."             // optional
          }
        }
    """
    profile = _require_profile(domain_profile_id)

    if profile.status != DOMAIN_STATUS_DRAFT:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Domain profile '{domain_profile_id}' has status '{profile.status}' "
                "and cannot be edited.  Create a new draft to make changes."
            ),
        )

    patch: dict[str, Any] = body.get("patch", {})

    if "name" in patch:
        profile.name = str(patch["name"])
    if "notes" in patch:
        profile.notes = str(patch["notes"])
    if "capture_protocol" in patch:
        profile.capture_protocol = [CaptureStep.from_dict(s) for s in patch["capture_protocol"]]
    if "validators" in patch:
        profile.validators = [ProfileValidator.from_dict(v) for v in patch["validators"]]
    if "exporters" in patch:
        profile.exporters = [ProfileExporter.from_dict(e) for e in patch["exporters"]]

    profile.updated_at = _now_rfc3339()
    get_store().save(profile)

    return JSONResponse(content={"domain_profile": profile.to_dict()})


# ---------------------------------------------------------------------------
# POST /api/domains/{domain_profile_id}/confirm
# ---------------------------------------------------------------------------


@router.post("/domains/{domain_profile_id}/confirm", status_code=200)
async def confirm_domain_profile(domain_profile_id: str, body: dict[str, Any]) -> JSONResponse:
    """
    Confirm a draft DomainProfile, making it immutable and ready for compile.

    Once confirmed, PATCH requests will be rejected (409).

    Request body::

        {
          "confirmed_by": "alice",  // optional
          "note": "LGTM"            // optional
        }
    """
    profile = _require_profile(domain_profile_id)

    if profile.status == DOMAIN_STATUS_CONFIRMED:
        # Idempotent — already confirmed, return current state.
        return JSONResponse(
            content={
                "domain_profile": {
                    "id": profile.id,
                    "status": profile.status,
                    "schema_version": profile.schema_version,
                    "updated_at": profile.updated_at,
                }
            }
        )

    if profile.status != DOMAIN_STATUS_DRAFT:
        raise HTTPException(
            status_code=409,
            detail=f"Profile '{domain_profile_id}' has status '{profile.status}' and cannot be confirmed.",
        )

    confirmed_by: str = body.get("confirmed_by", "")
    note: str = body.get("note", "")

    profile.status = DOMAIN_STATUS_CONFIRMED
    profile.updated_at = _now_rfc3339()
    if confirmed_by or note:
        existing = profile.notes or ""
        addendum = f"Confirmed by: {confirmed_by}. {note}".strip()
        profile.notes = f"{existing}\n{addendum}".strip() if existing else addendum

    get_store().save(profile)

    return JSONResponse(
        content={
            "domain_profile": {
                "id": profile.id,
                "status": profile.status,
                "schema_version": profile.schema_version,
                "updated_at": profile.updated_at,
            }
        }
    )


# ---------------------------------------------------------------------------
# POST /api/blueprints/compile
# ---------------------------------------------------------------------------


@router.post("/blueprints/compile", status_code=200)
async def compile_blueprint(body: dict[str, Any]) -> JSONResponse:
    """
    Compile a BlueprintIR from media + a confirmed DomainProfile.

    Request body::

        {
          "media": {
            "media_id": "vid_001",
            "media_type": "video",
            "uri": "...",       // optional
            "metadata": {}      // optional
          },
          "domain_profile_id": "<uuid>"
        }

    Returns ``400`` if *domain_profile_id* is absent or the profile is not
    confirmed.  Returns ``404`` if the profile is not found.
    """
    domain_profile_id: str | None = body.get("domain_profile_id")
    if not domain_profile_id:
        raise HTTPException(
            status_code=400,
            detail="'domain_profile_id' is required.  Derive a domain profile, confirm it, then compile.",
        )

    profile = _require_profile(domain_profile_id)

    media: dict[str, Any] = body.get("media", {})

    try:
        blueprint = compileBlueprintFromMedia(media=media, confirmed_domain_profile=profile)
    except BlueprintCompileError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return JSONResponse(content={"blueprint": blueprint.to_dict()})
