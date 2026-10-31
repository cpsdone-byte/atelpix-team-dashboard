import sys
if '--team' in sys.argv:
    from atelpix.team_viewer import TeamViewer
    TeamViewer().mainloop()
else:
    from atelpix.app import App
    App().mainloop()
