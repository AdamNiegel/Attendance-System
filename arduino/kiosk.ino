#include <Wire.h>
#include <LiquidCrystal_I2C.h>

LiquidCrystal_I2C lcd(0x27, 16, 2); // blank screen? try 0x3F
const int BUZZER = 8, GREEN = 9, RED = 10;

void beep(int ms) { digitalWrite(BUZZER, HIGH); delay(ms); digitalWrite(BUZZER, LOW); }
void showIdle() { lcd.clear(); lcd.print("Scan your ID"); }

void setup() {
  pinMode(BUZZER, OUTPUT); pinMode(GREEN, OUTPUT); pinMode(RED, OUTPUT);
  Serial.begin(9600);
  lcd.init(); lcd.backlight();
  showIdle();
}

void loop() {
  if (Serial.available()) {
    String line = Serial.readStringUntil(0x0A);
    line.trim();
    int a = line.indexOf(0x2C), b = line.indexOf(0x2C, a + 1);
    if (a < 0 || b < 0) return;
    String code = line.substring(0, a);
    String l1 = line.substring(a + 1, b);
    String l2 = line.substring(b + 1);
    lcd.clear();
    lcd.setCursor(0, 0); lcd.print(l1.substring(0, 16));
    lcd.setCursor(0, 1); lcd.print(l2.substring(0, 16));
    if (code == "OK")        { digitalWrite(GREEN, HIGH); beep(150); }
    else if (code == "LATE") { digitalWrite(GREEN, HIGH); beep(100); delay(100); beep(100); }
    else                     { digitalWrite(RED, HIGH); beep(600); }
    delay(2000);
    digitalWrite(GREEN, LOW); digitalWrite(RED, LOW);
    showIdle();
  }
}
