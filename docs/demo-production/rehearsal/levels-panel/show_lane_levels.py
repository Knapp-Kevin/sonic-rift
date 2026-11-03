"""Screenshot the reworked Studio: level sliders and Mute in each lane header, Check balance in
the transport row. Round-2 project with only take D kept (E and F tracks removed in this
unsaved session), driven through the real controls."""
import os
from unittest.mock import patch

import rehearse_scene as rs

OUT = rs.HERE / "lane_levels"
OUT.mkdir(exist_ok=True)
rs.OUT = OUT
rs.LOG = open(OUT / "lane_levels_log.txt", "a", encoding="utf-8")
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
    for name in ("Round 2 E", "Round 2 F"):
        track = next(t for t in editor.session.project.tracks if t.name == name)
        editor._mutate(lambda: editor.session.remove_track(track.id))
    by_name = {t.name: t.id for t in editor.session.project.tracks}
    d = by_name["Round 2 D"]
    if editor.session.project.tracks[-1].muted:
        editor.timeline.controls[d]["mute"].click()
    editor.timeline.controls[d]["slider"].setValue(round(-15 / 0.5))     # keyboard-style commit
    rs.pump(0.3)
    rs.grab(w, "lanes_before_check")
    editor.balance_button.click()
    rs.wait_for(lambda: editor.balance_worker is None, 60, "Check balance")
    for name, track_id in by_name.items():
        rs.log(f"{name}: {editor.timeline.badges.get(track_id, '')}")
    rs.log(f"note: {editor.balance_note.text()}")
    rs.grab(w, "lanes_after_check")
    editor.clips_button.click()
    rs.grab(w, "lanes_with_clip_list")
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
