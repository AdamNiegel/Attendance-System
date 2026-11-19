# TUPM QR Attendance System

Flask + SQLite + html5-qrcode + Arduino Uno (LCD, buzzer, LEDs). No internet needed.

## Run (Windows)
1. Install Python 3 (tick "Add to PATH").
2. Unzip. Double-click `run.bat`.
3. Browser opens at http://127.0.0.1:5000 (use Chrome or Edge).
4. Admin login: `admin` / `admin123`

Manual: `python -m venv venv`, `venv\Scripts\activate`, `pip install -r requirements.txt`, `python app.py`.
Change admin password: `python init_db.py admin NEWPASSWORD`.

## Arduino
1. Arduino IDE: install library "LiquidCrystal I2C" (Frank de Brabander).
2. Open `arduino/kiosk/kiosk.ino`, pick board Uno + port, upload.
3. Wiring: LCD GND-GND, VCC-5V, SDA-A4, SCL-A5. Buzzer + to D8, - to GND.
   Green LED D9 (via 220 ohm), red LED D10 (via 220 ohm), short legs to GND.
4. Blank LCD? Change `0x27` to `0x3F`.
5. Close Serial Monitor before connecting. On Kiosk page click "Connect Arduino", pick port, wait 2 seconds.
   Test in Serial Monitor (9600): `OK,Present,TUPM-25-0001`, `LATE,Late,TUPM-25-0001`, `ERR,Not enrolled,TUPM-25-0001`

## Demo flow
1. Login admin. Sessions: open a session (late after N minutes).
2. Kiosk: Enroll mode, scan a new ID. Attendance mode: scan it, scan again (Already recorded), scan non-enrolled ID.
3. Student: /register with the enrolled ID, set password, log in, see dashboard.
4. Admin: Attendance page, change status, student status updates.

## Rules
- Present: scan before start + late minutes. Late: after. Absent: no scan when session closed (or day passed). Excused: admin only.
- Safe: under 2 absences and under 4 lates. Warning: 2 absences or 4-5 lates. Drop: 3 absences or 6 lates.
- Students count only sessions on or after their enrollment day.

## Notes
- QR code must contain exactly `TUPM-YY-NNNN`.
- No camera? Use manual ID box on Kiosk.
- Arduino unplugged: attendance still saves, page shows "Hardware not connected".
- Reset everything: delete `database.db`, rerun.
