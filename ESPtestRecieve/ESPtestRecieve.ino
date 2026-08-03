#include <Wire.h>

#define I2C_ADDR 0x08     // 要和 Jetson 端 ESP_ADDR 一致
#define SDA_PIN  8        // ESP32-C3 SuperMini 默认 SDA=GPIO8
#define SCL_PIN  9        // 默认 SCL=GPIO9

void onReceive(int len) {
  String s;
  while (Wire.available()) s += (char)Wire.read();
  Serial.print("got: ");
  Serial.println(s);
}

void setup() {
  pinMode(2, OUTPUT);
  digitalWrite(2, LOW);

  Serial.begin(115200);
  Wire.begin((uint8_t)I2C_ADDR, SDA_PIN, SCL_PIN, 100000);  // 从机模式
  Wire.onReceive(onReceive);
}

void loop() { delay(10); }