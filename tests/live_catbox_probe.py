"""Opt-in integration probe. Publishes ONLY a tiny synthetic color setting.

    python3 tests/live_catbox_probe.py --upload-synthetic-fixture

The anonymous fixture can remain on Catbox. Never run automatically in CI.
Does not inspect, export, or change the actual desktop.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import savedesktopdesign as app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upload-synthetic-fixture", action="store_true", required=True)
    parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="sdd-live-test-") as tmp:
        archive_path = Path(tmp) / "fixture.sdd"
        content = b"[Colors:Window]\nBackgroundNormal=32,32,32\n"
        manifest = {"app": app.APP_NAME, "version": app.VERSION,
                    "public_design": 1, "paths": [".config/kdeglobals"],
                    "profile": {"plasma": "synthetic-test", "session": "synthetic-test", "screens": []},
                    "requirements": [], "categories": [], "with_packages": False}
        with tarfile.open(archive_path, "w:gz") as archive:
            for name, data in (("manifest.json", json.dumps(manifest).encode()),
                               ("home/.config/kdeglobals", content)):
                info = tarfile.TarInfo(name)
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
        app.inspect_public_archive(archive_path)
        print("Uploading synthetic fixture only", flush=True)
        code = app.upload_design(archive_path)
        print("Upload accepted; downloading using the generated code", flush=True)
        received = Path(tmp) / "received.sdd"
        app.download_design(code, received)
        app.inspect_public_archive(received)
        assert app.sha256_file(received) == app.sha256_file(archive_path)
        print("PASS: real Catbox upload, code, download, checksum and archive validation")
        print("Public synthetic fixture code: " + code)


if __name__ == "__main__":
    main()
