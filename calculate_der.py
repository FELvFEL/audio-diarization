from pathlib import Path

from convert_ami_annotations_to_json_by_segments import (
    convert_annotations_by_segments,
)
from convert_ami_annotations_to_json_by_words_trancription import (
    convert_annotations_by_words,
)
from convert_icsi_annotations_to_json_by_segments import (
    convert_icsi_annotations_by_segments,
)
from convert_icsi_annotations_to_json_by_words import (
    convert_icsi_annotations_by_words,
)
from diarization_metrics import evaluate_diarization, print_results


def read_number(prompt):
    """Считывает число, разрешая точку или запятую как разделитель."""

    return float(input(prompt).strip().replace(",", "."))


def main():
    print("Выберите источник эталонной разметки:")
    print("1 - AMI")
    print("2 - ICSI")
    source = input("Введите 1 или 2: ").strip()
    if source not in {"1", "2"}:
        raise ValueError("Нужно выбрать 1 или 2.")

    source_name = "AMI" if source == "1" else "ICSI"
    meeting = input(f"Введите имя встречи {source_name}: ").strip()
    diarization_json_path = Path(
        input("Введите путь к JSON-файлу результата диаризации: ")
        .strip()
        .strip('"')
    )

    print("Выберите способ построения эталонной разметки:")
    print("1 - на основе слов")
    print("2 - на основе сегментов")
    conversion_type = input("Введите 1 или 2: ").strip()
    if conversion_type not in {"1", "2"}:
        raise ValueError("Нужно выбрать 1 или 2.")

    time_offset = read_number("Введите сдвиг от начала записи в секундах: ")
    fragment_duration = read_number(
        "Введите длительность фрагмента в секундах: "
    )

    if time_offset < 0:
        raise ValueError("Сдвиг не может быть отрицательным.")
    if fragment_duration <= 0:
        raise ValueError("Длительность фрагмента должна быть больше нуля.")

    if source == "1" and conversion_type == "1":
        reference_json_path = convert_annotations_by_words(
            meeting,
            diarization_json_path,
            time_offset,
            fragment_duration,
        )
    elif source == "1":
        reference_json_path = convert_annotations_by_segments(
            meeting,
            diarization_json_path,
            time_offset,
            fragment_duration,
        )
    elif source == "2" and conversion_type == "1":
        reference_json_path = convert_icsi_annotations_by_words(
            meeting,
            diarization_json_path,
            time_offset,
            fragment_duration,
        )
    else:
        reference_json_path = convert_icsi_annotations_by_segments(
            meeting,
            diarization_json_path,
            time_offset,
            fragment_duration,
        )

    reference, metrics, jer_by_speaker, mean_jer = evaluate_diarization(
        reference_json_path,
        diarization_json_path,
    )
    print_results(reference, metrics, jer_by_speaker, mean_jer)


if __name__ == "__main__":
    main()
