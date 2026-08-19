import xml.etree.ElementTree as ET
from pathlib import Path

from ami_annotations_download import download_meeting_annotations
from reference_json import (
    clip_interval,
    load_diarization_result,
    map_and_save_reference,
)


def collect_non_speech(words_path):
    """Возвращает интервалы смеха, свиста и других неречевых элементов."""

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


def convert_annotations_by_segments(
    meeting,
    diarization_json_path,
    time_offset,
    fragment_duration,
    output_dir=Path("content/reference_json_files"),
):
    """Создаёт эталонный JSON по сегментной разметке AMI."""

    diarization_segments, audio_file = load_diarization_result(
        diarization_json_path
    )

    with download_meeting_annotations(meeting, {"segments", "words"}) as annotations_dir:
        segments_dir = annotations_dir / "segments"
        words_dir = annotations_dir / "words"
        meeting_segment_files = sorted(
            segments_dir.glob(f"{meeting}.*.segments.xml")
        )
        result_segments = []

        for segment_path in meeting_segment_files:
            speaker = segment_path.name.split(".")[1]
            words_path = words_dir / f"{meeting}.{speaker}.words.xml"
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
                    clipped = clip_interval(
                        piece_start,
                        piece_end,
                        time_offset,
                        fragment_duration,
                    )
                    if clipped is None:
                        continue
                    clipped_start, clipped_end = clipped

                    result_segments.append(
                        {
                            "start": round(clipped_start, 3),
                            "end": round(clipped_end, 3),
                            "speaker": speaker,
                        }
                    )

    return map_and_save_reference(
        result_segments,
        diarization_segments,
        audio_file,
        "segments",
        output_dir,
    )


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
    convert_annotations_by_segments(
        meeting,
        diarization_json_path,
        time_offset,
        fragment_duration,
    )


if __name__ == "__main__":
    main()
