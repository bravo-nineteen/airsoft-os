# AOS 3.5 — Tactical Planning Widgets

Experimental Debian 13 / Xorg / PySide6 desktop shell, upgraded from AOS 3.4.

## New in 3.5
- System Status: four circular ring gauges for CPU, RAM, disk and battery. Missing battery is shown as N/A.
- Widget Manager: optional Schedule, Roster and Planning Map panels, which can be moved and resized in Edit mode.
- Map Planner: import a local field image, add labelled colour-coded markers, routes and waypoints; undo, save/load JSON plans and export an annotated PNG.
- Plan autosave to ~/.config/aoj-os/planning/autosave.json after committed changes.
- A dedicated Map Planner icon on the sidebar.
- Existing widget layouts backed up and migrated to 3.5 defaults on first launch.

## Install
Extract the ZIP and run `sudo bash linux/install.sh`, then select Airsoft OS 3.5 at the login screen.

## Use
Open Map Planner from the left navigation, import a JPG/PNG, select Marker, Route or Waypoint, choose a colour, then click on the map. For routes and waypoint chains, click multiple points and select FINISH ROUTE. Use SAVE PLAN to store a JSON plan and EXPORT PNG to create a flat image.

Use the widget manager (More > Choose widgets) to show Schedule, Roster and Planning Map on the desktop. These panels open the existing management modules. Schedule and roster panels are launchers, not yet live inline previews.

## Important limitations
- Planning is local/offline; simultaneous multi-terminal editing and conflict resolution are not implemented.
- Saved JSON references the original local image path. Keep the image file in place to reopen the map.
- Undo is single-step per click/object, not a full editing history. Markers/routes are not draggable after creation; use undo and recreate them.
- No hardware testing on CF-19; PySide6 is not available in the packaging environment, so GUI runtime was not exercised.
- Keep your existing Debian session available for recovery.
