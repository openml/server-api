from __future__ import annotations

import random
import re

SplitEntry = dict[str, int | str]


def generate_splits(
    n_samples: int,
    n_folds: int,
    n_repeats: int,
    *,
    seed: int = 0,
) -> list[SplitEntry]:
    """Generate cross-validation splits deterministically.

    Returns a flat list of dicts with keys:
        repeat, fold, rowid, type ('TRAIN' or 'TEST')
    """
    if n_folds <= 0:
        msg = f"n_folds must be a positive integer, got {n_folds}"
        raise ValueError(msg)
    if n_repeats <= 0:
        msg = f"n_repeats must be a positive integer, got {n_repeats}"
        raise ValueError(msg)
    if n_samples <= 0:
        return []

    entries: list[SplitEntry] = []
    rng = random.Random(seed)  # noqa: S311

    for repeat in range(n_repeats):
        indices = list(range(n_samples))
        rng.shuffle(indices)

        for fold in range(n_folds):
            for row_pos, rowid in enumerate(indices):
                split_type = "TEST" if row_pos % n_folds == fold else "TRAIN"
                entries.append(
                    {
                        "repeat": repeat,
                        "fold": fold,
                        "rowid": rowid,
                        "type": split_type,
                    },
                )

    return entries


_ARFF_DATA_SECTION = re.compile(r"@[Dd][Aa][Tt][Aa]")


def parse_arff_splits(arff_content: str) -> list[SplitEntry]:
    """Parse an OpenML splits ARFF file into the same list-of-dict format.

    Expected ARFF columns (in order): type, rowid, repeat, fold
    (This is the column order used by OpenML's split ARFF files.)
    """
    in_data = False
    entries: list[SplitEntry] = []

    for line in arff_content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("%"):
            continue
        if _ARFF_DATA_SECTION.match(stripped):
            in_data = True
            continue
        if not in_data:
            continue

        parts = [p.strip() for p in stripped.split(",")]
        if len(parts) < 4:  # noqa: PLR2004
            continue
        split_type, rowid_s, repeat_s, fold_s = parts[:4]
        try:
            entries.append(
                {
                    "repeat": int(repeat_s),
                    "fold": int(fold_s),
                    "rowid": int(rowid_s),
                    "type": split_type.strip("'\""),
                },
            )
        except ValueError:
            continue

    return entries


def build_fold_index(
    splits: list[SplitEntry],
    repeat: int = 0,
) -> dict[int, tuple[list[int], list[int]]]:
    """Build a dict of fold -> (train_indices, test_indices) for a given repeat."""
    folds: dict[int, tuple[list[int], list[int]]] = {}
    for entry in splits:
        if entry["repeat"] != repeat:
            continue
        fold = int(entry["fold"])
        rowid = int(entry["rowid"])
        split_type = str(entry["type"]).upper()
        if split_type not in {"TRAIN", "TEST"}:
            continue
        if fold not in folds:
            folds[fold] = ([], [])
        if split_type == "TRAIN":
            folds[fold][0].append(rowid)
        else:
            folds[fold][1].append(rowid)
    return folds
