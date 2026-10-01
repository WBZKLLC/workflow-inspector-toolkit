"""Prepare public-only release objects; never update a branch or access another repo."""
from pathlib import Path, PurePosixPath
import base64
import hashlib
import json
import lzma
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request

REPO = "WBZKLLC/workflow-inspector-toolkit"
assert os.environ.get("GITHUB_REPOSITORY") == REPO, "Unexpected repository"
raw = lzma.decompress(Path("release-source.xz").read_bytes())
assert hashlib.sha256(raw).hexdigest() == "5279e3fabff89dc74ed83ef418fa9acfbf4ff68098cd34d149161f7f9281756e", "Source transfer mismatch"
files = json.loads(raw)
assert len(files) == 35, "Unexpected source file count"
root = Path(tempfile.mkdtemp(prefix="public-toolkit-"))
for name, text in files.items():
    relative = PurePosixPath(name)
    assert not relative.is_absolute() and ".." not in relative.parts
    assert isinstance(text, str)
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
print("SOURCE_SHA256=" + hashlib.sha256(raw).hexdigest(), flush=True)

chrome = shutil.which("google-chrome") or shutil.which("google-chrome-stable") or shutil.which("chromium")
assert chrome, "Headless browser unavailable"
for name, width, height in (("desktop", 1360, 1050), ("mobile", 390, 2875)):
    target = root / "docs" / f"demo-{name}.png"
    subprocess.run([
        chrome, "--headless", "--no-sandbox", "--disable-gpu",
        "--disable-dev-shm-usage", "--disable-background-networking",
        "--disable-sync", "--no-first-run", "--hide-scrollbars",
        "--force-device-scale-factor=1", f"--window-size={width},{height}",
        "--virtual-time-budget=2000", f"--screenshot={target}",
        (root / "examples/comparison.html").as_uri(),
    ], check=True, timeout=60, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    image = target.read_bytes()
    assert image.startswith(b"\x89PNG\r\n\x1a\n") and len(image) > 10000
    print(f"Rendered {name} preview: {len(image)} bytes", flush=True)

subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=root, check=True)
subprocess.run([sys.executable, "scripts/check_release.py"], cwd=root, check=True)
subprocess.run([sys.executable, "-m", "examples.python_client"], cwd=root, check=True)

def post(endpoint, body):
    assert endpoint in {"git/blobs", "git/trees"}
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/{endpoint}",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": "Bearer " + os.environ["GH_TOKEN"],
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "workflow-inspector-toolkit-release",
            "X-GitHub-Api-Version": "2022-11-28",
        }, method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)

entries = []
# The connected publishing client adds CI separately. The runner does not
# create/update a workflow, commit, ref, setting, deployment, or other repository.
for name in sorted(files):
    if name == ".github/workflows/ci.yml":
        continue
    entries.append({"path": name, "mode": "100644", "type": "blob", "content": files[name]})
for name in ("desktop", "mobile"):
    path = f"docs/demo-{name}.png"
    data = (root / path).read_bytes()
    result = post("git/blobs", {"content": base64.b64encode(data).decode(), "encoding": "base64"})
    expected = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
    assert result["sha"] == expected, "Preview transfer mismatch"
    entries.append({"path": path, "mode": "100644", "type": "blob", "sha": result["sha"]})
    print(f"ASSET_BLOB {path} {result['sha']}", flush=True)
assert len(entries) == 36
result = post("git/trees", {"tree": entries})
print("PREPARED_TREE_SHA=" + result["sha"], flush=True)
with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
    summary.write("## Public toolkit release prepared\n\n")
    summary.write("35 source files transferred with an exact SHA-256 match. Two report previews rendered from fictional examples. All 69 tests and release checks passed.\n\n")
    summary.write("Prepared tree: `" + result["sha"] + "` (CI is added by the publishing client). No branch was changed by this job.\n")
