import shutil
import urllib.request
import zipfile
from contextlib import contextmanager
from pathlib import Path


AMI_MANUAL_ANNOTATIONS_URL = "https://groups.inf.ed.ac.uk/ami/AMICorpusAnnotations/ami_public_manual_1.6.2.zip"


@contextmanager
def download_meeting_annotations(meeting, required_directories):
    annotations_dir = Path("ami_temp")
    archive_path = annotations_dir / "ami_public_manual_1.6.2.zip"

    if annotations_dir.exists():
        shutil.rmtree(annotations_dir)
    annotations_dir.mkdir()

    try:
        print(f"Скачивание ручной разметки AMI для встречи {meeting}...")
        urllib.request.urlretrieve(AMI_MANUAL_ANNOTATIONS_URL, archive_path)

        with zipfile.ZipFile(archive_path) as archive:
            for member_name in archive.namelist():
                parts = member_name.rstrip("/").split("/")
                if len(parts) < 2:
                    continue

                directory = parts[-2]
                file_name = parts[-1]
                if directory not in required_directories:
                    continue
                if not file_name.startswith(f"{meeting}."):
                    continue
                if not file_name.endswith(".xml"):
                    continue

                target_dir = annotations_dir / directory
                target_dir.mkdir(parents=True, exist_ok=True)
                target_path = target_dir / file_name
                target_path.write_bytes(archive.read(member_name))

        missing = [
            directory
            for directory in required_directories
            if not list((annotations_dir / directory).glob(f"{meeting}.*.xml"))
        ]
        if missing:
            raise FileNotFoundError(
                f"Для встречи {meeting} не найдена разметка: {', '.join(missing)}."
            )

        yield annotations_dir
    finally:
        shutil.rmtree(annotations_dir, ignore_errors=True)
        print("Временные файлы разметки удалены.")
