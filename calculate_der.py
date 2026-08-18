import json
from pathlib import Path

from convert_ami_annotations_to_json_by_segments import (
    convert_annotations_by_segments,
)
from convert_ami_annotations_to_json_by_words_trancription import (
    convert_annotations_by_words,
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


def intervals_duration(intervals):
    """Возвращает суммарную длительность непересекающихся интервалов."""

    return sum(end - start for start, end in intervals)


def intersection_duration(first_intervals, second_intervals):
    """Возвращает длительность пересечения двух наборов интервалов."""

    intersection = 0.0
    first_index = 0
    second_index = 0

    while (
        first_index < len(first_intervals)
        and second_index < len(second_intervals)
    ):
        first_start, first_end = first_intervals[first_index]
        second_start, second_end = second_intervals[second_index]

        overlap_start = max(first_start, second_start)
        overlap_end = min(first_end, second_end)
        if overlap_end > overlap_start:
            intersection += overlap_end - overlap_start

        if first_end <= second_end:
            first_index += 1
        else:
            second_index += 1

    return intersection


def calculate_jer(reference, hypothesis):
    """Вычисляет JER каждого эталонного говорящего и средний JER."""

    jer_by_speaker = {}

    for speaker, reference_intervals in sorted(reference.items()):
        hypothesis_intervals = hypothesis.get(speaker, [])
        intersection = intersection_duration(
            reference_intervals,
            hypothesis_intervals,
        )
        union = (
            intervals_duration(reference_intervals)
            + intervals_duration(hypothesis_intervals)
            - intersection
        )
        jer_by_speaker[speaker] = 1.0 - intersection / union

    if not jer_by_speaker:
        raise ValueError("В эталонной разметке отсутствуют говорящие.")

    mean_jer = sum(jer_by_speaker.values()) / len(jer_by_speaker)
    return jer_by_speaker, mean_jer


def evaluate_diarization(reference_json_path, diarization_json_path):
    """Вычисляет DER и JER для двух JSON-файлов."""

    reference = load_segments(reference_json_path)
    hypothesis = load_segments(diarization_json_path)
    metrics = calculate_der(reference, hypothesis)
    jer_by_speaker, mean_jer = calculate_jer(reference, hypothesis)
    return reference, metrics, jer_by_speaker, mean_jer


def print_results(reference, metrics, jer_by_speaker, mean_jer):
    """Выводит результаты расчёта DER и JER."""

    print()
    print(f"Эталонная речь: {metrics['reference_speech']:.3f} с")
    print(
        f"Пропуск речи: {metrics['missed_speech']:.3f} с "
        f"({metrics['missed_speech'] / metrics['reference_speech'] * 100:.3f}%)"
    )
    print(
        f"Ложная речь: {metrics['false_alarm']:.3f} с "
        f"({metrics['false_alarm'] / metrics['reference_speech'] * 100:.3f}%)"
    )
    print(
        f"Путаница говорящих: {metrics['speaker_confusion']:.3f} с "
        f"({metrics['speaker_confusion'] / metrics['reference_speech'] * 100:.3f}%)"
    )
    print(f"DER: {metrics['der'] * 100:.3f}%")
    print()

    for speaker, jer in jer_by_speaker.items():
        speaker_speech = intervals_duration(reference[speaker])
        speech_percentage = speaker_speech / metrics["reference_speech"] * 100
        print(
            f"{speaker}: речь {speaker_speech:.3f} с "
            f"({speech_percentage:.3f}% эталонной речи), "
            f"JER {jer * 100:.3f}%"
        )
    print(f"Средний JER: {mean_jer * 100:.3f}%")


def main():
    meeting = input("Введите имя встречи AMI: ").strip()
    diarization_json_path = Path(
        input("Введите путь к JSON-файлу результата диаризации: ")
        .strip()
        .strip('"')
    )

    print("Выберите способ построения эталонной разметки:")
    print("1 - на основе слов")
    print("2 - на основе сегментов")
    conversion_type = input("Введите 1 или 2: ").strip()

    time_offset = float(
        input("Введите сдвиг от начала записи в секундах: ")
        .strip()
        .replace(",", ".")
    )
    fragment_duration = float(
        input("Введите длительность фрагмента в секундах: ")
        .strip()
        .replace(",", ".")
    )

    if time_offset < 0:
        raise ValueError("Сдвиг не может быть отрицательным.")
    if fragment_duration <= 0:
        raise ValueError("Длительность фрагмента должна быть больше нуля.")

    if conversion_type == "1":
        reference_json_path = convert_annotations_by_words(
            meeting,
            diarization_json_path,
            time_offset,
            fragment_duration,
        )
    elif conversion_type == "2":
        reference_json_path = convert_annotations_by_segments(
            meeting,
            diarization_json_path,
            time_offset,
            fragment_duration,
        )
    else:
        raise ValueError("Нужно выбрать 1 или 2.")

    reference, metrics, jer_by_speaker, mean_jer = evaluate_diarization(
        reference_json_path,
        diarization_json_path,
    )
    print_results(reference, metrics, jer_by_speaker, mean_jer)


if __name__ == "__main__":
    main()
