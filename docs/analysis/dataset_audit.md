# Intent Dataset Audit

Read-only audit of `ai/ml/intent/data/train.jsonl`, `val.jsonl`, and
`test.jsonl`. The datasets were not modified. Full flagged rows are in
[`dataset_audit_flagged.csv`](dataset_audit_flagged.csv).

## Flag definitions

- `generator_artifact`: text contains `Romanised:`, `Native:`, `Impolite:`,
  `Polite:`, or `(1)`.
- `multiple_label_cues`: the current language lexicon matches cues for at
  least two labels among confirm, decline, reschedule, call_later, and
  stop_calling.
- `entirely_latin_or_english`: Hindi, Malayalam, or Tamil text contains no
  character in its native Unicode script range. English is not flagged by
  this rule.

## Counts

| Split | Rows | Any flag | Generator artifacts | Multiple-label cues | Indic rows entirely Latin/English |
|---|---:|---:|---:|---:|---:|
| train | 1,920 | 1,626 | 112 | 438 | 1,440 |
| val | 240 | 201 | 14 | 62 | 180 |
| test | 240 | 201 | 16 | 48 | 180 |

The categories overlap, so their counts do not sum to the `Any flag` column.
The large entirely-Latin/English count is not an inference from audio: it is
based only on Unicode characters in the JSONL text.

## Findings

1. Hindi, Malayalam, and Tamil rows are overwhelmingly Romanized or English/
   code-mixed rather than native-script text. This limits what a native-script
   evaluation can establish without a separate native-script test set.
2. Generator scaffolding appears in all three splits. Examples include
   `Romanised:`, `Native:`, `Polite:`, `Impolite:`, and numbered `(1)` suffixes.
3. Many rows intentionally combine cues such as `confirm` + `busy`,
   `reschedule` + `later`, or `stop_calling` + `no`/`busy`. These are useful
   ambiguity cases but should not be treated as clean single-intent examples
   without human review.
4. The CSV preserves split, row number, language, label, original text, the
   flags, and the matched labels for every flagged row.
