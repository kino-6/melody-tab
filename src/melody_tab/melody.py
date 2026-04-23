"""Melody extraction and cleanup heuristics for post-processing MIDI notes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from melody_tab.models import NoteEvent

MELODY_MIN_MIDI = 40  # E2
MELODY_MAX_MIDI = 88  # E6


@dataclass(slots=True)
class MelodyConfig:
    """Tuneable parameters for melody cleanup and selection."""

    mode: Literal["highest", "duration", "balanced"] = "balanced"
    min_note_ms: float = 90.0
    max_jump_semitones: int = 12
    preferred_low_midi: int = 55
    preferred_high_midi: int = 75
    duration_weight: float = 2.8
    jump_penalty_weight: float = 0.22
    out_of_range_penalty_weight: float = 0.7
    octave_shift_outliers: bool = True
    merge_gap_ms: float = 60.0
    time_slice_ms: float = 70.0


@dataclass(slots=True)
class MelodyStats:
    """Counters useful for reporting in output headers."""

    raw_notes: int = 0
    dropped_short: int = 0
    merged_repeats: int = 0
    octave_shifted: int = 0
    dropped_unplayable: int = 0


@dataclass(slots=True)
class MelodyDecision:
    """Per-slice debug details."""

    slice_start: float
    candidate_midis: list[int]
    selected_midi: int | None
    score_details: list[str] = field(default_factory=list)
    dropped_reasons: list[str] = field(default_factory=list)


def clamp_to_range_with_octave(midi: int, low: int, high: int) -> tuple[int | None, bool]:
    """Try octave shifts to fit a note into [low, high]."""
    if low <= midi <= high:
        return midi, False
    shifted = midi
    changed = False
    while shifted < low:
        shifted += 12
        changed = True
    while shifted > high:
        shifted -= 12
        changed = True
    if low <= shifted <= high:
        return shifted, changed
    return None, changed


def _preclean_notes(
    events: list[NoteEvent], config: MelodyConfig, low: int = MELODY_MIN_MIDI, high: int = MELODY_MAX_MIDI
) -> tuple[list[NoteEvent], MelodyStats, list[str]]:
    stats = MelodyStats(raw_notes=len(events))
    debug: list[str] = []
    cleaned: list[NoteEvent] = []

    min_note_sec = config.min_note_ms / 1000.0
    for ev in sorted(events, key=lambda n: (n.onset, n.midi, n.offset)):
        if ev.duration < min_note_sec:
            stats.dropped_short += 1
            debug.append(f"drop short: midi={ev.midi} start={ev.onset:.3f} dur={ev.duration:.3f}")
            continue

        midi = ev.midi
        shifted = False
        if config.octave_shift_outliers:
            shifted_midi, shifted = clamp_to_range_with_octave(ev.midi, low, high)
            if shifted_midi is None:
                stats.dropped_unplayable += 1
                debug.append(f"drop out-range: midi={ev.midi} start={ev.onset:.3f}")
                continue
            midi = shifted_midi
            if shifted:
                stats.octave_shifted += 1
                debug.append(f"octave-shift: {ev.midi}->{midi} at {ev.onset:.3f}s")
        elif not (low <= ev.midi <= high):
            stats.dropped_unplayable += 1
            debug.append(f"drop out-range (no shift): midi={ev.midi} start={ev.onset:.3f}")
            continue

        cleaned.append(NoteEvent(midi=midi, name=ev.name, onset=ev.onset, offset=ev.offset))

    # merge near-identical adjacent notes
    merged: list[NoteEvent] = []
    merge_gap_sec = config.merge_gap_ms / 1000.0
    for ev in cleaned:
        if merged and merged[-1].midi == ev.midi and ev.onset - merged[-1].offset <= merge_gap_sec:
            prev = merged[-1]
            merged[-1] = NoteEvent(midi=prev.midi, name=prev.name, onset=prev.onset, offset=max(prev.offset, ev.offset))
            stats.merged_repeats += 1
            debug.append(f"merge repeat: midi={ev.midi} around {ev.onset:.3f}s")
        else:
            merged.append(ev)

    return merged, stats, debug


def _build_time_slices(events: list[NoteEvent], slice_sec: float) -> list[tuple[float, list[NoteEvent]]]:
    if not events:
        return []
    slices: list[tuple[float, list[NoteEvent]]] = []
    start = min(e.onset for e in events)
    end = max(e.offset for e in events)
    t = start
    while t <= end + 1e-8:
        active = [ev for ev in events if ev.onset <= t < ev.offset]
        if active:
            slices.append((t, active))
        t += slice_sec
    return slices


def _out_of_range_penalty(cand_midi: int, preferred_low: int, preferred_high: int, penalty_weight: float) -> float:
    if preferred_low <= cand_midi <= preferred_high:
        return 0.0
    if cand_midi < preferred_low:
        return (preferred_low - cand_midi) * penalty_weight
    return (cand_midi - preferred_high) * penalty_weight


def _score_candidate(
    cand: NoteEvent,
    config: MelodyConfig,
) -> tuple[float, list[str]]:
    details: list[str] = []
    score = 0.0

    dur_score = cand.duration * config.duration_weight
    score += dur_score
    details.append(f"dur={dur_score:.2f}")

    range_pen = _out_of_range_penalty(
        cand_midi=cand.midi,
        preferred_low=config.preferred_low_midi,
        preferred_high=config.preferred_high_midi,
        penalty_weight=config.out_of_range_penalty_weight,
    )
    score -= range_pen
    details.append(f"range_pen=-{range_pen:.2f}")

    if config.mode == "highest":
        high_bonus = cand.midi * 0.04
        score += high_bonus
        details.append(f"highest={high_bonus:.2f}")
    elif config.mode == "duration":
        duration_bonus = cand.duration * 0.6
        score += duration_bonus
        details.append(f"dur_mode={duration_bonus:.2f}")
    else:
        center = (config.preferred_low_midi + config.preferred_high_midi) / 2.0
        bal_bonus = max(0.0, 0.4 - (abs(cand.midi - center) * 0.04))
        score += bal_bonus
        details.append(f"bal_pitch={bal_bonus:.2f}")

    return score, details


def _jump_penalty(curr_midi: int, prev_midi: int, config: MelodyConfig) -> float:
    jump = abs(curr_midi - prev_midi)
    base_penalty = jump * config.jump_penalty_weight
    overflow_penalty = max(0, jump - config.max_jump_semitones) * (config.jump_penalty_weight * 2.0)
    return base_penalty + overflow_penalty


def extract_melody(
    events: list[NoteEvent],
    config: MelodyConfig,
    low: int = MELODY_MIN_MIDI,
    high: int = MELODY_MAX_MIDI,
) -> tuple[list[NoteEvent], MelodyStats, list[MelodyDecision], list[str]]:
    """Extract a single-note melody from noisy/polyphonic note events."""
    cleaned, stats, cleanup_debug = _preclean_notes(events, config, low=low, high=high)
    slices = _build_time_slices(cleaned, config.time_slice_ms / 1000.0)

    decisions: list[MelodyDecision] = []
    melody_points: list[tuple[float, int]] = []

    if not slices:
        return [], stats, decisions, cleanup_debug

    dp: list[list[float]] = []
    back: list[list[int]] = []

    for i, (slice_start, candidates) in enumerate(slices):
        row_scores = [-1e18] * len(candidates)
        row_back = [-1] * len(candidates)
        score_rows: list[str] = []
        for j, cand in enumerate(candidates):
            base_score, details = _score_candidate(cand, config=config)
            if i == 0:
                row_scores[j] = base_score
            else:
                best_prev_score = -1e18
                best_prev_idx = -1
                for k, prev_cand in enumerate(slices[i - 1][1]):
                    jump_pen = _jump_penalty(cand.midi, prev_cand.midi, config)
                    total = dp[i - 1][k] + base_score - jump_pen
                    if total > best_prev_score:
                        best_prev_score = total
                        best_prev_idx = k
                row_scores[j] = best_prev_score
                row_back[j] = best_prev_idx
                details.append(f"jump_pen=-{_jump_penalty(cand.midi, slices[i - 1][1][best_prev_idx].midi, config):.2f}")

            score_rows.append(f"midi={cand.midi} score={row_scores[j]:.2f} ({', '.join(details)})")

        dp.append(row_scores)
        back.append(row_back)
        best_idx = max(range(len(candidates)), key=lambda idx: row_scores[idx])
        selected = candidates[best_idx].midi if candidates else None
        decisions.append(
            MelodyDecision(
                slice_start=slice_start,
                candidate_midis=[c.midi for c in candidates],
                selected_midi=selected,
                score_details=score_rows,
            )
        )

    final_i = len(slices) - 1
    final_j = max(range(len(slices[final_i][1])), key=lambda idx: dp[final_i][idx])
    chosen_per_slice: list[int] = [0] * len(slices)
    j = final_j
    for i in range(final_i, -1, -1):
        chosen_per_slice[i] = j
        j = back[i][j] if i > 0 else -1

    for i, (slice_start, candidates) in enumerate(slices):
        selected = candidates[chosen_per_slice[i]].midi
        decisions[i].selected_midi = selected
        if not melody_points or melody_points[-1][1] != selected:
            melody_points.append((slice_start, selected))

    # rebuild note events from selected melody points
    melody: list[NoteEvent] = []
    for i, (start, midi) in enumerate(melody_points):
        end = melody_points[i + 1][0] if i + 1 < len(melody_points) else start + (config.time_slice_ms / 1000.0)
        if end <= start:
            end = start + (config.time_slice_ms / 1000.0)
        melody.append(NoteEvent(midi=midi, name=f"M{midi}", onset=start, offset=end))

    return melody, stats, decisions, cleanup_debug


def format_melody_debug(decisions: list[MelodyDecision], cleanup_lines: list[str]) -> str:
    """Render human-readable debug details for tuning heuristics."""
    out: list[str] = ["# cleanup", *cleanup_lines, "", "# slices"]
    for d in decisions:
        out.append(f"t={d.slice_start:.3f}s candidates={d.candidate_midis} selected={d.selected_midi}")
        for row in d.score_details:
            out.append(f"  - {row}")
        for row in d.dropped_reasons:
            out.append(f"  x {row}")
    return "\n".join(out)
