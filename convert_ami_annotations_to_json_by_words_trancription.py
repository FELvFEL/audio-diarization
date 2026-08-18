"""Преобразование пословной разметки встречи AMI из NXT XML в JSON."""

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from ami_annotations_download import download_meeting_annotations
from speaker_mapping import find_best_speaker_mapping


def collect_word_intervals(words_path):
    """Возвращает временные интервалы слов из элементов <w>."""

    intervals = []
    root = ET.parse(words_path).getroot()

    for node in root:
        tag = node.tag.split("}")[-1]
        if tag != "w":
            continue

        start_text = node.attrib.get("starttime")
        end_text = node.attrib.get("endtime")
        if start_text is None or end_text is None:
            continue

        start = float(start_text)
        end = float(end_text)
        if end > start:
            intervals.append((start, end))

    return intervals


def merge_touching_intervals(intervals):
    """Объединяет соприкасающиеся и пересекающиеся интервалы слов."""

    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def convert_annotations_by_words(
    meeting,
    diarization_json_path,
    time_offset,
    fragment_duration,
    output_dir=Path("content/reference_json_files"),
):
    """Создаёт эталонный JSON по пословной разметке AMI."""

    diarization_json_path = Path(diarization_json_path)
    with diarization_json_path.open("r", encoding="utf-8") as file:
        diarization_result = json.load(file)

    diarization_segments = diarization_result["segments"]
    audio_file = diarization_result["audio_file"]
    diarization_speaker_count = len(
        {segment["speaker"] for segment in diarization_segments}
    )

    with download_meeting_annotations(meeting, {"words"}) as annotations_dir:
        words_dir = annotations_dir / "words"
        word_files = sorted(words_dir.glob(f"{meeting}.*.words.xml"))
        speakers = sorted({path.name.split(".")[1] for path in word_files})
        result_segments = []

        for words_path in word_files:
            speaker = words_path.name.split(".")[1]
            word_intervals = collect_word_intervals(words_path)

            for start, end in merge_touching_intervals(word_intervals):
                shifted_start = start - time_offset
                shifted_end = end - time_offset
                clipped_start = max(0.0, shifted_start)
                clipped_end = min(fragment_duration, shifted_end)

                if clipped_end <= clipped_start:
                    continue

                result_segments.append(
                    {
                        "start": round(clipped_start, 3),
                        "end": round(clipped_end, 3),
                        "speaker": speaker,
                    }
                )

    speaker_mapping, matched_overlap = find_best_speaker_mapping(
        result_segments,
        diarization_segments,
    )
    print("Автоматический маппинг говорящих:")
    for speaker in speakers:
        print(
            f"{speaker} -> {speaker_mapping[speaker]} "
            f"({matched_overlap[speaker]:.3f} с совпадения)"
        )

    for segment in result_segments:
        segment["speaker"] = speaker_mapping[segment["speaker"]]

    result_segments.sort(
        key=lambda item: (item["start"], item["end"], item["speaker"])
    )
    result = {"audio_file": audio_file, "segments": result_segments}

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    speaker_count_status = (
        "correct" if diarization_speaker_count == len(speakers) else "incorrect"
    )
    output_name = (
        f"{Path(audio_file).stem}_reference_by_words_"
        f"{speaker_count_status}_num_speakers_"
        f"{diarization_speaker_count}.json"
    )
    output_path = output_dir / output_name
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)

    print(f"Готово. Сохранено речевых интервалов: {len(result_segments)}")
    print(f"JSON-файл: {output_path.resolve()}")
    return output_path


def main():
    meeting = input("Введите имя встречи AMI: ").strip()
    diarization_json_path = Path(
        input("Введите путь к JSON-файлу результата диаризации: ").strip()
    )
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
    convert_annotations_by_words(
        meeting,
        diarization_json_path,
        time_offset,
        fragment_duration,
    )


if __name__ == "__main__":
    main()
