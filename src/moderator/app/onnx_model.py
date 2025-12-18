import json
import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import onnxruntime as ort

PAD = "<PAD>"
UNK = "<UNK>"

_HEX_RE = re.compile(r"^[0-9a-fA-F]+$")
_B64_RE = re.compile(r"^[A-Za-z0-9+/]+={0,2}$")
_JWT_RE = re.compile(r"^eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$")


def shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    c = Counter(s)
    n = len(s)
    return -sum((v / n) * math.log2(v / n) for v in c.values())


@dataclass
class CnnArtifacts:
    vocab: Dict[str, int]
    mean: np.ndarray
    std: np.ndarray
    prefixes: List[str]


class CharCNNOnnxModel:
    """
    Возвращает prob_tp = P(real_secret=1). Чем больше — тем “более настоящий секрет”.
    """
    def __init__(self, model_dir: str, max_len: int = 256):
        self.model_dir = model_dir
        self.max_len = int(max_len)

        vocab_path = os.path.join(model_dir, "vocab.json")
        norm_path = os.path.join(model_dir, "feat_norm.json")
        onnx_path = os.path.join(model_dir, "charcnn.onnx")

        if not os.path.exists(vocab_path):
            raise FileNotFoundError(f"vocab.json not found: {vocab_path}")
        if not os.path.exists(norm_path):
            raise FileNotFoundError(f"feat_norm.json not found: {norm_path}")
        if not os.path.exists(onnx_path):
            raise FileNotFoundError(f"charcnn.onnx not found: {onnx_path}")

        with open(vocab_path, "r", encoding="utf-8") as f:
            vocab = json.load(f)

        with open(norm_path, "r", encoding="utf-8") as f:
            norm = json.load(f)

        mean = np.array(norm["mean"], dtype=np.float32)
        std = np.array(norm["std"], dtype=np.float32)
        prefixes = norm.get("prefixes", [])

        self.art = CnnArtifacts(vocab=vocab, mean=mean, std=std, prefixes=prefixes)

        # ONNX Runtime session
        self.sess = ort.InferenceSession(
            onnx_path,
            providers=["CPUExecutionProvider"],
        )
        # запомним имена входов на случай, если экспорт поменяет
        ins = {i.name for i in self.sess.get_inputs()}
        self.in_char = "x_char" if "x_char" in ins else self.sess.get_inputs()[0].name
        self.in_feat = "x_feat" if "x_feat" in ins else self.sess.get_inputs()[1].name

    def _encode_chars(self, s: str) -> np.ndarray:
        v = self.art.vocab
        unk = v.get(UNK, 1)
        pad = v.get(PAD, 0)

        s = (s or "").strip()
        ids = [v.get(ch, unk) for ch in s[: self.max_len]]
        if len(ids) < self.max_len:
            ids.extend([pad] * (self.max_len - len(ids)))
        return np.asarray(ids, dtype=np.int64)

    def _structural_features(self, s: str) -> np.ndarray:
        s = s or ""
        L = len(s)
        ent = shannon_entropy(s) if L > 0 else 0.0

        digits = sum(ch.isdigit() for ch in s)
        lowers = sum(ch.islower() for ch in s)
        uppers = sum(ch.isupper() for ch in s)
        letters = sum(ch.isalpha() for ch in s)
        spaces = sum(ch.isspace() for ch in s)
        specials = L - digits - letters - spaces

        denom = L if L > 0 else 1
        f_digits = digits / denom
        f_lowers = lowers / denom
        f_uppers = uppers / denom
        f_letters = letters / denom
        f_spaces = spaces / denom
        f_specials = specials / denom

        f_has_eq = 1.0 if "=" in s else 0.0
        f_has_dash = 1.0 if "-" in s else 0.0
        f_has_us = 1.0 if "_" in s else 0.0
        f_has_slash = 1.0 if "/" in s else 0.0
        f_has_plus = 1.0 if "+" in s else 0.0

        is_hex = 1.0 if (L >= 16 and _HEX_RE.match(s) is not None) else 0.0
        is_b64 = 1.0 if (L >= 16 and _B64_RE.match(s) is not None) else 0.0
        is_jwt = 1.0 if _JWT_RE.match(s) is not None else 0.0

        pref = [1.0 if s.startswith(p) else 0.0 for p in self.art.prefixes]

        return np.array(
            [
                float(L),
                float(ent),
                f_digits, f_lowers, f_uppers, f_letters, f_spaces, f_specials,
                f_has_eq, f_has_dash, f_has_us, f_has_slash, f_has_plus,
                is_hex, is_b64, is_jwt,
                *pref,
            ],
            dtype=np.float32,
        )

    def _norm(self, x: np.ndarray) -> np.ndarray:
        return (x - self.art.mean) / self.art.std

    def predict_prob_tp(self, candidate: str) -> float:
        x_char = self._encode_chars(candidate)[None, :]              # [1, L] int64
        x_feat = self._norm(self._structural_features(candidate))    # [F] float32
        x_feat = x_feat.astype(np.float32)[None, :]                  # [1, F]

        logit = self.sess.run(None, {self.in_char: x_char, self.in_feat: x_feat})[0]
        # logit shape: [B] или [B,1]
        logit = np.asarray(logit).reshape(-1)[0]
        prob = 1.0 / (1.0 + np.exp(-float(logit)))
        return float(prob)
