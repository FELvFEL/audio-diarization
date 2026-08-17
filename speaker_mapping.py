from itertools import permutations


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

    best_diarization_order = max(
        permutations(diarization_speakers, len(reference_speakers)),
        key=lambda order: sum(
            overlap[(reference_speaker, diarization_speaker)]
            for reference_speaker, diarization_speaker in zip(
                reference_speakers,
                order,
            )
        ),
    )
    mapping = dict(zip(reference_speakers, best_diarization_order))
    matched_overlap = {
        reference_speaker: overlap[(reference_speaker, mapping[reference_speaker])]
        for reference_speaker in reference_speakers
    }

    return mapping, matched_overlap
