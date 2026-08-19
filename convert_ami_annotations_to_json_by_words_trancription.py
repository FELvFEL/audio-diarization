from pathlib import Path

from ami_annotations_download import download_meeting_annotations
from reference_json import (
    clip_interval,
    load_diarization_result,
    map_and_save_reference,
)
from word_intervals import collect_word_intervals, merge_touching_intervals


def convert_annotations_by_words(
    meeting,
    diarization_json_path,
    time_offset,
    fragment_duration,
    output_dir=Path("content/reference_json_files"),
):
    """Создаёт эталонный JSON по пословной разметке AMI."""

    diarization_segments, audio_file = load_diarization_result(
        diarization_json_path
    )

    with download_meeting_annotations(meeting, {"words"}) as annotations_dir:
        words_dir = annotations_dir / "words"
        word_files = sorted(words_dir.glob(f"{meeting}.*.words.xml"))
        result_segments = []

        for words_path in word_files:
            speaker = words_path.name.split(".")[1]
            word_intervals = collect_word_intervals(words_path)

            for start, end in merge_touching_intervals(word_intervals):
                clipped = clip_interval(
                    start,
                    end,
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
        "words",
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
    convert_annotations_by_words(
        meeting,
        diarization_json_path,
        time_offset,
        fragment_duration,
    )


if __name__ == "__main__":
    main()
