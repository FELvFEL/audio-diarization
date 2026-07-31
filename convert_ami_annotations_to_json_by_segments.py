"""Преобразование ручной разметки одной встречи AMI из NXT XML в JSON по целым сегментам речи (большие пробелы не разрывают речь)."""

import json
import xml.etree.ElementTree as ET
from pathlib import Path


# Путь к каталогу, содержащему папки segments и words.
ANNOTATIONS_DIR = Path(r"content/AMI_ES2002a_manual")


def collect_non_speech(words_path):
    """Возвращает интервалы смеха, свиста и других неречевых элементов"""

    intervals = []
    root = ET.parse(words_path).getroot()

    for node in root:
        tag = node.tag.split("}")[-1]
        if tag == "w":
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


def subtract_intervals(start, end, excluded):
    """Вычитает неречевые интервалы из речевого сегмента."""

    pieces = [(start, end)]

    for excluded_start, excluded_end in sorted(excluded):
        new_pieces = []

        for piece_start, piece_end in pieces:
            if excluded_end <= piece_start or excluded_start >= piece_end:
                new_pieces.append((piece_start, piece_end))
                continue

            if piece_start < excluded_start:
                new_pieces.append((piece_start, excluded_start))
            if excluded_end < piece_end:
                new_pieces.append((excluded_end, piece_end))

        pieces = new_pieces

    return pieces


segments_dir = ANNOTATIONS_DIR / "segments"
words_dir = ANNOTATIONS_DIR / "words"

if not segments_dir.is_dir():
    raise FileNotFoundError(f"Не найден каталог: {segments_dir}")
if not words_dir.is_dir():
    raise FileNotFoundError(f"Не найден каталог: {words_dir}")

segment_files = sorted(segments_dir.glob("*.segments.xml"))
if not segment_files:
    raise FileNotFoundError(f"В каталоге {segments_dir} нет файлов *.segments.xml")

meeting = segment_files[0].name.split(".")[0]
meeting_segment_files = segment_files
speakers = sorted(
    {path.name.split(".")[1] for path in meeting_segment_files}
)

print(f"Встреча: {meeting}")
print(f"Участники эталонной разметки: {', '.join(speakers)}")

audio_file = input("Введите имя аудиофайла с расширением: ").strip()
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
    name = input(f"Введите имя для участника {speaker}: ").strip()
    if not name:
        raise ValueError(f"Имя для участника {speaker} не введено.")
    if name in speaker_names.values():
        raise ValueError(f"Имя {name!r} введено более одного раза.")
    speaker_names[speaker] = name

result_segments = []

for segment_path in meeting_segment_files:
    speaker = segment_path.name.split(".")[1]
    words_path = words_dir / f"{meeting}.{speaker}.words.xml"

    if not words_path.is_file():
        raise FileNotFoundError(
            f"Не найдена пословная разметка участника {speaker}: {words_path}"
        )

    non_speech = collect_non_speech(words_path)
    root = ET.parse(segment_path).getroot()

    for segment in root.findall("segment"):
        start = float(segment.attrib["transcriber_start"])
        end = float(segment.attrib["transcriber_end"])

        for piece_start, piece_end in subtract_intervals(
            start,
            end,
            non_speech,
        ):
            shifted_start = piece_start - time_offset
            shifted_end = piece_end - time_offset

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
output_path = output_dir / f"{Path(audio_file).stem}.json"
with output_path.open("w", encoding="utf-8") as file:
    json.dump(result, file, ensure_ascii=False, indent=2)

print(f"Готово. Сохранено сегментов: {len(result_segments)}")
print(f"JSON-файл: {output_path.resolve()}")
