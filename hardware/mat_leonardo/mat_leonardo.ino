// Second Opinion: pressure mat -> one Enter key press
// Board: Arduino Leonardo (or Pro Micro). Needs the built-in Keyboard library.
//
// Wiring:  mat wire A -> pin 2
//          mat wire B -> GND
// When the foil layers touch, pin 2 is connected to GND (reads LOW).

#include <Keyboard.h>

const int MAT_PIN = 2;                       // wire A goes here
const unsigned long DEBOUNCE_MS = 60;        // ignore flicker for this long
const unsigned long COOLDOWN_MS = 10000;     // after one Enter, ignore the mat for 10 s
const unsigned long RELEASE_MS  = 1500;      // mat must be empty this long to re-arm

bool armed = true;
bool lastRaw = HIGH;
bool stable = HIGH;
unsigned long lastChange = 0;
unsigned long firedAt = 0;
unsigned long releasedAt = 0;

void setup() {
  pinMode(MAT_PIN, INPUT_PULLUP);
  pinMode(LED_BUILTIN, OUTPUT);
  delay(3000);            // safety pause so you can still re-upload if needed
  Keyboard.begin();
}

void loop() {
  unsigned long now = millis();
  bool raw = digitalRead(MAT_PIN);

  // debounce
  if (raw != lastRaw) { lastChange = now; lastRaw = raw; }
  if ((now - lastChange) > DEBOUNCE_MS && raw != stable) {
    stable = raw;
    if (stable == HIGH) releasedAt = now;      // someone stepped off
  }

  bool pressed = (stable == LOW);

  // re-arm only after cooldown AND the mat has been empty for a moment
  if (!armed && !pressed && (now - firedAt) > COOLDOWN_MS && (now - releasedAt) > RELEASE_MS) {
    armed = true;
  }

  // someone stepped on: send ONE Enter
  if (armed && pressed) {
    Keyboard.write(KEY_RETURN);
    armed = false;
    firedAt = now;
    digitalWrite(LED_BUILTIN, HIGH);           // little light on the board
  }

  if (!armed && (now - firedAt) > 500) digitalWrite(LED_BUILTIN, LOW);
}
