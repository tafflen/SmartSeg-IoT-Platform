// SmartSeg - Arduino Sensor Code
// Sensors: IR (D5), Inductive Proximity (D6), Rain/Moisture (A0)

const int IR_PIN = 5;
const int PROXIMITY_PIN = 6;
const int RAIN_PIN = A0;

void setup() {
  Serial.begin(9600);
  pinMode(IR_PIN, INPUT);
  pinMode(PROXIMITY_PIN, INPUT);
}

void loop() {
  int ir = digitalRead(IR_PIN);         // 0 = object detected, 1 = no object
  int metal = digitalRead(PROXIMITY_PIN); // 0 = metal detected, 1 = no metal
  int moisture = analogRead(RAIN_PIN);   // 0-1023, lower = wetter

  // Send data in format the Python server expects
  Serial.print("IR:");
  Serial.print(ir);
  Serial.print(",METAL:");
  Serial.print(metal);
  Serial.print(",MOISTURE:");
  Serial.println(moisture);

  delay(300); // Send every 300ms
}
