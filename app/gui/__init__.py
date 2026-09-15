"""Tkinter/ttk GUI (layer L6).

Rule (spec §7/§8): widgets live in views/panels/main_window and are touched
ONLY from the GUI thread. Logic lives in controllers/ and models/ and contains
NO Tkinter imports, so it is fully testable headless.
"""
