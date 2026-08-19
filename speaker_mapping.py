from functools import lru_cache


def merge_speaker_intervals(segments, speaker):
    intervals = sorted(
        (float(item["start"]), float(item["end"]))
        for item in segments
        if item["speaker"] == speaker and float(item["end"]) > float(item["start"])
    )
    merged = []

    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    return merged


def intersection_duration(first_intervals, second_intervals):
    total = 0.0
    first_index = 0
    second_index = 0

    while first_index < len(first_intervals) and second_index < len(second_intervals):
        first_start, first_end = first_intervals[first_index]
        second_start, second_end = second_intervals[second_index]

        total += max(0.0, min(first_end, second_end) - max(first_start, second_start))

        if first_end <= second_end:
            first_index += 1
        else:
            second_index += 1

    return total


def find_best_speaker_mapping(reference_segments, diarization_segments):
    reference_speakers = sorted({item["speaker"] for item in reference_segments})
    diarization_speakers = sorted({item["speaker"] for item in diarization_segments})

    if not reference_speakers:
        raise ValueError("В эталонной разметке отсутствуют говорящие.")
    if len(diarization_speakers) < len(reference_speakers):
        raise ValueError(
            "В результате диаризации меньше говорящих, чем в эталонной разметке."
        )

    reference_intervals = {
        speaker: merge_speaker_intervals(reference_segments, speaker)
        for speaker in reference_speakers
    }
    diarization_intervals = {
        speaker: merge_speaker_intervals(diarization_segments, speaker)
        for speaker in diarization_speakers
    }
    overlap = {
        (reference_speaker, diarization_speaker): intersection_duration(
            reference_intervals[reference_speaker],
            diarization_intervals[diarization_speaker],
        )
        for reference_speaker in reference_speakers
        for diarization_speaker in diarization_speakers
    }

    @lru_cache(maxsize=None)
    def find_best_order(reference_index, used_diarization_indexes):
        if reference_index == len(reference_speakers):
            return 0.0, ()

        reference_speaker = reference_speakers[reference_index]
        best_score = None
        best_order = None

        for diarization_index, diarization_speaker in enumerate(diarization_speakers):
            if diarization_index in used_diarization_indexes:
                continue

            remaining_score, remaining_order = find_best_order(
                reference_index + 1,
                used_diarization_indexes | frozenset({diarization_index}),
            )
            score = overlap[(reference_speaker, diarization_speaker)] + remaining_score
            order = (diarization_speaker,) + remaining_order

            if (
                best_score is None
                or score > best_score
                or (score == best_score and order < best_order)
            ):
                best_score = score
                best_order = order

        return best_score, best_order

    _, best_diarization_order = find_best_order(0, frozenset())
    mapping = dict(zip(reference_speakers, best_diarization_order))
    matched_overlap = {
        reference_speaker: overlap[(reference_speaker, mapping[reference_speaker])]
        for reference_speaker in reference_speakers
    }

    return mapping, matched_overlap
