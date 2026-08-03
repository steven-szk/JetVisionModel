#include <Arduino.h>
#include <LovyanGFX.hpp>

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
      // once verified, you can raise the write frequency to 40MHz for maximum smoothness
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
      panel_cfg.pin_rst          = 10;  // RST pin

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

// off-screen canvas (Sprite) for animation, avoids tearing/flicker from drawing directly to the screen
LGFX_Sprite canvas(&lcd);

// global test variables
int ball_x = 50;
int ball_y = 50;
int ball_dx = 4;
int ball_dy = 3;
const int ball_r = 15;

unsigned long last_time = 0;
int frame_count = 0;
float fps = 0.0;

void runColorTest() {
  // 1. flash the three primary colors (to check for inverted colors or RGB/BGR swap)
  lcd.fillScreen(TFT_RED);   delay(500);
  lcd.fillScreen(TFT_GREEN); delay(500);
  lcd.fillScreen(TFT_BLUE);  delay(500);
  lcd.fillScreen(TFT_BLACK);
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("Init ST7796 Display...");

  lcd.init();
  lcd.setRotation(1); // rotation: 0/2 = portrait (320x480), 1/3 = landscape (480x320)

  runColorTest();

  // create a 200x120 canvas
  canvas.createSprite(200, 120);
}

void loop() {
  // ---------------------------------------------------
  // static background UI (drawn directly to the screen)
  // ---------------------------------------------------
  lcd.startWrite(); // begin an SPI bulk-write lock to improve rendering efficiency

  // draw title
  lcd.setTextColor(TFT_YELLOW, TFT_BLACK);
  lcd.setTextSize(2);
  lcd.drawString("ESP32-C3 + ST7796 Test", 10, 10);

  // draw color-check bar
  lcd.fillRect(10, 40, 60, 25, TFT_RED);
  lcd.fillRect(80, 40, 60, 25, TFT_GREEN);
  lcd.fillRect(150, 40, 60, 25, TFT_BLUE);
  lcd.fillRect(220, 40, 60, 25, TFT_WHITE);

  // geometry test area
  lcd.drawRect(10, 75, 460, 235, TFT_DARKGREY);

  // ---------------------------------------------------
  // dynamic animation logic (double-buffered via Sprite for flicker-free rendering)
  // ---------------------------------------------------
  canvas.fillScreen(TFT_BLACK);
  canvas.drawRect(0, 0, canvas.width(), canvas.height(), TFT_WHITE);

  // update the ball's physics coordinates
  ball_x += ball_dx;
  ball_y += ball_dy;

  if (ball_x - ball_r <= 0 || ball_x + ball_r >= canvas.width())  ball_dx = -ball_dx;
  if (ball_y - ball_r <= 0 || ball_y + ball_r >= canvas.height()) ball_dy = -ball_dy;

  // draw the moving ball on the canvas
  canvas.fillCircle(ball_x, ball_y, ball_r, TFT_CYAN);
  canvas.drawCircle(ball_x, ball_y, ball_r, TFT_WHITE);

  // FPS calculation
  frame_count++;
  unsigned long now = millis();
  if (now - last_time >= 1000) {
    fps = (float)frame_count * 1000.0 / (now - last_time);
    frame_count = 0;
    last_time = now;
  }

  // print the live FPS on the canvas
  canvas.setTextColor(TFT_GREEN, TFT_BLACK);
  canvas.setTextSize(2);
  canvas.setCursor(10, 10);
  canvas.printf("FPS: %.1f", fps);

  // push the local canvas to the main screen at (x:20, y:90)
  canvas.pushSprite(20, 90);

  // static text and variables on the right
  lcd.setTextColor(TFT_CYAN, TFT_BLACK);
  lcd.setTextSize(2);
  lcd.setCursor(240, 100);
  lcd.printf("Res: %dx%d", lcd.width(), lcd.height());

  lcd.setCursor(240, 140);
  lcd.setTextColor(TFT_ORANGE, TFT_BLACK);
  lcd.printf("CLK: %dMHz", 40);

  lcd.endWrite(); // end SPI write
}
