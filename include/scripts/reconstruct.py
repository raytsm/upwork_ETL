from pathlib import Path
import shutil


# reconstruct.py is in include/scripts/, so parents[1] is the include/ folder.
INCLUDE_DIR = Path(__file__).resolve().parents[1]

RAW_DATA_DIR = INCLUDE_DIR / "data" / "raw_data"
RECONSTRUCTED_DATA_DIR = INCLUDE_DIR / "data" / "reconstructed_data"


def reconstruct_file(source_path: Path, destination_path: Path) -> None:
    """Dummy logic: copy the raw file to the reconstructed-data directory."""
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, destination_path)
    print(f"Reconstructed: {source_path} -> {destination_path}")


def reconstruct() -> None:
    """Process all files under raw_data and save them under reconstructed_data."""
    if not RAW_DATA_DIR.exists():
        raise FileNotFoundError(f"Raw data directory does not exist: {RAW_DATA_DIR}")

    RECONSTRUCTED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    files = [path for path in RAW_DATA_DIR.rglob("*") if path.is_file()]

    if not files:
        print(f"No files found in {RAW_DATA_DIR}")
        return

    for source_path in files:
        relative_path = source_path.relative_to(RAW_DATA_DIR)
        destination_path = RECONSTRUCTED_DATA_DIR / relative_path
        reconstruct_file(source_path, destination_path)

    print(f"Finished. Processed {len(files)} file(s).")


# if __name__ == "__main__":
#     reconstruct()
