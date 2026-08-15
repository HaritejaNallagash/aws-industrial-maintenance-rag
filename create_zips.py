from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

project_root = Path(".").resolve()
src_dir = project_root / "src"
build_dir = project_root / "build"

build_dir.mkdir(exist_ok=True)

def make_zip(zip_name):
    zip_path = build_dir / zip_name

    if zip_path.exists():
        zip_path.unlink()

    with ZipFile(zip_path, "w", ZIP_DEFLATED) as z:
        for file_path in src_dir.rglob("*"):
            if file_path.is_file():
                z.write(file_path, file_path.relative_to(project_root))

    print(f"Created: {zip_path}")

make_zip("ingestion-lambda.zip")
make_zip("query-lambda.zip")