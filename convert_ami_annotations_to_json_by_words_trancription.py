"""Преобразование пословной разметки встречи AMI из NXT XML в JSON, по транскрицпции слов (большие пробелы речи считаются как отсутствие речи)."""

import json
import xml.etree.ElementTree as ET
from pathlib import Path


# Путь к каталогу, содержащему папку words.
ANNOTATIONS_DIR = Path(r"content/AMI_ES2002a_manual")


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

        # Знаки препинания имеют нулевую длительность и не являются речью.
        if end > start:
            intervals.append((start, end))

    return intervals


def merge_touching_intervals(intervals):
    """Объединяет соприкасающиеся и пересекающиеся интервалы слов."""

    merged = []

    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1] = (
                merged[-1][0],
                max(merged[-1][1], end),
            )
        else:
            merged.append((start, end))

    return merged


words_dir = ANNOTATIONS_DIR / "words"
word_files = sorted(words_dir.glob("*.words.xml"))

meeting = word_files[0].name.split(".")[0]
speakers = sorted(
    {path.name.split(".")[1] for path in word_files}
)

print(f"Встреча: {meeting}")
print(f"Участники эталонной разметки: {', '.join(speakers)}")

audio_file = input(
    "Введите имя аудиофайла с расширением: "
).strip()
diarization_speaker_count = int(
    input("Введите число говорящих в результате диаризации: ")
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

speaker_names = {}
for speaker in speakers:
    name = input(
        f"Введите имя для участника {speaker}: "
    ).strip()
    speaker_names[speaker] = name

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
                "speaker": speaker_names[speaker],
            }
        )

result_segments.sort(
    key=lambda item: (
        item["start"],
        item["end"],
        item["speaker"],
    )
)

result = {
    "audio_file": audio_file,
    "segments": result_segments,
}

output_dir = ANNOTATIONS_DIR.parent / "reference_json_files"
output_dir.mkdir(parents=True, exist_ok=True)
speaker_count_status = (
    "correct"
    if diarization_speaker_count == len(speakers)
    else "incorrect"
)
output_name = (
    f"{Path(audio_file).stem}_reference_by_words_"
    f"{speaker_count_status}_num_speakers_"
    f"{diarization_speaker_count}.json"
)
output_path = output_dir / output_name

with output_path.open("w", encoding="utf-8") as file:
    json.dump(result, file, ensure_ascii=False, indent=2)

print(
    f"Готово. Сохранено речевых интервалов: "
    f"{len(result_segments)}"
)
print(f"JSON-файл: {output_path.resolve()}")
