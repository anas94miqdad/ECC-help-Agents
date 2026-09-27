"""Offline tests for the scientific-writing-publication skill scripts. No network calls."""

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / 'skills/scientific-writing-publication/scripts'


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verify = load('verify_references')
cites = load('check_citations')
checks = load('manuscript_checks')


class VerifyReferencesTest(unittest.TestCase):
    def test_normalize_and_validate_doi(self):
        self.assertEqual(verify.normalize_doi('https://doi.org/10.1000/ABC.1.'), '10.1000/abc.1')
        self.assertEqual(verify.normalize_doi('doi: 10.1000/xyz'), '10.1000/xyz')
        self.assertTrue(verify.is_valid_doi('10.1000/xyz'))
        self.assertFalse(verify.is_valid_doi('10.10/xyz'))
        self.assertFalse(verify.is_valid_doi('not-a-doi'))

    def test_surname_formats(self):
        self.assertEqual(verify.surname('Smith J'), 'smith')
        self.assertEqual(verify.surname('Smith, John'), 'smith')
        self.assertEqual(verify.surname('John Smith'), 'smith')
        self.assertEqual(verify.surname('Maier-Hein L'), 'maier hein')
        self.assertEqual(verify.surname('Müller A'), 'muller')

    def test_compare_verified(self):
        record = {'title': 'Deep learning for <i>fracture</i> segmentation on CT',
                  'year': 2023, 'first_author': 'Smith'}
        claimed = {'title': 'Deep learning for fracture segmentation on CT.',
                   'year': '2023', 'first_author': 'Smith J'}
        self.assertEqual(verify.compare(claimed, record)[0], 'VERIFIED')

    def test_compare_rejects_title_mismatch(self):
        record = {'title': 'A completely different study of cardiac MRI', 'year': 2023, 'first_author': 'Doe'}
        claimed = {'title': 'Deep learning for fracture segmentation on CT', 'year': '2023'}
        self.assertEqual(verify.compare(claimed, record)[0], 'REJECTED')

    def test_compare_partial_on_author_or_year(self):
        record = {'title': 'Fracture segmentation on CT', 'year': 2022, 'first_author': 'Doe'}
        claimed = {'title': 'Fracture segmentation on CT', 'year': '2023', 'first_author': 'Smith'}
        status, reasons = verify.compare(claimed, record)
        self.assertEqual(status, 'PARTIALLY_VERIFIED')
        self.assertEqual(len(reasons), 2)

    def test_compare_identifier_only_is_partial(self):
        self.assertEqual(verify.compare({}, {'title': 'x', 'year': 2020})[0], 'PARTIALLY_VERIFIED')

    def test_retraction_wins(self):
        record = {'title': 'Fracture segmentation on CT', 'year': 2022, 'retracted': True}
        self.assertEqual(verify.compare({'title': 'Fracture segmentation on CT'}, record)[0], 'RETRACTED')

    def test_parse_crossref_and_notices(self):
        msg = {'title': ['Example'], 'issued': {'date-parts': [[2021, 5]]},
               'author': [{'family': 'Doe', 'given': 'J'}], 'container-title': ['J Test'],
               'type': 'journal-article', 'updated-by': [{'type': 'correction', 'DOI': '10.1/c'}]}
        rec = verify.parse_crossref_work(msg)
        self.assertEqual((rec['title'], rec['year'], rec['first_author']), ('Example', 2021, 'Doe'))
        items = [{'update-to': [{'DOI': '10.1000/X', 'type': 'retraction'}]},
                 {'update-to': [{'DOI': '10.1000/other', 'type': 'retraction'}]}]
        notices = rec['notices'] + verify.notices_from_update_items(items, '10.1000/x')
        retracted, corrected = verify.classify_notices(notices)
        self.assertTrue(retracted)
        self.assertEqual(corrected, ['correction'])

    def test_parse_pubmed_summary(self):
        result = {'123': {'title': 'T', 'pubdate': '2020 Jan', 'authors': [{'name': 'Doe J'}],
                          'articleids': [{'idtype': 'doi', 'value': '10.1/ABC'}],
                          'pubtype': ['Journal Article', 'Retracted Publication']}}
        rec = verify.parse_pubmed_summary(result, '123')
        self.assertEqual(rec['year'], 2020)
        self.assertEqual(rec['doi'], '10.1/abc')
        self.assertTrue(rec['retracted'])
        self.assertIsNone(verify.parse_pubmed_summary({'9': {'error': 'x'}}, '9'))

    def test_invalid_doi_rejected_without_network(self):
        out = verify.verify_one({'id': '1', 'doi': 'doi:not-valid'})
        self.assertEqual(out['status'], 'REJECTED')

    def test_no_identifier_stays_unverified(self):
        out = verify.verify_one({'id': '1', 'title': 'Something'})
        self.assertEqual(out['status'], 'UNVERIFIED')


class CheckCitationsTest(unittest.TestCase):
    MANUSCRIPT = """# Introduction
Fractures are common [1]. Prior work used CNNs [2-4] and transformers [3, 6].
Later we cite [5].

## References
1. Doe J. First paper. J Test. 2020. doi:10.1000/a1
2. Roe R. Second paper. J Test. 2021.
3. Poe P. Third paper. J Test. 2022.
4. Moe M. Fourth paper. J Test. 2023. https://doi.org/10.1000/A1
5. Zoe Z. Fifth paper. J Test. 2024.
7. Unused U. Never cited. J Test. 2019.
"""

    def test_numeric_report(self):
        body, refs = cites.split_manuscript(self.MANUSCRIPT)
        report = cites.check_numeric(body, refs)
        self.assertEqual(report['missing_entries'], [6])
        self.assertEqual(report['uncited_entries'], [7])
        self.assertFalse(report['first_appearance_order_ok'])
        self.assertEqual(report['first_out_of_order'], [6])
        self.assertTrue(any('10.1000/a1' in d[2] for d in report['duplicates']))

    def test_expand_numeric(self):
        self.assertEqual(cites.expand_numeric('1, 3–5;8'), [1, 3, 4, 5, 8])

    def test_author_year(self):
        body = 'As shown (Smith et al., 2020; Doe, 2019), and Roe (2021) agreed.'
        refs = 'Smith J, Lee K. Title A. J Test. 2020.\nDoe J. Title B. J Test. 2019.\nKay K. Title C. 2018.'
        report = cites.check_author_year(body, refs)
        self.assertEqual(report['missing_entries'], ['Roe 2021'])
        self.assertEqual(report['uncited_entries'], ['Kay 2018'])

    def test_detect_style(self):
        self.assertEqual(cites.detect_style('a [1] b [2]'), 'numeric')
        self.assertEqual(cites.detect_style('a (Smith, 2020)'), 'author-year')


class ManuscriptChecksTest(unittest.TestCase):
    TEXT = """# A study title

## Abstract
We included 120 patients. Mean Dice was 0.87 (95% CI 0.85-0.89). This groundbreaking model
reached an AUC of 0.93.

## Introduction
Background text [MISSING: epidemiology source].

## Methods
### 2.1 Data
We included 120 patients (Table 1). See Figure 2 and Figure 1.

## Results
Mean Dice was 0.87 (95% CI 0.85-0.89). Table 3 shows subgroups.

## References
1. Ref.
"""

    def test_report(self):
        report = checks.run_checks(self.TEXT, abstract_limit=10)
        self.assertIn('0.93', report['abstract_numbers_not_in_main_text'])
        self.assertNotIn('0.87', report['abstract_numbers_not_in_main_text'])
        self.assertEqual(len(report['placeholders']), 1)
        self.assertIn('groundbreaking', report['hype_terms'])
        self.assertIn('methods', report['section_word_counts'])
        self.assertNotIn('2.1 data', report['section_word_counts'])
        self.assertEqual(report['figure_table_references']['table']['gaps'], [2])
        self.assertFalse(report['figure_table_references']['figure']['first_mention_order_ok'])
        self.assertTrue(any('abstract' in i and 'limit' in i for i in report['issues']))

    def test_plain_text_headings(self):
        text = 'Abstract\nWe found 3 cases.\nIntroduction\nThere were 3 cases.\n'
        report = checks.run_checks(text)
        self.assertEqual(report['abstract_numbers_not_in_main_text'], [])
        self.assertEqual(report['main_text_words'], 4)

    def test_decimal_comma_matches(self):
        self.assertEqual(checks.abstract_numbers_missing('Dice 0,87', 'Dice 0.87'), [])


if __name__ == '__main__':
    unittest.main()
