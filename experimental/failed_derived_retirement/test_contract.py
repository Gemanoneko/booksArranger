"""Unexecuted in-memory scenarios. Fake leases are NOT native evidence."""
from dataclasses import replace
import unittest
from contract import (ArtifactReceipt, AttemptSnapshot, EvidenceReceipt, Event,
    LedgerRow, NativeFacts, Refused, State, artifact_enrollment_digest, digest,
    evidence_enrollment_digest, ledger_transition, plan_retirement, source_set_digest)


def h(value):
    return digest(value)


def enroll(receipt):
    return replace(receipt, enrollment_sha256=artifact_enrollment_digest(receipt))


def evidence_enroll(receipt):
    return replace(receipt, enrollment_sha256=evidence_enrollment_digest(receipt))


class FakeLease:
    def __init__(self, facts):
        self.facts, self.open = facts, True

    def assert_held(self):
        if not self.open:
            raise Refused('Fixture lease closed')

    def facts_and_hash(self):
        self.assert_held()
        return self.facts


class FakeScope:
    def __init__(self, attempt, receipts, evidence):
        self.current = attempt
        self.leases = {r.artifact_id: FakeLease(r.facts) for r in receipts}
        self.enrolled = {r.enrollment_sha256: r.enrollment_kind for r in receipts}
        self.enrolled[evidence.enrollment_sha256] = 'failure-evidence-coverage'
        self.calls = 0
        self.change_on_second_read = False

    def assert_current(self, expected):
        self.calls += 1
        if self.change_on_second_read and self.calls > 1:
            self.current = replace(self.current, revision=self.current.revision + 1)
        if self.current != expected:
            raise Refused('Fixture app admission/revision changed')

    def assert_enrolled(self, receipt_sha256, kind):
        if self.enrolled.get(receipt_sha256) != kind:
            raise Refused('No authenticated fixture enrollment')

    def lease(self, receipt):
        if receipt.artifact_id not in self.leases:
            raise Refused('No held fixture artifact')
        return self.leases[receipt.artifact_id]


class PlanningScenarios(unittest.TestCase):
    def setUp(self):
        self.attempt = AttemptSnapshot('job-A', 'attempt-A', 4, 'failed', h('journal'), h('manifest'), h('failure'))
        def make(name, index, role, kind, source_set):
            facts = NativeFacts((7, 0, index), 7, index, 'FileIdInfo128', 0,
                                index * 10, 123456789, 1, 0x20, h(name))
            return enroll(ArtifactReceipt(name, 'job-A', 'attempt-A', name, role,
                          facts, source_set, h('transform-revision'), kind, h('placeholder')))
        self.source = make('source00000.m4b', 1, 'source_snapshot', 'protected-source-snapshot', h('source-receipt-origin'))
        source_set = source_set_digest((self.source,))
        self.checked = make('checked.m4b', 2, 'failed_derived', 'verified-attempt-producer', source_set)
        self.compatible = make('compatible.m4b', 3, 'failed_derived', 'verified-legacy-redundancy', source_set)
        self.diagnostic = make('diagnostic-receipt.json', 4, 'diagnostic', 'retained-failure-evidence', source_set)
        self.sources = (self.source,)
        self.derived = (self.checked, self.compatible)
        self.evidence = evidence_enroll(EvidenceReceipt(self.attempt.failure_sha256,
            self.attempt.manifest_sha256, source_set,
            tuple((r.artifact_id, r.facts.sha256) for r in self.derived),
            (self.diagnostic,), (), h('placeholder')))
        self.reset_scope()

    def reset_scope(self):
        self.scope = FakeScope(self.attempt, self.sources + self.derived + self.evidence.diagnostics, self.evidence)

    def plan(self, **kwargs):
        return plan_retirement(self.scope, self.attempt, self.sources, self.derived, self.evidence, **kwargs)

    def test_two_derived_plan_preserves_source_diagnostics_and_old_attempt(self):
        old = self.attempt
        result = self.plan()
        self.assertEqual(tuple(r.artifact_id for r in result.derived), ('checked.m4b', 'compatible.m4b'))
        self.assertEqual(result.sources, (self.source,))
        self.assertEqual(result.evidence.diagnostics, (self.diagnostic,))
        self.assertIs(self.attempt, old)
        self.assertTrue(all(lease.open for lease in self.scope.leases.values()))
        self.assertFalse(hasattr(result, 'dispose'))

    def test_exact_plan_roundtrip_and_changed_plan_refusal(self):
        result = self.plan()
        self.assertEqual(self.plan(expected_plan_sha256=result.plan_sha256), result)
        with self.assertRaises(Refused):
            self.plan(expected_plan_sha256=h('different-plan'))

    def test_active_published_nonterminal_intent_and_reference_refuse(self):
        original = self.attempt
        for changes in ({'state': 'running'}, {'state': 'completed'},
                        {'active_attempts': ('new-attempt',)},
                        {'publication_intents': ('intent',)}, {'output_receipts': ('output',)},
                        {'referenced_artifacts': (self.checked.artifact_id,)}):
            with self.subTest(changes=changes):
                self.attempt = replace(original, **changes)
                self.reset_scope()
                with self.assertRaises(Refused):
                    self.plan()
        self.attempt = original

    def test_unknown_enrollment_refuses_without_filename_inference(self):
        self.scope.enrolled.clear()
        with self.assertRaises(Refused):
            self.plan()

    def test_copied_enrollment_digest_cannot_authorize_different_payload(self):
        self.derived = (replace(self.checked, transform_sha256=h('changed-code')), self.compatible)
        with self.assertRaises(Refused):
            self.plan()

    def test_historical_name_or_current_hash_is_not_producer_enrollment(self):
        unknown = enroll(replace(self.checked, enrollment_kind='filename-and-current-hash'))
        self.derived = (unknown, self.compatible)
        self.evidence = evidence_enroll(replace(self.evidence,
            covered_derived=tuple((r.artifact_id, r.facts.sha256) for r in self.derived)))
        self.reset_scope()
        with self.assertRaises(Refused):
            self.plan()

    def test_changed_source_bytes_identity_or_closed_lease_refuse(self):
        for facts in (replace(self.source.facts, sha256=h('changed')),
                      replace(self.source.facts, ino=999), replace(self.source.facts, size=999)):
            with self.subTest(facts=facts):
                self.reset_scope()
                self.scope.leases[self.source.artifact_id].facts = facts
                with self.assertRaises(Refused):
                    self.plan()
        self.reset_scope()
        self.scope.leases[self.source.artifact_id].open = False
        with self.assertRaises(Refused):
            self.plan()

    def test_changed_derived_native_id_or_bytes_refuse(self):
        for facts in (replace(self.checked.facts, ino=999),
                      replace(self.checked.facts, sha256=h('changed'))):
            with self.subTest(facts=facts):
                self.reset_scope()
                self.scope.leases[self.checked.artifact_id].facts = facts
                with self.assertRaises(Refused):
                    self.plan()

    def test_extra_stream_alias_reparse_and_zero_identity_refuse(self):
        for facts in (replace(self.checked.facts, streams=('::$DATA', ':Zone.Identifier:$DATA')),
                      replace(self.checked.facts, links=2), replace(self.checked.facts, attributes=0x400),
                      replace(self.checked.facts, dev=0), replace(self.checked.facts, identity=(0, 0, 0))):
            with self.subTest(facts=facts):
                original = self.derived
                self.derived = (enroll(replace(self.checked, facts=facts)), self.compatible)
                self.reset_scope()
                with self.assertRaises(Refused):
                    self.plan()
                self.derived = original

    def test_source_target_identity_overlap_refuses(self):
        self.derived = (enroll(replace(self.checked, facts=self.source.facts)), self.compatible)
        self.reset_scope()
        with self.assertRaises(Refused):
            self.plan()

    def test_mixed_identity_methods_cannot_hide_same_legacy_file_id(self):
        facts = replace(self.checked.facts, identity=self.source.facts.identity, dev=7, ino=1,
                        identity_method='BY_HANDLE_FILE_INFORMATION64', identity_api_error=50)
        self.derived = (enroll(replace(self.checked, facts=facts)), self.compatible)
        self.reset_scope()
        with self.assertRaises(Refused):
            self.plan()

    def test_unique_failure_representative_is_not_retired(self):
        self.evidence = evidence_enroll(replace(self.evidence,
            retain_representatives=(self.checked.artifact_id,)))
        self.reset_scope()
        with self.assertRaises(Refused):
            self.plan()

    def test_missing_or_changed_diagnostic_coverage_refuses(self):
        for changes in ({'covered_derived': ()}, {'failure_sha256': h('other-failure')},
                        {'manifest_sha256': h('other-manifest')}, {'diagnostics': ()},
                        {'source_set_sha256': h('different-source')}):
            with self.subTest(changes=changes):
                original = self.evidence
                self.evidence = evidence_enroll(replace(original, **changes))
                self.reset_scope()
                with self.assertRaises(Refused):
                    self.plan()
                self.evidence = original

    def test_attempt_revision_changes_during_planning_refuse(self):
        self.scope.change_on_second_read = True
        with self.assertRaises(Refused):
            self.plan()

    def test_boolean_json_is_not_a_live_scope(self):
        with self.assertRaises(AttributeError):
            plan_retirement({'safe': True}, self.attempt, self.sources, self.derived, self.evidence)


class CrashLedgerScenarios(unittest.TestCase):
    def setUp(self):
        self.row = LedgerRow(h('plan'), h('enrollment'), 'checked.m4b')

    def test_normal_intent_disposition_absence_preserves_history(self):
        intent = ledger_transition(self.row, self.row, Event.INTENT_COMMITTED)
        disposition = ledger_transition(intent, intent, Event.DISPOSITION_RECORDED)
        removed = ledger_transition(disposition, disposition, Event.ABSENCE_CONFIRMED)
        self.assertEqual(removed.state, State.REMOVED)
        self.assertEqual(removed.revision, 3)
        self.assertEqual(len(removed.history), 3)
        self.assertEqual(self.row.state, State.VERIFIED)
        self.assertEqual(self.row.history, ())

    def test_missing_without_intent_is_not_removed(self):
        with self.assertRaises(Refused):
            ledger_transition(self.row, self.row, Event.RECOVERY_ABSENT)

    def test_crash_after_intent_absence_is_uncertain_not_disposition_proof(self):
        intent = ledger_transition(self.row, self.row, Event.INTENT_COMMITTED)
        uncertain = ledger_transition(intent, intent, Event.RECOVERY_ABSENT)
        self.assertEqual(uncertain.state, State.ABSENT_AFTER_INTENT)
        self.assertEqual(ledger_transition(uncertain, uncertain, Event.RECOVERY_ABSENT), uncertain)

    def test_crash_after_disposition_receipt_absence_completes(self):
        intent = ledger_transition(self.row, self.row, Event.INTENT_COMMITTED)
        disposition = ledger_transition(intent, intent, Event.DISPOSITION_RECORDED)
        self.assertEqual(ledger_transition(disposition, disposition, Event.RECOVERY_ABSENT).state, State.REMOVED)

    def test_intent_exact_present_requires_fresh_admission(self):
        intent = ledger_transition(self.row, self.row, Event.INTENT_COMMITTED)
        self.assertEqual(ledger_transition(intent, intent, Event.RECOVERY_PRESENT_EXACT), intent)

    def test_terminal_name_replacement_and_disposition_still_present_refuse(self):
        intent = ledger_transition(self.row, self.row, Event.INTENT_COMMITTED)
        disposition = ledger_transition(intent, intent, Event.DISPOSITION_RECORDED)
        removed = ledger_transition(disposition, disposition, Event.ABSENCE_CONFIRMED)
        uncertain = ledger_transition(intent, intent, Event.RECOVERY_ABSENT)
        for row in (disposition, removed, uncertain):
            with self.subTest(state=row.state), self.assertRaisesRegex(Refused, 'replacement-name transition'):
                ledger_transition(row, row, Event.RECOVERY_PRESENT_EXACT)

    def test_changed_receipt_cas_cannot_advance_or_lose_old_history(self):
        current = replace(self.row, revision=1)
        with self.assertRaises(Refused):
            ledger_transition(current, self.row, Event.INTENT_COMMITTED)
        self.assertEqual(current.history, ())

    def test_terminal_or_inconsistent_history_cannot_endorse_absence(self):
        rows = (replace(self.row, state=State.REMOVED),
                replace(self.row, state=State.INTENDED, revision=1,
                        history=(('verified', 'disposition_recorded'),)),
                replace(self.row, state=State.INTENDED, revision=1,
                        history=(('removal_intended', 'intent_committed'),)),
                replace(self.row, state=State.REMOVED, revision=1,
                        history=(('verified', 'intent_committed'),)))
        for row in rows:
            with self.subTest(row=row), self.assertRaises(Refused):
                ledger_transition(row, row, Event.RECOVERY_ABSENT)

    def test_no_direct_verified_to_removed_or_disposition_transition(self):
        for event in (Event.ABSENCE_CONFIRMED, Event.DISPOSITION_RECORDED):
            with self.subTest(event=event), self.assertRaises(Refused):
                ledger_transition(self.row, self.row, event)


if __name__ == '__main__':
    unittest.main()
