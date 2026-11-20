import subprocess
import sys
import time
from researchmind_skills.api import create_local_context
from researchmind_skills.runtime.resources import compute_slot


def test_compute_slot_is_process_owned_and_released_on_exit(tmp_path):
    ctx = create_local_context(tmp_path)
    marker = tmp_path / "acquired.txt"
    code = (
        "from researchmind_skills.api import create_local_context; from researchmind_skills.runtime.resources import compute_slot; from pathlib import Path; "
        + f"ctx=create_local_context({str(tmp_path)!r}); "
        + "\nwith compute_slot(ctx):\n    Path("
        + repr(str(marker))
        + ").write_text('acquired')"
    )
    with compute_slot(ctx):
        child = subprocess.Popen([sys.executable, "-c", code])
        try:
            time.sleep(0.3)
            assert not marker.exists()
        except BaseException:
            child.terminate()
            child.wait()
            raise
    child.wait(timeout=10)
    assert child.returncode == 0 and marker.read_text() == "acquired"
