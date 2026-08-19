import xml.etree.ElementTree as ET


def collect_word_intervals(words_path):
    """Возвращает интервалы слов с заполненными временными метками."""

    intervals = []
    root = ET.parse(words_path).getroot()

    for node in root.iter():
        if node.tag.split("}")[-1] != "w":
            continue

        start_text = node.attrib.get("starttime")
        end_text = node.attrib.get("endtime")
        if not start_text or not end_text:
            continue

        try:
            start = float(start_text)
            end = float(end_text)
        except ValueError:
            continue

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
