import os
import traceback


def _fatal(error):
    """Report a startup failure without a console (pythonw has none)."""
    log = os.path.join(os.path.expanduser("~"), ".vyron_crash.log")
    try:
        with open(log, "a", encoding="utf-8") as handle:
            handle.write("".join(traceback.format_exception(error)) + "\n")
    except Exception:
        pass
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(
            None,
            "VYRON n'a pas pu demarrer.\nVYRON could not start.\n\n"
            "Details / details: " + log,
            "VYRON",
            0x10,
        )
    except Exception:
        pass


if __name__ == '__main__':
    try:
        from vyron.app import main as run
        run()
    except Exception as exc:
        _fatal(exc)
