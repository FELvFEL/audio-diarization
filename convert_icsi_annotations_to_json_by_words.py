from pathlib import Path

from icsi_annotations_download import download_icsi_annotations
from reference_json import (
    clip_interval,
    load_diarization_result,
    map_and_save_reference,
)
from word_intervals import collect_word_intervals, merge_touching_intervals


def convert_icsi_annotations_by_words(
    meeting,
    diarization_json_path,
    time_offset,
    fragment_duration,
    output_dir=Path("content/reference_json_files"),
):
    """Создаёт эталонный JSON по пословной разметке ICSI."""

    diarization_segments, audio_file = load_diarization_result(
        diarization_json_path
    )

    with download_icsi_annotations(meeting, {"Words"}) as annotations_dir:
        words_dir = annotations_dir / "Words"
        word_files = sorted(
            path
            for path in words_dir.glob("*.words.xml")
            if path.name.split(".")[0].lower() == meeting.lower()
        )
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
