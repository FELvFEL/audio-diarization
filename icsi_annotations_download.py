import shutil
import urllib.request
import zipfile
from contextlib import contextmanager
from pathlib import Path


ICSI_CORE_ANNOTATIONS_URL = "https://groups.inf.ed.ac.uk/ami/ICSICorpusAnnotations/ICSI_core_NXT.zip"


@contextmanager
def download_icsi_annotations(meeting, required_directories):
    annotations_dir = Path("icsi_temp")
    archive_path = annotations_dir / "ICSI_core_NXT.zip"

    if annotations_dir.exists():
        shutil.rmtree(annotations_dir)
    annotations_dir.mkdir()

    try:
        print(f"Скачивание ручной разметки ICSI для встречи {meeting}...")
        urllib.request.urlretrieve(ICSI_CORE_ANNOTATIONS_URL, archive_path)

        with zipfile.ZipFile(archive_path) as archive:
            for member_name in archive.namelist():
                parts = member_name.rstrip("/").split("/")
                if len(parts) < 2:
                    continue

                directory = parts[-2]
                file_name = parts[-1]
                if directory not in required_directories:
                    continue
                if not file_name.lower().startswith(f"{meeting.lower()}."):
                    continue
                expected_suffix = (
                    ".segs.xml" if directory == "Segments" else ".words.xml"
                )
                if not file_name.lower().endswith(expected_suffix):
                    continue

                target_dir = annotations_dir / directory
                target_dir.mkdir(parents=True, exist_ok=True)
                target_path = target_dir / file_name
                target_path.write_bytes(archive.read(member_name))

        missing = [
            directory
            for directory in required_directories
            if not list((annotations_dir / directory).glob("*.xml"))
        ]
        if missing:
            raise FileNotFoundError(
                f"Для встречи {meeting} не найдена разметка ICSI: "
                f"{', '.join(missing)}."
            )

        yield annotations_dir
    finally:
        shutil.rmtree(annotations_dir, ignore_errors=True)
        print("Временные файлы разметки удалены.")
