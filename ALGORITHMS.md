# Algorithms (Skeleton)

## Joint Angle Math (2D)
- v1 = A − J, v2 = B − J; angle = arccos(clamp(dot(v1,v2)/(||v1||·||v2||), −1, 1)).
- ε guard; NaN if degenerate.

## Filters
- EMA and 1‑Euro (placeholders).

## Gait Logic
- Heel‑strike from ankle vertical minima; cadence/step time; normalization by hip width.

## Rep Segmentation & Scoring
- Zero‑crossings in angle velocity; banded scoring ±5°/±10°; stability term.
