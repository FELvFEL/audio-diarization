import xml.etree.ElementTree as ET
from pathlib import Path

from icsi_annotations_download import download_icsi_annotations
from reference_json import (
    clip_interval,
    load_diarization_result,
    map_and_save_reference,
)


def convert_icsi_annotations_by_segments(
    meeting,
    diarization_json_path,
    time_offset,
    fragment_duration,
    output_dir=Path("content/reference_json_files"),
):
    """Создаёт эталонный JSON по сегментной разметке ICSI."""

    diarization_segments, audio_file = load_diarization_result(
        diarization_json_path
    )

    with download_icsi_annotations(meeting, {"Segments"}) as annotations_dir:
        segments_dir = annotations_dir / "Segments"
        meeting_segment_files = sorted(
            path
            for path in segments_dir.glob("*.segs.xml")
            if path.name.split(".")[0].lower() == meeting.lower()
        )
        result_segments = []

        for segment_path in meeting_segment_files:
            speaker = segment_path.name.split(".")[1]
            root = ET.parse(segment_path).getroot()

            for segment in root:
                if segment.tag.split("}")[-1] != "segment":
                    continue

                start_text = segment.attrib.get("starttime")
                end_text = segment.attrib.get("endtime")
                if not start_text or not end_text:
                    continue

                start = float(start_text)
                end = float(end_text)
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
        "segments",
        output_dir,
    )
