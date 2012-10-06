#define SENSOR 2
#define LED 11
#define RESET A2
#define CUMULATIVE_TIME  300000; // 5 * 60 * 1000
#define CURRENT_TIME 10000;  // 10 * 1000
#define BOOT_TIME 1800000; // 30 * 60 * 1000

volatile boolean lock = true;
volatile unsigned int counter = 0;
volatile unsigned int interval;
volatile unsigned long previous = millis();
unsigned long cumulative_timer;
unsigned long current_timer;
unsigned long boot_timer;

void event()
{
  if (!digitalRead(SENSOR)) {
    if (!lock) {
      lock = true;
      digitalWrite(LED, HIGH);
      counter++;
      interval = millis() - previous;
      previous = millis();
      delayMicroseconds(15000);
    }
  } else {
    digitalWrite(LED, LOW);
    lock = false;
    delayMicroseconds(15000);
  }
}

void setup()
{
  Serial.begin(9600);
  pinMode(SENSOR, INPUT);
  pinMode(LED, OUTPUT);  
  pinMode(RESET, OUTPUT);
  digitalWrite(RESET, HIGH);
  cumulative_timer = millis() + CUMULATIVE_TIME;
  current_timer = millis() + CURRENT_TIME;
  boot_timer = millis() + BOOT_TIME;
  digitalWrite(LED, HIGH);
  attachInterrupt(0, event, CHANGE);
}

void loop()
{
  if (millis() > cumulative_timer) {
    cumulative_timer = millis() + CUMULATIVE_TIME;
    Serial.print("cumulative=");
    Serial.println(counter);
    counter = 0;
  }
  
  if (millis() > current_timer) {
    current_timer = millis() + CURRENT_TIME;
    Serial.print("current=");
    Serial.println(interval);
  }
  
  /*if (millis() > boot_timer) {
    boot_timer = millis() + BOOT_TIME;
    digitalWrite(RESET, LOW);
    delay(300);
    digitalWrite(RESET, HIGH);
    delay(5000);
    Serial.print("$$$");
    delay(300);
    Serial.print("reboot\r");
    delay(5000);
    Serial.print("$$$");
    delay(300);
    Serial.print("load default\r");
    Serial.print("save\r");
    Serial.print("reboot\r");
  }*/
}
