# VanCore Demo Dashboard – Frontend Functionality Breakdown

This document lists **every visible element** from the VanCore demo dashboard and explains, in plain English, what each one shows or controls.

It is grouped by section, roughly matching how you might split pages in the final app:
- Global (header, time, weather)
- Power System
- Lighting Control
- Climate Control
- Water System
- Van Level
- GPS & Travel
- Network
- Media
- Automation
- Security System

---

## 1. Global / App Shell

These elements sit at the top or are “global context”.

### 1.1 Header Bar

1. **Title – “Van Control Dashboard”**  
   - What it is: The name of the dashboard, shown at the top.  
   - Purpose: Makes it obvious that this screen is for controlling the van.

2. **Dark Mode toggle – text: “Dark Mode” + control (on/off)**  
   - What it is: A switch for changing the colour scheme.  
   - What it controls: Turns the app into a dark or light look for comfort in different lighting conditions.

3. **Settings button – “Settings”**  
   - What it is: A button that opens a settings view (current or future).  
   - What it controls: Takes the user to a place where they can adjust app-wide preferences (units, theme, alerts, etc.).
  
4. **Notification 'Bell' Icon**
   - with number of outstanding notifications as a number in the corner


### 1.2 Time & Date

4. **Section label – “Current Time”**  
   - What it is: Text label for the time and date block.  
   - Purpose: Makes it clear what the following values represent.

5. **Time display – e.g. “11:11 PM”**  
   - What it is: A read-only digital clock.  
   - What it shows: The current local time where the van is.

6. **Date display – e.g. “Thursday, October 30”**  
   - What it is: A read-only date line.  
   - What it shows: The current day of the week and calendar date.

### 1.3 Weather Summary

7. **Section label – “Weather”**  
   - What it is: Text label for the weather block.  
   - Purpose: Groups all the outside-conditions readings.

8. **Outside temperature – e.g. “72°F”**  
   - What it is: Single value display.  
   - What it shows: The current outside air temperature near the van.

9. **Weather condition text – e.g. “sunny”**  
   - What it is: Short text description.  
   - What it shows: Current weather condition (sunny, cloudy, raining, etc.).

10. **Humidity – e.g. “45%”**  
    - What it is: Single value display.  
    - What it shows: Outside air humidity.

11. **Wind speed – e.g. “8 mph”**  
    - What it is: Single value display.  
    - What it shows: Current wind speed outside the van.

---

## 2. Power System Section – “Power System”

This block summarises the electrical system state.

12. **Section label – “Power System”**  
    - What it is: Title for the power block.  
    - Purpose: Groups all power-related items together.

### 2.1 Battery Card

13. **Battery label – “Battery Level”**  
    - What it is: Text label.  
    - Purpose: Announces the battery status area.

14. **Battery charging state – “charging”**  
    - What it is: Status text and speed (inc. time to full estimate)
    - What it shows: Whether the battery is currently being charged (vs. idle/discharging).

15. **Battery percentage – e.g. “85%”**  
    - What it is: Main number for battery fullness.  
    - What it shows: How full the main battery bank is.

16. **Battery voltage – e.g. “12.8 V”**  
    - What it is: Secondary number, very small and faint
    - What it shows: The current battery voltage, useful for more technical users and debugging.

### 2.2 Input Power Card

17. **Input power label – “Input Power”**  
    - What it is: Text label.  
    - Purpose: Marks the block that shows power coming *into* the system.

18. **Input power value – e.g. “320 W”**  
    - What it is: Single numeric display.  
    - What it shows: How much power is currently flowing into the system (from solar, shore, alternator, etc.).

19. **Input source description – e.g. “Solar/Shore Power”**  
    - What it is: Text description.  
    - What it shows: The source(s) currently feeding power into the system.

### 2.3 Output Power Card

20. **Output power label – “Output Power”**  
    - What it is: Text label.  
    - Purpose: Marks the block for power leaving the system.

21. **Output power value – e.g. “180 W”**  
    - What it is: Single numeric display.  
    - What it shows: How much power is currently being drawn by loads.

22. **Output destination description – e.g. “To Inverter”**  
    - What it is: Text description.  
    - What it shows: The primary destination of that output (for example, the inverter feeding AC sockets).

### 2.4 Total Power Draw Card

23. **Power draw label – “Power Draw”**  
    - What it is: Text label.  
    - Purpose: Titles the overall usage card.

24. **Power draw value – e.g. “140 W”**  
    - What it is: Single numeric display.  
    - What it shows: The total power being used by the system at this moment.

25. **Sub-label – “Current Usage”**  
    - What it is: Clarifying text.  
    - What it shows: That the value is a live reading (not a daily total or average).

Very visual layout of inputs/outputs/battery level flow sped up with faster power flow. Central, highly visual card. 

---

## 3. Lighting Section – “Lighting Control”

Controls and status for all lighting zones.

26. **Section label – “Lighting Control”**  
    - What it is: Title for the lighting block.  
    - Purpose: Groups all light-related controls.

### 3.1 Master Lighting

27. **Master lighting control – “Master Control On”**  
    - What it is: A toggle / main switch (text indicates “On”).  
    - What it controls: Turns **all van lights** on or off in one go.

28. **Overall lights status – “Lights On”**  
    - What it is: Status text.  
    - What it shows: The overall state of the lighting system (on vs off).

29. **Active lights count – e.g. “7”**  
    - What it is: Numeric display.  
    - What it shows: How many lights or zones are currently switched on.

### 3.2 Global Brightness

30. **Brightness label – “Brightness”**  
    - What it is: Text label.  
    - Purpose: Titles the brightness control.

31. **Brightness control/value – e.g. “75%”**  
    - What it is: Slider (implied) and value display.  
    - What it controls: Adjusts the brightness level of all dimmable lights together.

### 3.3 Individual Zones

32. **Kitchen lights switch – “Kitchen Lights On”**  
    - What it is: Zone-specific toggle.  
    - What it controls: Turns the **kitchen lighting** on or off.

33. **Bedroom lights switch – “Bedroom Lights Off”**  
    - What it is: Zone-specific toggle.  
    - What it controls: Turns the **bedroom lighting** on or off.

34. **Shower lights switch – “Shower Lights Off”**  
    - What it is: Zone-specific toggle.  
    - What it controls: Turns the **shower/bathroom lighting** on or off.

35. **Exterior lights switch – “Exterior Lights On”**  
    - What it is: Zone-specific toggle.  
    - What it controls: Turns the **external/awning lights** on or off.

---

## 4. Climate Section – “Climate Control”

Fan, vent and interior temperature.

36. **Section label – “Climate Control”**  
    - What it is: Title for climate controls.  
    - Purpose: Groups fan and temperature-related items.

### 4.1 Roof Fan / Vent

37. **Vent status line – e.g. “Maxxair Fan 45% open”**  
    - What it is: Combined label + value.  
    - What it shows: How far open the roof vent lid currently is (as a percentage).

> Note: In the UI this likely corresponds to a slider or numeric control underneath, but visually the only element is this single status line.

### 4.2 Fan Speed

38. **Fan speed label – “Fan Speed”**  
    - What it is: Text label.  
    - Purpose: Describes the fan speed control and value.

39. **Fan speed value – e.g. “3”**  
    - What it is: Numeric value display (implies steps / levels).  
    - What it controls: The speed level of the fan (for example 0 = off, 1–10 = increasing speed).

### 4.3 Interior Temperature

40. **Inside temperature label – “Inside Temp”**  
    - What it is: Text label.  
    - Purpose: Explains that the next value is for the inside of the van.

41. **Inside temperature value – e.g. “74°F”**  
    - What it is: Numeric display.  
    - What it shows: Current temperature inside the living area.

---

## 5. Water Section – “Water System”

Tank level, flow rate and pump control.

42. **Section label – “Water System”**  
    - What it is: Title for water-related elements.  
    - Purpose: Groups tank and pump info.

### 5.1 Tank & Flow

43. **Fresh water tank line – e.g. “Fresh Water Tank 68%”**  
    - What it is: Text label plus percentage.  
    - What it shows: How full the **fresh water tank** is.

44. **Flow rate label – “Flow Rate”**  
    - What it is: Text label.  
    - Purpose: Describes the usage-speed value beneath it.

45. **Flow rate value – e.g. “2.3 L/min”**  
    - What it is: Numeric display.  
    - What it shows: How fast water is currently flowing when a tap/shower is on.

### 5.2 Pump

46. **Pump status label – “Pump Status”**  
    - What it is: Text label.  
    - Purpose: Titles the pump control.

47. **Pump state – “Off”**  
    - What it is: Status text (representing a toggle).  
    - What it controls: Whether the **water pump** is on or off for the entire system.

---

## 6. Van Level Section – “Van Level”

Shows how level the van is front-to-back and side-to-side.

48. **Section label – “Van Level”**  
    - What it is: Title for levelling info.  
    - Purpose: Groups pitch and roll values.

49. **Pitch label – “Pitch”**  
    - What it is: Text label.  
    - Purpose: Describes the forward/backward tilt value.

50. **Pitch value – e.g. “2.1°”**  
    - What it is: Numeric display.  
    - What it shows: How much the van is tilted nose-up or nose-down.

51. **Roll label – “Roll”**  
    - What it is: Text label.  
    - Purpose: Describes the side-to-side tilt value.

52. **Roll value – e.g. “-1.3°”**  
    - What it is: Numeric display.  
    - What it shows: How much the van is leaning left or right.

---

## 7. GPS & Travel Section – “GPS & Travel”

Current location information.

53. **Section label – “GPS & Travel”**  
    - What it is: Title for travel/location info.  
    - Purpose: Groups GPS-related items.

54. **Location label – “Current Location”**  
    - What it is: Text label.  
    - Purpose: Explains what the place name refers to.

55. **Location value – e.g. “Moab, UT”**  
    - What it is: Text display.  
    - What it shows: The current place name for where the van is parked/driving.

---

## 8. Network Section – “Network”

Internet connection overview.

56. **Section label – “Network”**  
    - What it is: Title for network status.  
    - Purpose: Groups connectivity info.

57. **Connection status line – e.g. “Status Connected”**  
    - What it is: Status text.  
    - What it shows: Whether the van system is currently online (“Connected”) or not.

58. **Signal strength value – e.g. “85%”**  
    - What it is: Numeric display.  
    - What it shows: Overall signal strength of the current internet connection.

---

## 9. Media Section – “Media”

Audio playback overview.

59. **Section label – “Media”**  
    - What it is: Title for the media/audio block.  
    - Purpose: Groups the “now playing” information.

60. **Now playing label – “Now Playing”**  
    - What it is: Text label.  
    - Purpose: Explains what the following text refers to.

61. **Track name – e.g. “Life is a Highway”**  
    - What it is: Text display.  
    - What it shows: The current song or audio track playing in the van.


---

## 10. Automation Section – “Automation”

High-level automation summary.

62. **Section label – “Automation”**  
    - What it is: Title for automations.  
    - Purpose: Groups rule-related information.

63. **Active rules label – “Active Rules”**  
    - What it is: Text label.  
    - Purpose: Describes the numeric value below.

64. **Active rules count – e.g. “4”**  
    - What it is: Numeric display.  
    - What it shows: How many automation rules are currently turned on.

---

## 11. Security Section – “Security System”

Alarm and cameras overview.

65. **Section label – “Security System”**  
    - What it is: Title for security info.  
    - Purpose: Groups alarm/camera status.

66. **System status line – e.g. “System Status Armed”**  
    - What it is: Status text.  
    - What it shows: The current mode of the security system (armed vs disarmed, etc.).

67. **Cameras label – “Cameras Active”**  
    - What it is: Text label.  
    - Purpose: Describes the count value below it.

68. **Camera count – e.g. “0/4”**  
    - What it is: Numeric fraction.  
    - What it shows: How many cameras are currently active/online out of the total number of cameras.

69. **Motion label – “Motion Detected”**  
    - What it is: Text label.  
    - Purpose: Describes the motion status value.

70. **Motion state – e.g. “Yes”**  
    - What it is: Simple “Yes/No” display.  
    - What it shows: Whether motion is being detected right now by any sensor or camera.

---

## 12. Section → Page Mapping (for Backend Planning)

Even though the current demo is a single page, these sections naturally map to pages/modules in the final product:

- **Global / Shell**  
  - Title, dark mode toggle, settings button, time/date, weather.
- **Power System**  
  - Battery status, input power, output power, total power draw.
- **Lighting**  
  - Master light control, global brightness, per-zone switches.
- **Climate**  
  - Fan lid opening, fan speed, inside temperature.
- **Water**  
  - Fresh tank level, flow rate, pump state.
- **Van Level**  
  - Pitch and roll values.
- **GPS & Travel**  
  - Current location display.
- **Network**  
  - Online/offline status and signal strength.
- **Media**  
  - Now playing information.
- **Automation**  
  - Active rules count.
- **Security System**  
  - System armed state, camera count, motion status.

This file should now serve as your **ground truth frontend spec** for the current demo: every label, value, and control has an entry you can work backwards from when designing the backend entities and APIs.
