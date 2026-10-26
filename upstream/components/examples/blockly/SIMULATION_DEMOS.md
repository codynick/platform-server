# Simulation and Dashboard Demos

Use Simulator mode. Open Simulator and add the listed gadgets before Run; open
Dashboard in another tab. Click Load and choose Demo 1, 2, 3 or 4. These
projects do not use physical USB gadgets. Stop before switching projects.

| Project | Add to simulator | Demonstration |
| --- | --- | --- |
| 01_temperature_monitor.codynick | Temperature sensor, seven-segment | Move the temperature slider. The display, gauge and history graph follow it once per second. |
| 02_temperature_traffic_light.codynick | Temperature sensor, seven-segment, CJP | Below 20 C: blue. 20 through 30 C: green. Above 30 C: red. The seven-segment and gauge show the same reading. |
| 03_parking_assistant.codynick | Ultrasonic sensor, CJP | Distance below 20 cm: red. Otherwise: green. A gauge shows distance from 0 to 200 cm. |
| 04_joystick_status.codynick | CJP | Hold a direction: its LED lights and the info card names the direction. Release: Neutral. Click: white LED 6 and Pressed. |

The CJP mapping is up=13 blue, down=1 yellow, left=8 cyan, right=4 red,
click=6 white. The temperature and parking demos use LED 6.

Every project has a start stack and a main-loop stack. Named variables keep
readings readable. Dashboard widgets are created once, then updated in the loop.
The graph shows sample numbers and the last 20 readings. Dashboards are per user.

Version 0.1.9 includes the live-reading display block and pre-installs all four
designs into every user's Load list. No Upload step or local patch is needed.
Existing saved designs and edits to previously installed demos are preserved.
The original fixed-number seven-segment block remains available and unchanged.
