"""Offline tests for the scientific-writing-publication skill scripts. No network calls."""

import importlib.util
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / 'skills/scientific-writing-publication/scripts'


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sys.path.insert(0, str(SCRIPTS))
verify = load('verify_references')
cites = load('check_citations')
checks = load('manuscript_checks')
extract = load('extract_manuscript')
compare = load('compare_versions')
builder = load('build_docx')

W_NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
TRACKED_DOCX_BODY = (
    '<?xml version="1.0" encoding="UTF-8"?><w:document ' + W_NS + '><w:body>'
    '<w:p><w:r><w:t>Methods</w:t></w:r></w:p>'
    '<w:p><w:r><w:t xml:space="preserve">We scanned </w:t></w:r>'
    '<w:ins w:id="1" w:author="A"><w:r><w:t>120</w:t></w:r></w:ins>'
    '<w:del w:id="2" w:author="A"><w:r><w:delText>100</w:delText></w:r></w:del>'
    '<w:r><w:t xml:space="preserve"> patients.</w:t></w:r>'
    '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
    '<w:r><w:instrText>ADDIN ZOTERO_ITEM CSL_CITATION {}</w:instrText></w:r></w:p>'
    '<w:sdt><w:sdtContent><w:p><w:r><w:t>Inside content control.</w:t></w:r></w:p></w:sdtContent></w:sdt>'
    '</w:body></w:document>')


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

    def test_captions_are_not_citations(self):
        refs = checks.figure_table_refs('**Table 1.** Caption\nText, see Table 2.\nTable 2. Caption\nFig. 1. Overview\n')
        self.assertEqual(refs['table']['mentioned'], [2])
        self.assertEqual(refs['table']['captions_not_cited'], [1])
        self.assertEqual(refs['figure']['captions_not_cited'], [1])
        report = checks.run_checks('## Abstract\nA 1.\n## Results\nTable 1. Caption\nText 1.\n')
        self.assertTrue(any('never cited' in i for i in report['issues']))

    def test_keywords_not_counted_in_abstract(self):
        report = checks.run_checks('## Abstract\nOne two three.\n\n**Keywords:** a; b; c; d\n## Introduction\nText.\n')
        self.assertEqual(report['abstract_words'], 3)

    def test_decimal_comma_matches(self):
        self.assertEqual(checks.abstract_numbers_missing('Dice 0,87', 'Dice 0.87'), [])



class ExtractAndBuildDocxTest(unittest.TestCase):
    MD = """# Title of the study

Introduction

We included 120 patients and Dice was 0.87. {>>Where is the ethics vote?<<}

## Results

Dice was **0.87** with [MISSING: CI].

| Split | Patients |
|---|---|
| Test | 18 |

References

1. Doe J. Paper. 2020.
"""

    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'paper.docx'
            info = builder.build(self.MD, str(path), line_numbers=True, double_spacing=True)
            self.assertEqual(info['comments'], 1)
            with zipfile.ZipFile(path) as zf:
                names = set(zf.namelist())
                self.assertIn('word/comments.xml', names)
                doc = zf.read('word/document.xml').decode()
                self.assertIn('lnNumType', doc)
                self.assertIn('w:highlight', doc)
                self.assertIn('<dc:creator></dc:creator>', zf.read('docProps/core.xml').decode())
            blocks, meta = extract.extract(str(path))
            by_type = [b['type'] for b in blocks]
            self.assertIn('table', by_type)
            sections = {b['section'] for b in blocks}
            self.assertTrue({'introduction', 'results', 'references'} <= sections)
            commented = [b for b in blocks if b.get('comments')]
            self.assertEqual(commented[0]['comments'][0]['text'], 'Where is the ethics vote?')
            self.assertTrue(any('comment' in w for w in meta['warnings']))
            self.assertIn('abstract', meta['standard_sections_not_detected'])
            clean = extract.render_clean_markdown(blocks)
            self.assertNotIn('[P0', clean)
            self.assertIn('## Results', clean)
            md = extract.render_markdown(blocks, meta)
            self.assertIn('[P0001]', md)
            self.assertIn('[T0001] TABLE', md)

    def test_tracked_changes_fields_and_sdt(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'tracked.docx'
            with zipfile.ZipFile(path, 'w') as zf:
                zf.writestr('word/document.xml', TRACKED_DOCX_BODY)
            blocks, meta = extract.extract(str(path))
            para = [b for b in blocks if 'patients' in b['text']][0]
            self.assertEqual(para['text'], 'We scanned 120 patients.')
            self.assertEqual(para['tracked'], {'inserted': ['120'], 'deleted': ['100']})
            self.assertEqual(blocks[0]['type'], 'heading')
            self.assertEqual(para['section'], 'methods')
            self.assertTrue(any('Inside content control' in b['text'] for b in blocks))
            joined = ' '.join(meta['warnings'])
            self.assertIn('tracked changes', joined)
            self.assertIn('Zotero', joined)

    def test_pdf_cleaning(self):
        pages = [f"J Test Imaging\n{i}  Line one of text segmen-\n{i + 1}  tation continues here.\n{i + 1}"
                 for i in range(1, 4)]
        text, info = extract.clean_pdf_pages(pages)
        self.assertNotIn('J Test Imaging', text)
        self.assertIn('segmentation continues', text)
        self.assertTrue(info['stripped_line_numbers'])

    def test_unsupported_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'x.pages'
            path.write_text('x')
            with self.assertRaises(RuntimeError):
                extract.extract(str(path))

    def test_german_headings(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'de.md'
            path.write_text('Zusammenfassung\n\nWir fanden 3 Fälle.\n\nMaterial und Methoden\n\nText.\n',
                            encoding='utf-8')
            blocks, _ = extract.extract(str(path))
            self.assertEqual([b['section'] for b in blocks if b['type'] != 'heading'],
                             ['abstract', 'materials and methods'])
            path.write_text('# Zusammenfassung\n\nWir fanden 3 Fälle.\n\n# Material und Methoden\n\nText.\n',
                            encoding='utf-8')
            blocks, _ = extract.extract(str(path))
            self.assertEqual([b['section'] for b in blocks if b['type'] != 'heading'],
                             ['abstract', 'materials and methods'])


class CompareVersionsTest(unittest.TestCase):
    BLOCKS = [
        {'id': 'P0001', 'type': 'heading', 'text': 'Results', 'section': 'results'},
        {'id': 'P0002', 'type': 'paragraph', 'text': 'Dice was 0.87 in 18 patients.', 'section': 'results'},
        {'id': 'P0003', 'type': 'paragraph', 'text': 'Background on fractures.', 'section': 'introduction'},
        {'id': 'P0004', 'type': 'paragraph', 'text': 'Duplicate background.', 'section': 'introduction'},
        {'id': 'P0005', 'type': 'paragraph', 'text': '1. Doe J. Paper. doi:10.1000/a1', 'section': 'references'},
    ]

    def test_pass(self):
        md = """## Introduction
<!-- src: P0003 -->
Background on fractures [1].

## Results
<!-- src: P0002 -->
Mean Dice was 0.87 (18 patients; Table 1).
<!-- discarded: P0004 = duplicate of P0003 -->

## References
1. Doe J. Paper. doi:10.1000/a1
"""
        report = compare.compare(self.BLOCKS, md)
        self.assertEqual(report['uncovered_blocks'], [])
        self.assertEqual(report['new_numbers_without_source'], [])
        self.assertEqual(report['original_result_numbers_missing'], [])
        self.assertEqual(report['references']['dois_removed'], [])
        rows = compare.traceability_rows(md)
        self.assertEqual(rows[1][0], 'Results')
        self.assertEqual(rows[1][2], 'P0002')

    def test_detects_problems(self):
        md = """## Results
<!-- src: P0002 -->
Mean Dice was 0.87; sensitivity was 0.93.
<!-- src: NEW -->
A new paragraph.
<!-- discarded: P0004; P0099 = unknown -->
"""
        report = compare.compare(self.BLOCKS, md, data_texts=[])
        self.assertEqual(report['uncovered_blocks'], ['P0003'])
        self.assertEqual(report['new_numbers_without_source'], ['0.93'])
        self.assertEqual(report['original_result_numbers_missing'], ['18'])
        self.assertEqual(report['discarded_without_reason'], ['P0004'])
        self.assertEqual(report['unknown_block_ids'], ['P0099'])
        self.assertEqual(report['references']['dois_removed'], ['10.1000/a1'])
        self.assertEqual(len(report['new_paragraphs_for_author_review']), 1)

    def test_data_file_numbers_are_allowed(self):
        md = '<!-- src: P0002, P0003 -->\nDice 0.87 in 18 patients; sensitivity 0.93.\n<!-- discarded: P0004 = dup -->'
        report = compare.compare(self.BLOCKS, md, data_texts=['metric,value\nsensitivity,0.93'])
        self.assertEqual(report['new_numbers_without_source'], [])

    def test_line_initial_decimals_are_data_not_headings(self):
        # two-line table cells put medians at line start; they must count as numbers
        self.assertEqual(compare.numbers_in('3.51 ± 0.71\n3.63 (3.00–4.25)'),
                         {'3.51', '0.71', '3.63', '3', '4.25'})
        self.assertEqual(compare.numbers_in('2.1 Data collection\nValue 1.5.'), {'1.5'})

    def test_labels_and_citations_are_not_numbers(self):
        self.assertEqual(compare.numbers_in('See Figure 3 and Table 2 [4, 5]. Value 1.5.'), {'1.5'})
        self.assertEqual(compare.numbers_in('Value 1.5 {>>check: 16.66/40 = 0.4165<<}'), {'1.5'})


if __name__ == '__main__':
    unittest.main()
