import json
from pathlib import Path

from speaker_mapping import find_best_speaker_mapping


def load_diarization_result(diarization_json_path):
    """Загружает JSON с результатом диаризации."""

    diarization_json_path = Path(diarization_json_path)
    with diarization_json_path.open("r", encoding="utf-8") as file:
        result = json.load(file)

    segments = result.get("segments")
    audio_file = result.get("audio_file")
    if not isinstance(segments, list):
        raise ValueError("В JSON результата диаризации отсутствует список segments.")
    if not audio_file:
        raise ValueError("В JSON результата диаризации отсутствует audio_file.")

    return segments, str(audio_file)


def clip_interval(start, end, time_offset, fragment_duration):
    """Сдвигает интервал и обрезает его по границам аудиофрагмента."""

    clipped_start = max(0.0, start - time_offset)
    clipped_end = min(fragment_duration, end - time_offset)
    if clipped_end <= clipped_start:
        return None
    return clipped_start, clipped_end


def map_and_save_reference(
    reference_segments,
    diarization_segments,
    audio_file,
    reference_type,
    output_dir,
):
    """Сопоставляет говорящих и сохраняет эталонную разметку в JSON."""

    if not reference_segments:
        raise ValueError("В выбранном фрагменте отсутствует эталонная речь.")

    reference_speakers = sorted(
        {segment["speaker"] for segment in reference_segments}
    )
    diarization_speakers = sorted(
        {segment["speaker"] for segment in diarization_segments}
    )
    speaker_mapping, matched_overlap = find_best_speaker_mapping(
        reference_segments,
        diarization_segments,
    )

    print("Автоматический маппинг говорящих:")
    for speaker in reference_speakers:
        print(
            f"{speaker} -> {speaker_mapping[speaker]} "
            f"({matched_overlap[speaker]:.3f} с совпадения)"
        )

    for segment in reference_segments:
        segment["speaker"] = speaker_mapping[segment["speaker"]]

    reference_segments.sort(
        key=lambda item: (item["start"], item["end"], item["speaker"])
    )
    result = {"audio_file": audio_file, "segments": reference_segments}

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    speaker_count_status = (
        "correct"
        if len(diarization_speakers) == len(reference_speakers)
        else "incorrect"
    )
    output_name = (
        f"{Path(audio_file).stem}_reference_by_{reference_type}_"
        f"{speaker_count_status}_num_speakers_"
        f"{len(diarization_speakers)}.json"
    )
    output_path = output_dir / output_name
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)

    print(f"Готово. Сохранено речевых интервалов: {len(reference_segments)}")
    print(f"JSON-файл: {output_path.resolve()}")
    return output_path
