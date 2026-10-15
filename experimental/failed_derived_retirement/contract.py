"""Planning/crash-ledger model only. No filesystem I/O or deletion authority.

A future app-owned adapter must implement HeldScope using real catalog admission,
CAS receipts, native ancestry/file handles and full byte/stream verification.
A caller-authored JSON record or this model's success never authorizes disposal.
"""
from dataclasses import asdict, dataclass, replace
from enum import Enum
from hashlib import sha256
import json
from typing import Protocol


class Refused(ValueError):
    pass


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()


def require_hash(value):
    if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise Refused('Missing or malformed exact receipt digest')


@dataclass(frozen=True)
class NativeFacts:
    # Mirrors native_io.VerifiedFile.facts; content hash and streams are separate
    # same-held-handle observations. No pathname is an identity.
    identity: tuple[int, int, int]
    dev: int
    ino: int
    identity_method: str
    identity_api_error: int
    size: int
    modified: int
    links: int
    attributes: int
    sha256: str
    streams: tuple[str, ...] = ('::$DATA',)

    def validate(self):
        require_hash(self.sha256)
        if len(self.identity) != 3 or any(type(v) is not int or v < 0 for v in self.identity):
            raise Refused('Malformed native identity')
        if not self.identity[0] or not (self.identity[1] or self.identity[2]) or type(self.dev) is not int or self.dev <= 0 or type(self.ino) is not int or self.ino <= 0:
            raise Refused('Zero or ambiguous native identity')
        if self.identity_method not in ('FileIdInfo128', 'BY_HANDLE_FILE_INFORMATION64'):
            raise Refused('Unknown native identity method')
        if self.identity_method == 'FileIdInfo128' and self.identity_api_error != 0:
            raise Refused('Extended identity error')
        if self.identity_method == 'BY_HANDLE_FILE_INFORMATION64' and self.identity_api_error not in (1, 50, 87):
            raise Refused('Unapproved identity fallback')
        if type(self.size) is not int or self.size < 0 or type(self.modified) is not int:
            raise Refused('Malformed exact size/time')
        if type(self.links) is not int or type(self.attributes) is not int or self.attributes < 0 or self.links != 1 or self.attributes & (0x400 | 0x10):
            raise Refused('Aliased, reparse or non-file artifact')
        if self.streams != ('::$DATA',):
            raise Refused('Additional streams preserved')

    @property
    def key(self):
        return self.identity_method, self.dev, self.ino


@dataclass(frozen=True)
class ArtifactReceipt:
    artifact_id: str
    job_id: str
    attempt_id: str
    relative_name: str
    role: str
    facts: NativeFacts
    source_set_sha256: str
    transform_sha256: str
    enrollment_kind: str
    enrollment_sha256: str

    def validate(self):
        self.facts.validate()
        if self.enrollment_sha256 != artifact_enrollment_digest(self):
            raise Refused('Enrollment does not bind exact artifact receipt')
        for value in (self.source_set_sha256, self.transform_sha256, self.enrollment_sha256):
            require_hash(value)
        if not self.artifact_id or not self.relative_name or any(c in self.relative_name for c in '/\\:') or self.relative_name in ('.', '..'):
            raise Refused('Artifact is not a bounded direct owned member')
        if self.role not in ('source_snapshot', 'failed_derived', 'diagnostic'):
            raise Refused('Unknown artifact role')


@dataclass(frozen=True)
class AttemptSnapshot:
    job_id: str
    attempt_id: str
    revision: int
    state: str
    journal_sha256: str
    manifest_sha256: str
    failure_sha256: str
    active_attempts: tuple[str, ...] = ()
    referenced_artifacts: tuple[str, ...] = ()
    publication_intents: tuple[str, ...] = ()
    output_receipts: tuple[str, ...] = ()

    def validate(self):
        for value in (self.journal_sha256, self.manifest_sha256, self.failure_sha256):
            require_hash(value)
        if not self.job_id or not self.attempt_id or type(self.revision) is not int or self.revision < 0:
            raise Refused('Unknown frozen attempt')
        if self.state != 'failed' or self.active_attempts or self.publication_intents or self.output_receipts:
            raise Refused('Attempt is active, nonterminal, publishing or published')


@dataclass(frozen=True)
class EvidenceReceipt:
    failure_sha256: str
    manifest_sha256: str
    source_set_sha256: str
    covered_derived: tuple[tuple[str, str], ...]
    diagnostics: tuple[ArtifactReceipt, ...]
    retain_representatives: tuple[str, ...]
    enrollment_sha256: str


def artifact_enrollment_digest(receipt):
    value = asdict(receipt)
    value.pop('enrollment_sha256')
    return digest({'schema': 'books-failed-derived-artifact-v1', 'receipt': value})


def evidence_enrollment_digest(evidence):
    value = asdict(evidence)
    value.pop('enrollment_sha256')
    return digest({'schema': 'books-failed-derived-evidence-v1', 'receipt': value})


def source_set_digest(sources):
    return digest([(r.artifact_id, asdict(r.facts), r.enrollment_sha256) for r in sources])


class HeldArtifact(Protocol):
    def assert_held(self) -> None: ...
    def facts_and_hash(self) -> NativeFacts: ...


class HeldScope(Protocol):
    # Implementations must own app admission + exact old attempt/CAS scope, not
    # infer ownership from a path, age, journal boolean or terminal UI label.
    def assert_current(self, expected: AttemptSnapshot) -> None: ...
    def assert_enrolled(self, receipt_sha256: str, kind: str) -> None: ...
    def lease(self, receipt: ArtifactReceipt) -> HeldArtifact: ...


@dataclass(frozen=True)
class DiagnosticPlan:
    attempt: AttemptSnapshot
    sources: tuple[ArtifactReceipt, ...]
    derived: tuple[ArtifactReceipt, ...]
    evidence: EvidenceReceipt
    plan_sha256: str


def _verify_lease(scope, receipt, attempt, role):
    receipt.validate()
    if (receipt.job_id, receipt.attempt_id, receipt.role) != (attempt.job_id, attempt.attempt_id, role):
        raise Refused('Receipt escaped frozen job/attempt/role')
    if role == 'failed_derived' and receipt.relative_name not in ('checked.m4b', 'compatible.m4b'):
        raise Refused('Artifact outside this exact two-name derived profile')
    if role == 'failed_derived' and receipt.enrollment_kind not in ('verified-attempt-producer', 'verified-legacy-redundancy'):
        raise Refused('Missing producer or explicit new legacy redundancy enrollment')
    if role == 'source_snapshot' and receipt.enrollment_kind != 'protected-source-snapshot':
        raise Refused('Source is not an enrolled protected snapshot')
    if role == 'diagnostic' and receipt.enrollment_kind != 'retained-failure-evidence':
        raise Refused('Diagnostic is not enrolled retained evidence')
    scope.assert_enrolled(receipt.enrollment_sha256, receipt.enrollment_kind)
    held = scope.lease(receipt)
    held.assert_held()
    if held.facts_and_hash() != receipt.facts:
        raise Refused('Current native identity/bytes/stream/time differ from receipt')
    return held


def plan_retirement(scope: HeldScope, attempt: AttemptSnapshot,
                    sources: tuple[ArtifactReceipt, ...], derived: tuple[ArtifactReceipt, ...],
                    evidence: EvidenceReceipt, *, expected_plan_sha256=None) -> DiagnosticPlan:
    """Freeze a diagnostic plan. Does not dispose, create intent or grant authority."""
    attempt.validate()
    scope.assert_current(attempt)
    if not sources or not derived or not evidence.diagnostics:
        raise Refused('Sources, derived candidates and preserved diagnostics required')
    all_artifacts = sources + derived + evidence.diagnostics
    if len({r.artifact_id for r in all_artifacts}) != len(all_artifacts):
        raise Refused('Duplicate artifact reference')
    if (len({r.facts.key for r in all_artifacts}) != len(all_artifacts)
            or len({r.facts.identity for r in all_artifacts}) != len(all_artifacts)):
        raise Refused('Source/derived/evidence native identities overlap, including mixed identity methods')
    if len({r.relative_name.casefold() for r in all_artifacts}) != len(all_artifacts):
        raise Refused('Owned names collide')
    if any(r.artifact_id in attempt.referenced_artifacts for r in derived):
        raise Refused('Derived artifact still referenced by another attempt/recovery/publication')
    if any(r.artifact_id in evidence.retain_representatives for r in derived):
        raise Refused('Unique failure representative must be preserved')
    source_digest = source_set_digest(sources)
    if evidence.source_set_sha256 != source_digest or any(r.source_set_sha256 != source_digest for r in derived):
        raise Refused('Derived redundancy is not bound to exact preserved source set')
    require_hash(evidence.enrollment_sha256)
    if evidence.enrollment_sha256 != evidence_enrollment_digest(evidence):
        raise Refused('Enrollment does not bind exact failure evidence')
    scope.assert_enrolled(evidence.enrollment_sha256, 'failure-evidence-coverage')
    if (evidence.failure_sha256, evidence.manifest_sha256) != (attempt.failure_sha256, attempt.manifest_sha256):
        raise Refused('Diagnostic coverage differs from frozen failure/manifest')
    if tuple(sorted(evidence.covered_derived)) != tuple(sorted((r.artifact_id, r.facts.sha256) for r in derived)):
        raise Refused('Compact diagnostic evidence does not cover exact discarded bytes')
    held = []
    for role, receipts in (('source_snapshot', sources), ('failed_derived', derived), ('diagnostic', evidence.diagnostics)):
        held.extend(_verify_lease(scope, r, attempt, role) for r in receipts)
    scope.assert_current(attempt)
    for lease in held:
        lease.assert_held()
    value = {'attempt': asdict(attempt), 'sources': [asdict(r) for r in sources],
             'derived': [asdict(r) for r in derived], 'evidence': asdict(evidence)}
    fingerprint = digest(value)
    if expected_plan_sha256 is not None and fingerprint != expected_plan_sha256:
        raise Refused('Expected plan changed')
    return DiagnosticPlan(attempt, sources, derived, evidence, fingerprint)


class State(str, Enum):
    VERIFIED = 'verified'
    INTENDED = 'removal_intended'
    DISPOSITION_SET = 'disposition_set'
    REMOVED = 'removed'
    ABSENT_AFTER_INTENT = 'absent_after_intent'


class Event(str, Enum):
    INTENT_COMMITTED = 'intent_committed'
    DISPOSITION_RECORDED = 'disposition_recorded'
    ABSENCE_CONFIRMED = 'absence_confirmed'
    RECOVERY_ABSENT = 'recovery_absent'
    RECOVERY_PRESENT_EXACT = 'recovery_present_exact'


_TRANSITIONS = {
        (State.VERIFIED, Event.INTENT_COMMITTED): State.INTENDED,
        (State.INTENDED, Event.DISPOSITION_RECORDED): State.DISPOSITION_SET,
        (State.INTENDED, Event.RECOVERY_ABSENT): State.ABSENT_AFTER_INTENT,
        (State.DISPOSITION_SET, Event.ABSENCE_CONFIRMED): State.REMOVED,
        (State.DISPOSITION_SET, Event.RECOVERY_ABSENT): State.REMOVED,
}


@dataclass(frozen=True)
class LedgerRow:
    plan_sha256: str
    enrollment_sha256: str
    artifact_id: str
    state: State = State.VERIFIED
    revision: int = 0
    history: tuple[tuple[str, str], ...] = ()


def ledger_transition(row: LedgerRow, expected: LedgerRow, event: Event) -> LedgerRow:
    """Pure expected-row/CAS history model, not a native observation or delete call.

    Native adapter must supply authenticated disposition/absence observations;
    this function only models receipt states already used by storage_cleanup.
    """
    if row != expected:
        raise Refused('Receipt CAS changed')
    if not isinstance(row.state, State) or type(row.revision) is not int or row.revision < 0 or len(row.history) != row.revision or not row.artifact_id:
        raise Refused('Malformed receipt state/history')
    if not isinstance(row.history, tuple) or row.revision > 3:
        raise Refused('Unbounded or malformed receipt history')
    replay = State.VERIFIED
    for entry in row.history:
        if not isinstance(entry, tuple) or len(entry) != 2 or entry[0] != replay.value:
            raise Refused('Receipt prior-state history changed')
        try:
            historical_event = Event(entry[1])
        except (ValueError, TypeError) as error:
            raise Refused('Unknown receipt history event') from error
        replay = _TRANSITIONS.get((replay, historical_event))
        if replay is None:
            raise Refused('Unsafe receipt history transition')
    if replay != row.state:
        raise Refused('Receipt state differs from full history replay')
    require_hash(row.plan_sha256)
    require_hash(row.enrollment_sha256)
    if event == Event.RECOVERY_PRESENT_EXACT and row.state == State.INTENDED:
        return row  # Preserve intent; fresh full live admission needed before any native retry.
    if event == Event.RECOVERY_ABSENT and row.state in (State.REMOVED, State.ABSENT_AFTER_INTENT):
        return row
    target = _TRANSITIONS.get((row.state, event))
    if target is None:
        raise Refused('Unknown, unsafe or replacement-name transition; preserved')
    return replace(row, state=target, revision=row.revision + 1,
                   history=row.history + ((row.state.value, event.value),))
