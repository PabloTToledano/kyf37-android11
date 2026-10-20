#!/usr/bin/env python3
"""Canonical rerunnable source fix after fix_full_emulation.py and fix_ir_reconnect.py."""
from pathlib import Path
import runpy
here=Path(__file__).resolve().parent
for script in ('fix_emulator_buttons.py','fix_core_progress.py','fix_rtc_resume.py','fix_timer_w.py','finish_core_review.py','finalize_emulator_review.py'):
 runpy.run_path(str(here/script),run_name='__main__')
