# Intent Error Analysis

Read-only analysis of the current ONNX model on
`ai/ml/intent/data/test.jsonl`. Runtime temperature was `0.527`; all six
labels were allowed. No model, training, or rules code was changed.

## 1. Model-only error dump

Model-only accuracy was `0.775` and macro F1 was `0.7846994251349524`.
The rows below are every one of the 54 errors, grouped by true label to
predicted label. Confidence is the calibrated runtime confidence.

### call_later -> decline (6)

```text
en | call_later | decline | 0.8657 | Call later, don't be busy.
ta | call_later | decline | 0.3931 | Call later, sure but busy now
hi | call_later | decline | 0.4011 | Umm... later? I'm busy now
hi | call_later | decline | 0.7166 | Abhi nahi, busy hoon
hi | call_later | decline | 0.5002 | Umm, later, I'm busy, haan
ta | call_later | decline | 0.3802 | Appuram, i'm busy, call me later
```

Mostly model errors. These texts contain strong `later`/`busy` cues; the
true label is plausible. The first is somewhat contradictory, so it is
ambiguous rather than a fully clear model error.

### confirm -> decline (5)

```text
en | confirm | decline | 0.7096 | Confirm, I'm not sure
ml | confirm | decline | 0.4470 | Athey, varam, busy now, come later?
en | confirm | decline | 0.4054 | Romanised: I'm a vālī, sūr.
en | confirm | decline | 0.8724 | Impolite: Can I come, but I'm not sure.
ml | confirm | decline | 0.7241 | Ok, I'm busy now
```

Mixed. The `not sure`, busy, and contradictory wording makes several true
labels questionable or ambiguous. The plain confirmation cues in the
Malayalam rows make those two more likely model errors.

### confirm -> unclear (13)

```text
ta | confirm | unclear | 0.6297 | sari, busy now?
hi | confirm | unclear | 0.8125 | Haan haan, kya kya karta hai?
ml | confirm | unclear | 0.9229 | Varam, is this clear?
hi | confirm | unclear | 0.6273 | Aap kya kare, haan haan?
ml | confirm | unclear | 0.5312 | Okay, busy now, come later?
ml | confirm | unclear | 0.8094 | Who called me? Umm...
hi | confirm | unclear | 0.8168 | Ji haan, tum kya kia hai?
ml | confirm | unclear | 0.5037 | Okay, I'm busy, can you come later?
en | confirm | unclear | 0.4000 | Native: I'm not sure if I can come.
hi | confirm | unclear | 0.7678 | Ji haan, kya kare?
hi | confirm | unclear | 0.8525 | Ji haan, kya sab kare?
ml | confirm | unclear | 0.5812 | Varam, I'm busy, can you come?
ml | confirm | unclear | 0.5023 | I'm sure it's okay, let's do this
```

Mixed. Several rows are genuinely ambiguous because they combine confirmation
with busy/later or uncertainty. The rows beginning `Haan haan`, `Ji haan`,
and `Varam` contain clear confirmation cues; those are model errors. `Who
called me?` is plausibly mislabeled as confirm.

### reschedule -> decline (3)

```text
ta | reschedule | decline | 0.6486 | Kana schedule, busy now
ml | reschedule | decline | 0.3427 | Um, change schedule, umm, busy now?
ml | reschedule | decline | 0.5079 | Reschedule when you're not busy?
```

The true label is plausible in all three. The model overweights `busy` and
underweights the scheduling request; these are model errors, with some
ambiguity from the wording.

### reschedule -> unclear (7)

```text
ml | reschedule | unclear | 0.5200 | Um, I'm busy now, can we move it later?
ta | reschedule | unclear | 0.7180 | Neram, when can we reschedule?
ml | reschedule | unclear | 0.4320 | Vere samayam, schedule reset?
ta | reschedule | unclear | 0.6868 | Reschedule, please, when is free?
ml | reschedule | unclear | 0.3259 | Schedule maaroo, busy abhi, when later?
ta | reschedule | unclear | 0.5031 | haan haan reschedule when can i come?
ml | reschedule | unclear | 0.8607 | Pinneedu, when can we do it?
```

The true label is clear for the rows containing `reschedule`, `schedule`, or
`when can we`; these are model errors. The `move it later` and `Pinneedu`
rows are less explicit and somewhat ambiguous.

### stop_calling -> decline (10)

```text
en | stop_calling | decline | 0.8846 | I don't want to be called again.
ta | stop_calling | decline | 0.7992 | Haan haan, stop, busy
ta | stop_calling | decline | 0.4968 | stop callin' i'm busy
ml | stop_calling | decline | 0.6510 | Stop calling, busy, no
en | stop_calling | decline | 0.8896 | Don't call me unless I consent. (1)
en | stop_calling | decline | 0.6008 | Stop calling me, no.
en | stop_calling | decline | 0.8862 | I don't want to be called. (1)
ml | stop_calling | decline | 0.6511 | Hai, stop calling, come on, no
en | stop_calling | decline | 0.8911 | Don't call me again. (1)
ta | stop_calling | decline | 0.7035 | Haan haan, stop
```

The true label is clear in nearly every row; these are primarily model
errors. The exception is the `busy`/`no` code-mixed wording, which creates
competing intent cues.

### stop_calling -> unclear (1)

```text
ta | stop_calling | unclear | 0.8868 | Umm, who's callin' me?
```

This is ambiguous and may be mislabeled: it mentions calling but does not ask
the caller to stop.

### unclear -> decline (9)

```text
ml | unclear | decline | 0.8717 | come, too busy, can't hear well
en | unclear | decline | 0.6372 | Romanised: 'I'm not sure if you're calling about the meeting or something else.'
ml | unclear | decline | 0.6729 | later, but I need more info
ml | unclear | decline | 0.8498 | Haan haan, not sure, unclear
hi | unclear | decline | 0.9157 | Pata nahi, kaun ho
ml | unclear | decline | 0.5164 | Come on, busy right now
ta | unclear | decline | 0.9356 | nope not sure
ml | unclear | decline | 0.6909 | Ethu event? I don't get it
ta | unclear | decline | 0.7655 | not clear, umm, please
```

Most true labels look correct: these are uncertainty, identity, or
insufficient-information utterances. The model is clearly at fault on most
of them, over-predicting decline from `nope`, `not`, or negative phrasing.

### Malayalam errors separately

There are 22 Malayalam errors:

```text
reschedule | unclear  | 0.5200 | Um, I'm busy now, can we move it later?
reschedule | unclear  | 0.4320 | Vere samayam, schedule reset?
unclear    | decline  | 0.8717 | come, too busy, can't hear well
confirm    | unclear  | 0.9229 | Varam, is this clear?
unclear    | decline  | 0.6729 | later, but I need more info
unclear    | decline  | 0.8498 | Haan haan, not sure, unclear
confirm    | unclear  | 0.5312 | Okay, busy now, come later?
confirm    | unclear  | 0.8094 | Who called me? Umm...
unclear    | decline  | 0.5164 | Come on, busy right now
reschedule | decline  | 0.3427 | Um, change schedule, umm, busy now?
confirm    | unclear  | 0.5037 | Okay, I'm busy, can you come later?
confirm    | decline   | 0.4470 | Athey, varam, busy now, come later?
reschedule | unclear  | 0.3259 | Schedule maaroo, busy abhi, when later?
stop_calling | decline | 0.6510 | Stop calling, busy, no
confirm    | unclear  | 0.5812 | Varam, I'm busy, can you come?
confirm    | decline   | 0.7241 | Ok, I'm busy now
unclear    | decline  | 0.6909 | Ethu event? I don't get it
stop_calling | decline | 0.6511 | Hai, stop calling, come on, no
confirm    | unclear  | 0.5023 | I'm sure it's okay, let's do this
reschedule | decline  | 0.5079 | Reschedule when you're not busy?
reschedule | unclear  | 0.8607 | Pinneedu, when can we do it?
```

Malayalam accuracy is `0.65`, the weakest language. The errors cluster around
code-mixed English words (`busy`, `later`, `schedule`) and short Romanized
Malayalam phrases.

## 2. End-to-end pipeline

The pipeline was run with all six allowed intents and `LLM_FALLBACK=none`.
Rules were evaluated first, then the ONNX model, then the no-LLM fallback.

| System | Accuracy | Macro F1 |
|---|---:|---:|
| Model-only | 0.7750 | 0.7846994251349524 |
| Full pipeline | 0.7791666666666667 | 0.7845556499082399 |

Decision shares for the full pipeline:

| Decision stage | Rows | Share |
|---|---:|---:|
| Rules | 142 | 59.17% |
| Model | 85 | 35.42% |
| Left as `unclear` | 13 | 5.42% |

The pipeline improves accuracy by 0.00417 but has a negligibly lower macro F1.
In the implementation, the final `unclear` return is reported with source
`rules`; the table separates those 13 rows by final outcome.

## 3. Model threshold sweep

Accepted predictions are model-only predictions with confidence strictly above
the threshold. All other rows are treated as `unclear` for this analysis.

| Threshold | Coverage | Accepted precision | `stop_calling` rows left unclear |
|---:|---:|---:|---:|
| 0.5 | 91.67% | 0.8000 | 2 |
| 0.6 | 80.83% | 0.8196 | 4 |
| 0.7 | 70.83% | 0.8529 | 7 |
| 0.8 | 53.33% | 0.8672 | 15 |
| 0.9 | 26.25% | 0.9524 | 24 |

Recommendation: `0.9` is the lowest tested threshold meeting the requested
accepted precision of at least 0.90. It has low coverage and leaves 24 of 40
stop-calling rows unclear, so this is a precision-first setting rather than a
balanced operating point.

## 4. Training-data audit

The training file contains 1,920 rows: 480 per language and 80 per
language/label.

### Rows per language and label

| Language | confirm | decline | reschedule | call_later | stop_calling | unclear | Total |
|---|---:|---:|---:|---:|---:|---:|---:|
| en | 80 | 80 | 80 | 80 | 80 | 80 | 480 |
| hi | 80 | 80 | 80 | 80 | 80 | 80 | 480 |
| ml | 80 | 80 | 80 | 80 | 80 | 80 | 480 |
| ta | 80 | 80 | 80 | 80 | 80 | 80 | 480 |

### Script composition

Native-script detection used Unicode ranges for Devanagari, Malayalam, and
Tamil. English was counted as Latin-script. The repository training data has
no native-script rows:

| Language | Native script / Latin rows | Romanized or non-native rows |
|---|---:|---:|
| en | 0 | 480 |
| hi | 0 | 480 |
| ml | 0 | 480 |
| ta | 0 | 480 |

Thus all Hindi, Malayalam, and Tamil training examples are Romanized or
English/code-mixed rather than written in their native scripts.

### Texts shorter than three whitespace-delimited words

| Label | Rows | Share |
|---|---:|---:|
| confirm | 1/320 | 0.3125% |
| decline | 8/320 | 2.5000% |
| reschedule | 0/320 | 0% |
| call_later | 1/320 | 0.3125% |
| stop_calling | 2/320 | 0.6250% |
| unclear | 4/320 | 1.2500% |

### Near-duplicate clusters

Clusters were counted per label after casefolding, Unicode normalization,
punctuation removal, and whitespace collapsing; a cluster has at least two
rows with the same normalized text.

| Label | Clusters | Rows in duplicate clusters | Largest cluster |
|---|---:|---:|---:|
| confirm | 11 | 22 | 2 |
| decline | 6 | 12 | 2 |
| reschedule | 5 | 12 | 4 |
| call_later | 9 | 21 | 3 |
| stop_calling | 21 | 42 | 2 |
| unclear | 1 | 2 | 2 |

## 5. Rules audit

The rules engine lowercases, NFC-normalizes, removes punctuation, collapses
whitespace, and uses whole-word phrase matching. It returns a rule decision
only when exactly one intent matches.

### Confirm patterns

| Language | Patterns |
|---|---|
| en | `yes`, `yeah`, `yep`, `yup`, `sure`, `okay`, `ok`, `alright`, `i will come`, `i'll come`, `i will be there`, `i'll be there`, `confirmed`, `count me in`, `will attend`, `attending`, `i'm coming`, `coming` |
| hi | `हाँ`, `हां`, `जी हाँ`, `जी हां`, `ठीक है`, `आऊंगा`, `आऊंगी`, `आएंगे`, `बिल्कुल`, `ज़रूर`, `हाँ आऊंगा`, `haan`, `haan haan`, `ji haan`, `theek hai`, `aaunga`, `aaungi`, `bilkul`, `zaroor`, `yes`, `okay` |
| ml | `അതെ`, `ശരി`, `വരാം`, `വരും`, `ഉണ്ട്`, `ഉണ്ടാകും`, `okay`, `sheri`, `varam`, `varum`, `atthe`, `yes`, `haan` |
| ta | `ஆம்`, `சரி`, `வருவேன்`, `வருவோம்`, `சரிதான்`, `aam`, `sari`, `varuven`, `varuvom`, `saridhan`, `yes`, `okay` |

### Stop-calling patterns

| Language | Patterns |
|---|---|
| en | `stop calling`, `do not call`, `don't call`, `remove my number`, `unsubscribe`, `stop`, `no more calls`, `please stop`, `do not disturb`, `dnd`, `block`, `opt out` |
| hi | `कॉल मत करो`, `फोन मत करो`, `बंद करो`, `मत बुलाओ`, `नंबर हटाओ`, `call mat karo`, `phone mat karo`, `band karo`, `mat bulao`, `stop`, `stop calling` |
| ml | `വിളിക്കരുത്`, `ഫോൺ ചെയ്യരുത്`, `നമ്പർ ഒഴിവാക്കൂ`, `vilikkaruth`, `phone cheyyaruth`, `nambar ozhivakku`, `stop`, `stop calling` |
| ta | `அழைக்காதீர்கள்`, `போன் பண்ணாதீர்கள்`, `நம்பர் எடுங்க`, `azhaikkadheenga`, `phone pannadheenga`, `number edhunga`, `stop`, `stop calling` |

### Stop-calling -> decline rule diagnosis

| Row | Rule result / failure reason |
|---|---|
| `I don't want to be called again.` | No exact stop phrase; `don't call` and `stop calling` do not match the wording `don't want to be called`. No rule matched. |
| `Haan haan, stop, busy` | `stop_calling: stop` and `call_later: busy` both match. The rules correctly detect a conflict and defer; they cannot select stop-calling uniquely. |
| `stop callin' i'm busy` | Punctuation normalization yields `stop callin i m busy`; `stop calling` fails because `callin` is not `calling`, while `stop` and `busy` match different intents, causing ambiguity. |
| `Stop calling, busy, no` | `stop calling`, `stop`, `busy`, and `no` match different intents. The multiple-match guard defers rather than selecting stop-calling. |
| `Don't call me unless I consent. (1)` | `don't call` matches. No rule failed; this is a model-only error that the rules would have prevented. |
| `Stop calling me, no.` | `stop calling`/`stop` and `no` both match, so the rule result is ambiguous. |
| `I don't want to be called. (1)` | No exact stop phrase; the lexicon lacks `don't want to be called`. No rule matched. |
| `Hai, stop calling, come on, no` | `stop calling`/`stop` and `no` match, so the rule result is ambiguous. |
| `Don't call me again. (1)` | `don't call` matches. No rule failed; this is a model-only error. |
| `Haan haan, stop` | `stop` matches uniquely. No rule failed; this is a model-only error. |

The rules are therefore strong for explicit stop phrases, but conflicting
`busy`/`no` cues intentionally prevent an automatic rule decision. The two
`I don't want to be called` variants expose a missing paraphrase.
