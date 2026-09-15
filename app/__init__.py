"""Universal Sniffer — professional electronics sniffer / logic analyzer platform.

Layer map (see docs/architecture.md):

    L6  GUI (app.gui)                 Tkinter/ttk views + controllers
    L5  Application (app.main, models) wiring, sessions, commands
    L4  Core engine (app.core)        capture, timeline, storage, analysis
    L3  Protocol decoders (app.protocol)
    L2  Transport (app.transport)     USB / future Ethernet
    L1  HAL (app.hal)                 device abstraction, simulator
    L0  Hardware (firmware/)          Teensy 4.1

Dependency rule: higher layers may depend on lower layers only.
Pure shared-kernel modules (errors, logging_setup, config,
core.sample_block, core.timeline, core.integrity) are importable by any layer.
"""

APP_NAME = "Universal Sniffer"
__version__ = "0.1.0"
