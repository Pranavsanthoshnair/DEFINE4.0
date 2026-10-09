"""
IndicTrans2 translation engine.
Loads AI4Bharat IndicTrans2 English→Indic distilled model (~200 M params).
Batches all segments in a single model call for efficiency.
Results are cached in-memory by (text, src, tgt).
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from typing import Optional

import structlog

log = structlog.get_logger()

# IndicTrans2 language tags (ISO → Flores tag)
LANG_TO_FLORES: dict[str, str] = {
    "en": "eng_Latn",
    "hi": "hin_Deva",
    "ml": "mal_Mlym",
    "ta": "tam_Taml",
    "te": "tel_Telu",
    "kn": "kan_Knda",
    "bn": "ben_Beng",
    "mr": "mar_Deva",
    "gu": "guj_Gujr",
}

# Allowlisted English words that should NOT trigger the "no Indic script" check
ALLOWLISTED_ENGLISH = {"ok", "okay", "sms", "otp"}


class IndicTransEngine:
    """
    Wrapper around IndicTrans2. Available only when the model is installed.
    """

    def __init__(self, model_id: str) -> None:
        self._model_id = model_id
        self._model = None
        self._tokenizer = None
        self._ip = None          # IndicProcessor
        self._load()

    def _load(self) -> None:
        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer  # type: ignore[import]
            from IndicTransToolkit import IndicProcessor  # type: ignore[import]

            self._tokenizer = AutoTokenizer.from_pretrained(
                self._model_id, trust_remote_code=True
            )
            self._model = AutoModelForSeq2SeqLM.from_pretrained(
                self._model_id, trust_remote_code=True
            )
            self._model.eval()
            self._ip = IndicProcessor(inference=True)
            log.info("indictrans2_loaded", model=self._model_id)
        except Exception as exc:
            log.warning("indictrans2_not_available", error=str(exc))

    @property
    def available(self) -> bool:
        return self._model is not None

    def translate_batch(
        self,
        texts: list[str],
        src_lang: str,
        tgt_lang: str,
    ) -> list[str]:
        """
        Translate a batch of texts. Returns list of translated strings.
        Raises RuntimeError if model not loaded.
        """
        if not self.available:
            raise RuntimeError("IndicTrans2 model not loaded")

        src_flores = LANG_TO_FLORES.get(src_lang)
        tgt_flores = LANG_TO_FLORES.get(tgt_lang)
        if not src_flores or not tgt_flores:
            raise ValueError(f"Unsupported language pair: {src_lang}→{tgt_lang}")

        import torch  # type: ignore[import]

        batch = self._ip.preprocess_batch(texts, src_lang=src_flores, tgt_lang=tgt_flores)
        inputs = self._tokenizer(
            batch, truncation=True, padding="longest",
            return_tensors="pt", return_attention_mask=True,
        )
        with torch.no_grad():
            generated = self._model.generate(
                **inputs,
                num_beams=5,
                num_return_sequences=1,
                max_length=256,
            )
        decoded = self._tokenizer.batch_decode(generated, skip_special_tokens=True)
        return self._ip.postprocess_batch(decoded, lang=tgt_flores)


def _sanity_check(original: str, translated: str, tgt_lang: str) -> bool:
    """
    Validate translation quality heuristics.
    Returns True if the translation passes, False if it should be rejected.
    """
    if not translated.strip():
        return False

    # Length ratio check
    ratio = len(translated) / max(len(original), 1)
    if ratio < 0.4 or ratio > 4.0:
        log.warning("translation_length_ratio_fail", ratio=ratio)
        return False

    # For Indic targets: check that output contains at least some target-script chars
    if tgt_lang in ("hi", "mr"):
        script_range = r"[\u0900-\u097F]"
    elif tgt_lang == "ml":
        script_range = r"[\u0D00-\u0D7F]"
    elif tgt_lang == "ta":
        script_range = r"[\u0B80-\u0BFF]"
    elif tgt_lang == "te":
        script_range = r"[\u0C00-\u0C7F]"
    elif tgt_lang == "kn":
        script_range = r"[\u0C80-\u0CFF]"
    elif tgt_lang == "bn":
        script_range = r"[\u0980-\u09FF]"
    elif tgt_lang == "gu":
        script_range = r"[\u0A80-\u0AFF]"
    else:
        return True  # English — no script check

    if not re.search(script_range, translated):
        log.warning("translation_no_target_script", tgt_lang=tgt_lang)
        return False

    return True


# Segment-level translation cache: (text, src, tgt) -> translated
_translate_cache: dict[tuple[str, str, str], str] = {}


def translate_segments(
    segments: dict[str, str],
    src_lang: str,
    tgt_lang: str,
    engine: IndicTransEngine,
) -> dict[str, str]:
    """
    Translate all segments, using the per-text cache.
    Returns the translated segments dict.
    """
    cache_hits: dict[str, str] = {}
    to_translate_keys: list[str] = []
    to_translate_texts: list[str] = []

    for key, text in segments.items():
        cache_key = (text, src_lang, tgt_lang)
        if cache_key in _translate_cache:
            cache_hits[key] = _translate_cache[cache_key]
        else:
            to_translate_keys.append(key)
            to_translate_texts.append(text)

    if to_translate_texts:
        translated_texts = engine.translate_batch(to_translate_texts, src_lang, tgt_lang)
        for key, orig, trans in zip(to_translate_keys, to_translate_texts, translated_texts):
            if not _sanity_check(orig, trans, tgt_lang):
                log.warning("translation_sanity_fail", key=key, tgt_lang=tgt_lang)
                trans = orig  # fallback to source text
            _translate_cache[(orig, src_lang, tgt_lang)] = trans
            cache_hits[key] = trans

    return cache_hits
