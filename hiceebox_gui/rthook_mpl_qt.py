# PyInstaller runtime hook: set matplotlib backend to QtAgg before any other code runs.
# This prevents the frozen app from using the MacOSX backend (which can cause immediate crash).
import matplotlib
matplotlib.use("QtAgg")
