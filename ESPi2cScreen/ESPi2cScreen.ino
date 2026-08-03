/*
 * ESP32-C3 SuperMini : I2C slave receive + ST7796 display (test GUI)
 * ------------------------------------------------------------------
 * Jetson (I2C master) --i2c-7--> ESP32-C3 (slave 0x08) --SPI--> ST7796 (480x320)
 *
 * When an I2C message arrives, show it on screen:
 *   - LATEST : the most recent message (ASCII + HEX, so binary data is readable too)
 *   - LOG    : a scrolling log of the last few messages
 *   - status : RX indicator / total count / uptime
 *
 * Dependency: LovyanGFX  (Arduino IDE: Library Manager -> search "LovyanGFX")
 *
 * Pins (the two buses do not overlap):
 *   I2C        SDA=8  SCL=9
 *   Display SPI SCLK=4 MOSI=6 MISO=-1 DC=3 CS=7 RST=10
 *   GPIO2      activity indicator, blinks when a message is received (optional)
 *
 * IMPORTANT: the I2C onReceive callback runs in an interrupt/event context. Do NOT
 *            do SPI screen drawing inside it, or you risk watchdog resets / crashes.
 *            The callback only copies the data and sets a flag; the actual drawing
 *            happens in loop().
 */

#include <Arduino.h>
#include <Wire.h>
#include <LovyanGFX.hpp>

// ======================= I2C config =======================
#define I2C_ADDR  0x08     // must match ESP_ADDR on the Jetson side
#define SDA_PIN   8        // ESP32-C3 SuperMini default SDA=GPIO8
#define SCL_PIN   9        // default SCL=GPIO9
#define ACT_LED   2        // blinks on each received message (optional activity LED)

// ======================= Display driver (same wiring as your sketch) =======================
class LGFX_C3_ST7796 : public lgfx::LGFX_Device {
  lgfx::Bus_SPI      _bus_instance;
  lgfx::Panel_ST7796 _panel_instance;

public:
  LGFX_C3_ST7796(void) {
    {
      auto bus_cfg = _bus_instance.config();

      #ifdef FSPI_HOST
        bus_cfg.spi_host = FSPI_HOST;
      #else
        bus_cfg.spi_host = SPI2_HOST;
      #endif

      bus_cfg.spi_mode   = 0;
      bus_cfg.freq_write = 40000000;
      bus_cfg.freq_read  = 16000000;
      bus_cfg.spi_3wire  = false;
      bus_cfg.use_lock   = true;

      bus_cfg.pin_sclk   = 4;        // SCLK
      bus_cfg.pin_mosi   = 6;        // MOSI / SDA
      bus_cfg.pin_miso   = -1;
      bus_cfg.pin_dc     = 3;        // DC / RS

      _bus_instance.config(bus_cfg);
      _panel_instance.setBus(&_bus_instance);
    }

    {
      auto panel_cfg = _panel_instance.config();

      panel_cfg.pin_cs           = 7;   // CS
      panel_cfg.pin_rst          = 10;  // RST

      panel_cfg.panel_width      = 320;
      panel_cfg.panel_height     = 480;
      panel_cfg.offset_x         = 0;
      panel_cfg.offset_y         = 0;
      panel_cfg.invert           = false;
      panel_cfg.rgb_order        = false;

      _panel_instance.config(panel_cfg);
      setPanel(&_panel_instance);
    }
  }
};

LGFX_C3_ST7796 lcd;

// ======================= Receive buffer (shared between callback and loop) =======================
#define RX_MAX     128       // max bytes per message
#define LOG_LINES  9         // number of log lines shown in the LOG area

portMUX_TYPE   rxMux    = portMUX_INITIALIZER_UNLOCKED;
volatile bool  msgReady = false;         // a new message is waiting to be processed
volatile size_t isrLen  = 0;
uint8_t        isrBuf[RX_MAX];           // written by callback, read by loop (guarded by rxMux)

// ======================= GUI state =======================
uint8_t   lastMsg[RX_MAX];               // raw bytes of the most recent message
size_t    lastLen   = 0;
uint32_t  rxTotal   = 0;                  // total messages received
uint32_t  lastRxMs  = 0;                  // timestamp of the most recent message
String    logbuf[LOG_LINES];             // scrolling log (sanitized printable text)

// Layout constants (480x320 landscape after rotation)
static const int SCR_W = 480, SCR_H = 320;

// ---------- I2C receive callback: only copy data, no screen drawing ----------
void onReceive(int len) {
  uint8_t tmp[RX_MAX];
  size_t  n = 0;
  while (Wire.available() && n < RX_MAX) tmp[n++] = (uint8_t)Wire.read();
  while (Wire.available()) Wire.read();   // discard any overflow bytes

  portENTER_CRITICAL_ISR(&rxMux);
  memcpy(isrBuf, tmp, n);
  isrLen   = n;
  msgReady = true;
  portEXIT_CRITICAL_ISR(&rxMux);
}

// ---------- Helper: convert raw bytes to printable ASCII (non-printable -> '.') ----------
String toAscii(const uint8_t *buf, size_t n) {
  String s;
  for (size_t i = 0; i < n; i++) {
    char c = (char)buf[i];
    s += (c >= 0x20 && c < 0x7F) ? c : '.';
  }
  return s;
}

// ---------- Helper: HEX preview (up to 20 bytes) ----------
String toHex(const uint8_t *buf, size_t n) {
  String s;
  size_t m = (n > 20) ? 20 : n;
  char b[4];
  for (size_t i = 0; i < m; i++) { sprintf(b, "%02X ", buf[i]); s += b; }
  if (n > m) s += "...";
  return s;
}

// ======================= Draw: static frame (drawn once in setup) =======================
void drawStaticUI() {
  lcd.fillScreen(TFT_BLACK);

  // Title bar
  lcd.fillRect(0, 0, SCR_W, 30, TFT_NAVY);
  lcd.setTextColor(TFT_YELLOW, TFT_NAVY);
  lcd.setTextSize(2);
  lcd.drawString("Defect Detection GUI", 8, 7);
  lcd.setTextColor(TFT_WHITE, TFT_NAVY);
  char addr[16];
  sprintf(addr, "addr 0x%02X", I2C_ADDR);
  lcd.drawString(addr, SCR_W - 120, 7);

  // LATEST panel frame
  lcd.drawRect(6, 36, SCR_W - 12, 96, TFT_DARKGREY);
  lcd.setTextColor(TFT_GREENYELLOW, TFT_BLACK);
  lcd.setTextSize(2);
  lcd.drawString("LATEST", 14, 42);

  // LOG panel frame
  lcd.drawRect(6, 138, SCR_W - 12, 150, TFT_DARKGREY);
  lcd.setTextColor(TFT_CYAN, TFT_BLACK);
  lcd.setTextSize(2);
  lcd.drawString("LOG", 14, 144);

  // Status bar divider + RX label
  lcd.drawFastHLine(0, 290, SCR_W, TFT_DARKGREY);
  lcd.setTextColor(TFT_WHITE, TFT_BLACK);
  lcd.setTextSize(2);
  lcd.drawString("RX", 28, 299);
}

// ======================= Draw: LATEST area (on each new message) =======================
void drawLatest() {
  // byte count (right of the label)
  lcd.fillRect(110, 42, 220, 16, TFT_BLACK);
  lcd.setTextColor(TFT_DARKGREY, TFT_BLACK);
  lcd.setTextSize(1);
  char cnt[24];
  sprintf(cnt, "(%u bytes)", (unsigned)lastLen);
  lcd.drawString(cnt, 110, 48);

  // ASCII in large font (up to 25 chars, truncated beyond that)
  lcd.fillRect(8, 62, SCR_W - 16, 30, TFT_BLACK);
  String a = toAscii(lastMsg, lastLen);
  if (a.length() > 25) a = a.substring(0, 25) + "..";
  lcd.setTextColor(TFT_WHITE, TFT_BLACK);
  lcd.setTextSize(3);
  lcd.drawString(a, 16, 66);

  // HEX preview
  lcd.fillRect(8, 100, SCR_W - 16, 24, TFT_BLACK);
  lcd.setTextColor(TFT_ORANGE, TFT_BLACK);
  lcd.setTextSize(1);
  lcd.drawString("hex: " + toHex(lastMsg, lastLen), 16, 104);
}

// ======================= Draw: LOG area (on each new message) =======================
void drawLog() {
  // rx count (right of the LOG label)
  lcd.fillRect(300, 144, 174, 16, TFT_BLACK);
  lcd.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
  lcd.setTextSize(2);
  char c[24];
  sprintf(c, "rx: %u", (unsigned)rxTotal);
  lcd.drawString(c, 340, 144);

  // log lines
  lcd.fillRect(8, 166, SCR_W - 16, 118, TFT_BLACK);
  lcd.setTextColor(TFT_GREEN, TFT_BLACK);
  lcd.setTextSize(1);
  int y = 168;
  for (int i = 0; i < LOG_LINES; i++) {
    if (logbuf[i].length()) lcd.drawString(logbuf[i], 14, y);
    y += 13;
  }
}

// ======================= Draw: status bar (periodic refresh, small regions) =======================
void drawStatusBar() {
  // RX indicator: green if a message arrived within the last 200ms, otherwise dim
  bool active = (millis() - lastRxMs) < 200 && rxTotal > 0;
  lcd.fillCircle(14, 305, 6, active ? TFT_GREEN : TFT_DARKGREEN);

  // uptime HH:MM:SS
  uint32_t s = millis() / 1000;
  char up[24];
  sprintf(up, "up %02u:%02u:%02u",
          (unsigned)(s / 3600), (unsigned)((s % 3600) / 60), (unsigned)(s % 60));
  lcd.fillRect(330, 299, SCR_W - 330 - 6, 18, TFT_BLACK);
  lcd.setTextColor(TFT_GREEN, TFT_BLACK);
  lcd.setTextSize(2);
  lcd.drawString(up, 336, 299);
}

// ======================= Process one new message =======================
void handleMessage(const uint8_t *buf, size_t n) {
  // save the latest
  memcpy(lastMsg, buf, n);
  lastLen  = n;
  rxTotal++;
  lastRxMs = millis();

  // serial print (keep the original debug path)
  Serial.print("got: ");
  Serial.println(toAscii(buf, n));

  // scrolling log: shift everything up one line, put the new line at the bottom
  for (int i = 0; i < LOG_LINES - 1; i++) logbuf[i] = logbuf[i + 1];
  String line = String("[") + rxTotal + "] " + toAscii(buf, n);
  if (line.length() > 74) line = line.substring(0, 74);  // truncate a single line
  logbuf[LOG_LINES - 1] = line;

  // blink the activity LED
  digitalWrite(ACT_LED, HIGH);

  // refresh the screen (SPI runs in loop context, which is safe)
  lcd.startWrite();
  drawLatest();
  drawLog();
  drawStatusBar();
  lcd.endWrite();
}

// ======================= setup =======================
void setup() {
  pinMode(ACT_LED, OUTPUT);
  digitalWrite(ACT_LED, LOW);

  Serial.begin(115200);
  delay(300);
  Serial.println("Init ST7796 + I2C slave...");

  // display init
  lcd.init();
  lcd.setRotation(1);           // landscape 480x320
  drawStaticUI();

  // waiting prompt
  lcd.setTextColor(TFT_WHITE, TFT_BLACK);
  lcd.setTextSize(2);
  lcd.drawString("waiting for I2C...", 16, 70);

  // I2C slave init
  Wire.begin((uint8_t)I2C_ADDR, SDA_PIN, SCL_PIN, 100000);
  Wire.onReceive(onReceive);

  Serial.printf("Ready. I2C slave 0x%02X on SDA=%d SCL=%d\n", I2C_ADDR, SDA_PIN, SCL_PIN);
}

// ======================= loop =======================
void loop() {
  // new message available -> pull it out and render
  if (msgReady) {
    uint8_t local[RX_MAX];
    size_t  n;
    portENTER_CRITICAL(&rxMux);
    n = isrLen;
    memcpy(local, isrBuf, n);
    msgReady = false;
    portEXIT_CRITICAL(&rxMux);

    handleMessage(local, n);
  }

  // periodic status-bar refresh (uptime / RX indicator), and turn the activity LED off after the blink
  static uint32_t lastTick = 0;
  if (millis() - lastTick > 100) {
    lastTick = millis();
    drawStatusBar();
    if (millis() - lastRxMs > 120) digitalWrite(ACT_LED, LOW);
  }
}
