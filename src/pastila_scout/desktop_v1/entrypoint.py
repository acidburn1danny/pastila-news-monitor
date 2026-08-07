"""Structural GUI entrypoint; production composition is intentionally absent."""

# ruff: noqa: BLE001, S110

from __future__ import annotations

import ctypes
import sys
import tkinter

from .controller import _DesktopTaskControllerV1
from .views import _DesktopMainWindowV1


def main() -> int:
    root = None
    controller = None
    try:
        if sys.platform == "win32":
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except BaseException:
                pass
        root = tkinter.Tk()
        root.tk.call("tk", "scaling", 2.0)
        cells: dict[str, object] = {}
        closed = False

        def select_page(*, page) -> None:
            cells["controller"].select_page(page=page)  # type: ignore[attr-defined]

        def close() -> None:
            nonlocal closed
            if closed:
                return
            closed = True
            cells["controller"].close()  # type: ignore[attr-defined]
            root.quit()

        def publish_snapshot(*, snapshot) -> None:
            cells["view"].publish_snapshot(snapshot=snapshot)  # type: ignore[attr-defined]

        controller = _DesktopTaskControllerV1(
            schedule_after=root.after,
            cancel_after=root.after_cancel,
            publish_snapshot=publish_snapshot,
        )
        view = _DesktopMainWindowV1(
            root=root, on_select_page=select_page, on_close=close
        )
        cells.update(controller=controller, view=view)
        root.protocol("WM_DELETE_WINDOW", close)
        controller.start()
        root.mainloop()
        return 0
    except BaseException:
        return 1
    finally:
        if controller is not None:
            try:
                controller.close()
            except BaseException:
                pass
        if root is not None:
            try:
                root.destroy()
            except BaseException:
                pass
