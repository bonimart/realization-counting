"""
Helper script for downloading and extracting minimally rigid graphs from https://zenodo.org/records/1245517.
"""

import zipfile
from dataclasses import dataclass
from pathlib import Path

import httpx
from tqdm import tqdm


@dataclass
class ZenodoFile:
    name: str
    url: str
    size: int

    def from_file_info(file_info: dict) -> ZenodoFile:
        return ZenodoFile(
            name=file_info["key"],
            url=file_info["links"]["self"],
            size=file_info.get("size", 0),
        )


def _download_file(file: ZenodoFile, output_path: Path, client: httpx.Client):
    with client.stream("GET", file.url) as r:
        r.raise_for_status()
        with (
            tqdm(
                total=file.size,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                desc=str(output_path),
            ) as progress,
            open(output_path, "wb") as f,
        ):
            for chunk in r.iter_bytes(chunk_size=8192):
                f.write(chunk)
                progress.update(len(chunk))


def _extract_zip(zip_path: Path, output_dir: Path):
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(output_dir)


def download_min_rigid_graphs(
    url: str = "https://zenodo.org/api/records/1245517", output_dir: Path = Path("data")
):
    headers = {"User-Agend": "ZenodoDownloader/1.0"}

    with httpx.Client(headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
        data = response.json()
        files = [
            ZenodoFile.from_file_info(file_info) for file_info in data.get("files", [])
        ]
        if not files:
            print("No files found")
            return
        output_dir.mkdir(exist_ok=True)
        for file in files:
            if not file.name.startswith("LamanGraphs"):
                continue

            print(f"Downloading: {file.name} ({file.size / (1024 * 1024):.2f} MB)")
            destination_path = output_dir / file.name
            _download_file(file, destination_path, client)
            print(f"Successfully saved to {destination_path}")

            print(f"Extracting {destination_path}...")
            _extract_zip(destination_path, output_dir)
            print(f"Succesfully extracted to: {output_dir}")


if __name__ == "__main__":
    download_min_rigid_graphs()
