"""Расчёт DER по эталонной и полученной моделью диаризации."""

import json
from pathlib import Path


# Пути к сравниваемым JSON-файлам.
REFERENCE_JSON_PATH = Path(
    r"content/reference_json_files/ES2002a__1060sec_reference_by_words_incorrect_num_speakers_5.json"
)
DIARIZATION_JSON_PATH = Path(
    r"content/diarization_json_files/pyannotate/speaker-diarization-community-1/ES2002a_1060sec_incorrect_num_speakers_5.json"
)


def load_segments(json_path):
    """Загружает сегменты и группирует интервалы по говорящим."""

    with json_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    intervals_by_speaker = {}
    for segment in data["segments"]:
        start = float(segment["start"])
        end = float(segment["end"])
        speaker = str(segment["speaker"])

        if end <= start:
            continue

        intervals_by_speaker.setdefault(speaker, []).append((start, end))

    return {
        speaker: merge_intervals(intervals)
        for speaker, intervals in intervals_by_speaker.items()
    }


def merge_intervals(intervals):
    """Объединяет пересекающиеся интервалы одного говорящего."""

    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def active_speakers(intervals_by_speaker, moment):
    """Возвращает множество говорящих, активных в указанный момент."""

    return {
        speaker
        for speaker, intervals in intervals_by_speaker.items()
        if any(start <= moment < end for start, end in intervals)
    }


def calculate_der(reference, hypothesis):
    """Вычисляет компоненты DER по всем элементарным интервалам."""

    boundaries = sorted(
        {
            time
            for intervals_by_speaker in (reference, hypothesis)
            for intervals in intervals_by_speaker.values()
            for interval in intervals
            for time in interval
        }
    )

    reference_speech = 0.0
    missed_speech = 0.0
    false_alarm = 0.0
    speaker_confusion = 0.0

    for start, end in zip(boundaries, boundaries[1:]):
        duration = end - start
        if duration <= 0:
            continue

        moment = (start + end) / 2
        reference_active = active_speakers(reference, moment)
        hypothesis_active = active_speakers(hypothesis, moment)

        reference_count = len(reference_active)
        hypothesis_count = len(hypothesis_active)
        correct_count = len(reference_active & hypothesis_active)

        reference_speech += reference_count * duration
        missed_speech += max(
            0,
            reference_count - hypothesis_count,
        ) * duration
        false_alarm += max(
            0,
            hypothesis_count - reference_count,
        ) * duration
        speaker_confusion += (
            min(reference_count, hypothesis_count) - correct_count
        ) * duration

    if reference_speech == 0:
        raise ValueError("В эталонной разметке отсутствует речь.")

    der = (
        missed_speech + false_alarm + speaker_confusion
    ) / reference_speech

    return {
        "reference_speech": reference_speech,
        "missed_speech": missed_speech,
        "false_alarm": false_alarm,
        "speaker_confusion": speaker_confusion,
        "der": der,
    }


reference = load_segments(REFERENCE_JSON_PATH)
hypothesis = load_segments(DIARIZATION_JSON_PATH)
metrics = calculate_der(reference, hypothesis)

print(f"Эталонная речь: {metrics['reference_speech']:.3f} с")
print(
    f"Пропуск речи: {metrics['missed_speech']:.3f} с "
    f"({metrics['missed_speech'] / metrics['reference_speech'] * 100:.3f}%)"
)
print(
    f"Ложная речь: {metrics['false_alarm']:.3f} с "
    f"({metrics['false_alarm'] / metrics['reference_speech'] * 100:.3f}%)'"
)
print(
    f"Путаница говорящих: {metrics['speaker_confusion']:.3f} с "
    f"({metrics['speaker_confusion'] / metrics['reference_speech'] * 100:.3f}%)"
)
print(f"DER: {metrics['der'] * 100:.3f}%")
