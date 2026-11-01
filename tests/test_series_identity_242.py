"""0.24.2 identity regressions: private metadata only; no network/media/database reads."""
import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import local_identity
import part_sets
from organization import plan
from public_research import PublicResearch, attach_shared_routing, retained_gap_fields

EVIDENCE = Path(__file__).resolve().parents[1] / 'Docs' / 'BooksArranger_DiagnosisEvidence_2026-11-01.json'


def saved_tolkien(number='2'):
    evidence = json.loads(EVIDENCE.read_text(encoding='utf-8'))
    saved = next(value for value in evidence['series_groups'] if (value.get('result') or {}).get('review', {}).get('number') == number)
    result = copy.deepcopy(saved['result'])
    row = {'id': saved['id'], 'revision': saved['revision'], 'fingerprint': result['metadata_facts']['source_fingerprint'],
           'members': copy.deepcopy(saved['evidence']['members']), 'metadata': copy.deepcopy(saved['evidence']['metadata'])}
    for index, member in enumerate(row['members']):
        member['path'] = os.path.abspath('synthetic-source/book/part-' + str(index + 1) + '.m4b')
        member['filename'] = Path(member['path']).name
    summary = result['metadata_facts']['local_agreement']
    local = {'version': summary['version'], 'fields': {name: copy.deepcopy(summary[name]) for name in ('title', 'author', 'series', 'number')},
             'gaps': list(summary['gaps']), 'series': None, 'route': None, 'part_book': None, 'accepted': True, 'ignored': [], 'conflicts': []}
    envelope = {'candidate_id': row['id'], 'revision': row['revision'], 'fingerprint': row['fingerprint'], 'result': result}
    return row, local, envelope


class CacheOnlyResearch(PublicResearch):
    def __init__(self, local):
        self.local = local
    def identity(self, row, root):
        return copy.deepcopy(self.local), None
    def with_names(self, row, root, local, typed=None):
        if typed:
            local['names'] = dict(typed)
            if 'series' in typed or 'number' in typed:
                local['series'] = {'name': typed.get('series', ''), 'number': typed.get('number', ''), 'provider': 'entered'} if typed.get('series') and typed.get('number') else None
        return local
    def rules(self):
        return None
    def _gap_fill(self, *args, **kwargs):
        return {'closed': [], 'unfilled': ['original_title', 'series']}


class RetainedResearchTests(unittest.TestCase):
    def test_real_tolkien_receipts_survive_empty_http_cache(self):
        for number, title in [('2', 'The Two Towers'), ('3', 'The Return of the King')]:
            with self.subTest(number=number):
                row, local, saved = saved_tolkien(number)
                fields = retained_gap_fields(row, local, saved)
                self.assertEqual(fields['catalog']['original_title'], title)
                self.assertEqual(fields['series']['name'], 'Властелин колец')
                self.assertEqual(fields['series']['number'], number)
                research = CacheOnlyResearch(local)
                result = research.approved(row, os.path.abspath('synthetic-source'), retained=saved)
                self.assertEqual(result['review']['title'], title)
                self.assertEqual(result['review']['series'], 'Властелин колец')
                self.assertEqual(result['review']['number'], number)
                self.assertEqual(result['review']['universe'], 'Middle-earth')
                self.assertEqual(result['work']['id'], saved['result']['work']['id'])
                self.assertEqual(plan(os.path.abspath('synthetic-output'), result['review'], facts=result['metadata_facts']),
                                 plan(os.path.abspath('synthetic-output'), research.approved(row, os.path.abspath('synthetic-source'), retained=saved)['review'], facts=result['metadata_facts']))

    def test_stale_candidate_revision_source_or_policy_is_not_reused(self):
        row, local, saved = saved_tolkien()
        for key, value in [('candidate_id', 'other'), ('revision', 2), ('fingerprint', 'changed')]:
            with self.subTest(key=key):
                self.assertIsNone(retained_gap_fields(row, local, dict(saved, **{key: value})))
        saved['result']['research_version'] = 'obsolete'
        self.assertIsNone(retained_gap_fields(row, local, saved))

    def test_conflicting_work_receipt_and_missing_author_credit_are_rejected(self):
        for change in ('work', 'receipt', 'authors', 'hold'):
            row, local, saved = saved_tolkien()
            if change == 'work': saved['result']['work']['id'] = 'fantlab:99999'
            if change == 'receipt': saved['result']['sources'][1]['url'] = 'https://fantlab.ru/work99999'
            if change == 'authors': saved['result']['metadata_facts']['authors'] = ['Another Writer']
            if change == 'hold': saved['result']['identity_hold'] = {'kind': 'author_unclear'}
            with self.subTest(change=change):
                self.assertIsNone(retained_gap_fields(row, local, saved))

    def test_changed_saved_names_digest_requires_new_identity(self):
        row, local, saved = saved_tolkien()
        local['names_digest'] = 'new-saved-names'
        self.assertIsNone(retained_gap_fields(row, local, saved))

    def test_current_series_conflict_is_not_filled_from_old_evidence(self):
        row, local, saved = saved_tolkien()
        local['series'] = {'name': 'Властелин колец', 'number': '4'}
        self.assertIsNone(retained_gap_fields(row, local, saved))

    def test_typed_title_wins_but_keeps_confirmed_series(self):
        row, local, saved = saved_tolkien()
        result = CacheOnlyResearch(local).approved(row, os.path.abspath('synthetic-source'), title='My title', retained=saved)
        self.assertEqual(result['review']['title'], 'My title')
        self.assertEqual(result['review']['number'], '2')

    def test_typed_series_and_explicit_empty_universe_win(self):
        row, local, saved = saved_tolkien()
        result = CacheOnlyResearch(local).approved(row, os.path.abspath('synthetic-source'), names={'series': 'My cycle', 'number': '7', 'universe': ''}, retained=saved)
        self.assertEqual(result['review']['title'], 'The Two Towers')
        self.assertEqual((result['review']['series'], result['review']['number'], result['review'].get('universe')), ('My cycle', '7', ''))

    def test_changed_rules_disable_retained_evidence(self):
        row, local, saved = saved_tolkien()
        research = CacheOnlyResearch(local)
        class Rules:
            def changed_for(self, result): return True
            def same_as(self, *args): return ''
        with patch.object(research, 'rules', return_value=Rules()), patch.object(research, '_local_lookup', return_value={'review': None}) as lookup:
            research.approved(row, os.path.abspath('synthetic-source'), retained=saved)
        self.assertIsNone(lookup.call_args.kwargs['retained_fields'])


class CorbettAndQueenTests(unittest.TestCase):
    def book(self, title, number, series='МЭТЬЮ КОРБЕТТ', author='Robert R. McCammon'):
        root = os.path.abspath('synthetic-source')
        path = os.path.join(root, author, series, number + '. ' + title, 'Part 1.m4b')
        return root, {'members': [{'path': path, 'metadata': {'tags': {'album': title, 'album_artist': 'МакКаммон Роберт'}}}]}

    def queen(self):
        root, row = self.book('Королева Бедлама', '2')
        parent = Path(row['members'][0]['path']).parent
        row['members'] = [{'path': str(parent / ('Часть ' + str(n) + '. ' + title + '.m4b')),
                           'metadata': {'tags': {'album': 'Королева Бедлама', 'album_artist': 'МакКаммон Роберт',
                                                'composer': 'Князев Игорь', 'track': str(n) + '/4'}}}
                          for n, title in enumerate(('Маскер', 'Безумие', 'Послание', 'Методы убийства'), 1)]
        return row

    def test_two_confirmed_eponymous_series_books_and_ordinals(self):
        for title, number in [('Голос ночной птицы', '1'), ('Королева Бедлама', '2')]:
            root, row = self.book(title, number)
            found = local_identity.folder_structure(row, root)
            self.assertEqual((found['series'], found['position']), ('Matthew Corbett', number))

    def test_person_alias_unrelated_book_and_wrong_ordinal_keep_veto(self):
        for title, number, series, author in [('Голос ночной птицы', '1', 'Роберт МакКаммон', 'Robert R. McCammon'),
                                               ('Unrelated book', '1', 'Matthew Corbett', 'Robert R. McCammon'),
                                               ('Королева Бедлама', '1', 'Matthew Corbett', 'Robert R. McCammon'),
                                               ('Голос ночной птицы', '1', 'Matthew Corbett', 'Other Writer')]:
            root, row = self.book(title, number, series, author)
            self.assertIsNone(local_identity.folder_structure(row, root))

    def test_confirmed_queen_section_set_asks_with_all_four_paths_in_order(self):
        row = self.queen(); row['members'].reverse()
        found = part_sets.confirmed_edition(row)
        self.assertEqual((found['decision'], found['basis'], found['parts']), ('ask', 'confirmed_internal_sections', 4))
        self.assertIn('Часть 1. Маскер', found['ordered_paths'][0])
        with patch('part_sets.read_chapters', side_effect=AssertionError('Unexpected audio read')):
            row['part_set'] = {'version': 'fixture'}
            self.assertEqual(PublicResearch._part_set(object(), row, os.path.abspath('synthetic-source'), None), found)

    def test_queen_missing_foreign_credits_mixed_folders_or_explicit_keep_refuse(self):
        for change in ('missing', 'wrong_author', 'wrong_album', 'wrong_section', 'other_folder', 'keep', 'duplicate'):
            row = self.queen()
            if change == 'missing': row['members'].pop()
            if change == 'wrong_author': row['members'][0]['metadata']['tags']['album_artist'] = 'Igor Knyazev'
            if change == 'wrong_album': row['members'][0]['metadata']['tags']['album'] = 'Other novel'
            if change == 'wrong_section': row['members'][0]['path'] = row['members'][0]['path'].replace('Маскер', 'Another work')
            if change == 'other_folder': row['members'][0]['path'] = str(Path(row['members'][0]['path']).parent / 'other' / Path(row['members'][0]['path']).name)
            if change == 'keep': row['volume_of_set'] = {'kept': True}
            if change == 'duplicate': row['members'][1] = copy.deepcopy(row['members'][0])
            with self.subTest(change=change): self.assertIsNone(part_sets.confirmed_edition(row))


def routing_result(title='Book One', author='Writer One', work_id='catalog:one', series_id='https://fantlab.ru/work100', series='Series', number='1'):
    return {'review': {'title': title, 'author': author, 'canonical_author': author, 'series': series, 'number': number},
            'metadata_facts': {'source_fingerprint': 'source-' + work_id, 'work_ids': [work_id], 'authors': [author], 'series_state': 'verified'},
            'work': {'id': work_id, 'verified_series': {'name': series, 'number': number, 'source_url': series_id}}}


class SharedAuthorityTests(unittest.TestCase):
    def test_all_three_tolkien_volumes_have_exact_middle_earth_authority(self):
        for work_id, title, number in [('fantlab:1667', 'The Fellowship of the Ring', '1'),
                                       ('fantlab:1668', 'The Two Towers', '2'),
                                       ('fantlab:1669', 'The Return of the King', '3')]:
            with self.subTest(work_id=work_id):
                first = routing_result(title, 'Tolkien J. R. R.', work_id, 'https://fantlab.ru/work1693', 'Властелин колец', number)
                first['work']['original_title'] = title
                before = copy.deepcopy(first)
                result = attach_shared_routing(first)
                planned = plan(os.path.abspath('synthetic-output'), result['review'], facts=result['metadata_facts'])
                self.assertEqual(planned['relative_path'].split(os.sep)[:2], ['Middle-earth', 'Властелин колец'])
                self.assertTrue(os.path.basename(planned['path']).endswith(' - Tolkien J. R. R.m4b'))
                self.assertEqual(result['metadata_facts']['authors'], ['Tolkien J. R. R.'])
                world = result['metadata_facts']['shared_routing']['universe']
                self.assertEqual((world['id'], world['basis']), ('user:middle-earth-2026-11-01', 'user'))
                self.assertEqual(world['members'], [{'work_id': work_id, 'authors': ['Tolkien J. R. R.'], 'series_id': 'https://fantlab.ru/work1693'}])
                self.assertEqual(first, before)

    def test_fellowship_world_requires_identity_and_preserves_explicit_universe(self):
        from shared_routing import resolve
        for change in ('work', 'title', 'author', 'number', 'series', 'cycle', 'unverified', 'member_binding',
                       'typed_empty', 'saved_empty', 'explicit_other'):
            with self.subTest(change=change):
                first = routing_result('The Fellowship of the Ring', 'Tolkien J. R. R.', 'fantlab:1667',
                                       'https://fantlab.ru/work1693', 'Властелин колец', '1')
                first['work']['original_title'] = 'The Fellowship of the Ring'
                if change == 'work':
                    first['work']['id'] = 'fantlab:99999'; first['metadata_facts']['work_ids'] = ['fantlab:99999']
                if change == 'title': first['work']['original_title'] = 'Another work'
                if change == 'author':
                    first['review']['author'] = first['review']['canonical_author'] = 'Another Writer'
                    first['metadata_facts']['authors'] = ['Another Writer']
                if change == 'number': first['review']['number'] = first['work']['verified_series']['number'] = '2'
                if change == 'series': first['review']['series'] = first['work']['verified_series']['name'] = 'Another series'
                if change == 'cycle': first['work']['verified_series']['source_url'] = 'https://fantlab.ru/work1694'
                if change == 'unverified': first['metadata_facts']['series_state'] = 'unknown'
                if change == 'member_binding': first['metadata_facts']['work_ids'] = ['fantlab:1668']
                if change == 'typed_empty': first['approval'] = {'names': {'universe': ''}}
                if change == 'saved_empty':
                    first['metadata_facts']['entered_names'] = {'fields': ['universe'], 'digest': 'a' * 64}
                    first['review']['universe'] = ''
                if change == 'explicit_other': first['review']['universe'] = 'My chosen world'
                before = copy.deepcopy(first)
                result = attach_shared_routing(first)
                self.assertEqual(result['review'].get('universe', ''), before['review'].get('universe', ''))
                self.assertFalse(resolve(result['review'], result['metadata_facts'])['shared_world'])
                self.assertNotIn('universe', result['metadata_facts'].get('shared_routing', {}))
                self.assertEqual(first, before)

    def test_general_shared_series_requires_same_stable_identity(self):
        first = routing_result(); second = routing_result(title='Book Two', author='Writer Two', work_id='catalog:two', number='2')
        result = attach_shared_routing(first, [second])
        self.assertEqual(plan(os.path.abspath('synthetic-output'), result['review'], facts=result['metadata_facts'])['relative_path'].split(os.sep)[0], 'Series')
        second['work']['verified_series']['source_url'] = 'https://fantlab.ru/work999'
        result = attach_shared_routing(first, [second])
        self.assertEqual(plan(os.path.abspath('synthetic-output'), result['review'], facts=result['metadata_facts'])['relative_path'].split(os.sep)[0], 'Writer One')

    def test_book_page_does_not_establish_shared_series_identity(self):
        first = routing_result(series_id='https://www.goodreads.com/book/show/123')
        second = routing_result(author='Writer Two', work_id='catalog:two', series_id='https://www.goodreads.com/book/show/123')
        self.assertNotIn('shared_routing', attach_shared_routing(first, [second])['metadata_facts'])

    def test_omen_explicit_memberships_keep_true_author_and_filename(self):
        for number, title, author in [('1', 'The Omen', 'David Seltzer'), ('2', 'Damien', 'Joseph Howard')]:
            result = attach_shared_routing(routing_result(title, author, 'local:omen-' + number, '', 'Omen', number))
            planned = plan(os.path.abspath('synthetic-output'), result['review'], facts=result['metadata_facts'])
            self.assertEqual(planned['relative_path'].split(os.sep)[0], 'Omen')
            self.assertEqual(result['metadata_facts']['authors'], [author])
            self.assertIn(author, os.path.basename(planned['path']))

    def test_wrong_omen_author_is_not_joined_by_title(self):
        result = attach_shared_routing(routing_result('The Omen', 'Someone Else', 'local:other', '', 'Omen', '1'))
        self.assertNotIn('shared_routing', result['metadata_facts'])

    def test_general_world_with_two_confirmed_series_has_bound_world_proof(self):
        first = routing_result(); second = routing_result(work_id='catalog:two', series_id='https://fantlab.ru/work200', series='Other series')
        for value in (first, second):
            value['review']['universe'] = 'World'
            value['work']['verified_world'] = {'id': 'user:world-one', 'name': 'World', 'basis': 'user', 'evidence': ['user:decision']}
        result = attach_shared_routing(first, [second])
        from shared_routing import resolve
        self.assertTrue(resolve(result['review'], result['metadata_facts'])['shared_world'])
        self.assertEqual(plan(os.path.abspath('synthetic-output'), result['review'], facts=result['metadata_facts'])['relative_path'].split(os.sep)[:2], ['World', 'Series'])

    def test_explicit_destination_choice_still_wins_after_proof_assembly(self):
        first = routing_result('The Omen', 'David Seltzer', 'local:omen', '', 'Omen', '1')
        root = os.path.abspath('synthetic-output'); chosen = os.path.join(root, 'My folder')
        first['metadata_facts']['destination_override'] = {'id': 'choice', 'folder': chosen, 'identity': {}}
        result = attach_shared_routing(first)
        self.assertEqual(os.path.dirname(plan(root, result['review'], facts=result['metadata_facts'])['path']), chosen)

    def test_source_and_peer_results_are_not_mutated(self):
        first = routing_result(); second = routing_result(author='Writer Two', work_id='catalog:two')
        before = copy.deepcopy((first, second))
        attach_shared_routing(first, [second])
        self.assertEqual((first, second), before)


if __name__ == '__main__':
    unittest.main()
