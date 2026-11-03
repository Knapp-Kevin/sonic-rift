"""Screenshot the new Levels panel on the round-2 project, driven through the panel's own
controls: D on, E and F muted, Check balance. Not saved."""
import os
from unittest.mock import patch

import rehearse_scene as rs

OUT = rs.HERE / "levels_panel"
OUT.mkdir(exist_ok=True)
rs.OUT = OUT
rs.LOG = open(OUT / "levels_log.txt", "a", encoding="utf-8")
PROJECT = rs.HERE / "round2" / "Evening Tide - The Beacon (music round 2).sonicrift.json"


def main():
    from PySide6.QtCore import QSize
    from PySide6.QtWidgets import QFileDialog
    from this_voice_thing.ui import main_window, taskbar

    with patch.object(main_window.ChatterboxApp, "start_default_model_load", lambda self: None), \
            patch.object(main_window.ChatterboxApp, "restart_api_server", lambda self: None):
        w = main_window.SonicRiftApp()
    taskbar.set_window_identity(w)
    w.resize(QSize(1600, 900))
    w.show()
    w.move(-4000, 40)
    rs.pump(1.0)
    editor = w.open_project_editor()
    with patch.object(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(PROJECT), ""))):
        editor.open_project()
    rs.pump(0.5)
    panel = editor.levels
    by_name = {t.name: t.id for t in editor.session.project.tracks}
    for name, muted in (("Round 2 D", False), ("Round 2 E", True), ("Round 2 F", True)):
        panel.rows[by_name[name]]["mute"].setChecked(muted)
    rs.grab(w, "levels_before_check")
    panel.check_button.click()
    rs.wait_for(lambda: editor.balance_worker is None, 60, "Check balance")
    for name, track_id in by_name.items():
        rs.log(f"{name}: {panel.rows[track_id]['value'].text()} | {panel.rows[track_id]['readout'].text()}")
    rs.log(f"summary: {panel.summary.text()} | duck {panel.duck_value.text()}")
    rs.grab(w, "levels_after_check")
    editor._mark_clean()
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except Exception as exc:
        import traceback
        rs.log("EXCEPTION " + "".join(traceback.format_exception(exc)))
        code = 1
    os._exit(code)
