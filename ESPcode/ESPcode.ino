#include <Wire.h>
#include <LovyanGFX.hpp>

// I2C Config
#define I2C_ADDR 0x08     // Target I2C address matching the Jetson host
#define SDA_PIN  8        // ESP32-C3 SuperMini default SDA = GPIO8
#define SCL_PIN  9        // ESP32-C3 SuperMini default SCL = GPIO9

// I2C RECIEVE DATA LENGTH
#define I2C_BUF_SIZE 128
char i2c_rx_buf[I2C_BUF_SIZE];
volatile bool i2c_data_ready = false;
volatile bool ip_updated = false;
volatile size_t rx_bytes_len = 0;
uint32_t rx_count = 0;   // Cumulative received packet counter

// Local copies of states for rendering
char current_msg[I2C_BUF_SIZE] = "Waiting for Jetson Nano Response";
size_t current_len = 0;
volatile uint32_t lastRxMs  = 0;                  // timestamp of the most recent message

// Log History Settings (Max 6 log entries displayed on left panel)
#define MAX_LOGS 6
char log_buffer[MAX_LOGS][I2C_BUF_SIZE];
uint8_t log_count = 0;

// Layout constants (480x320 landscape after rotation)
#define SCR_W 480
#define SCR_H 320

// Function vars
char IP[16] = {0}; 
char local_IP[16] = {0};

// =============================================
// ST7796 Display Hardware Driver Class
// =============================================
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
      bus_cfg.freq_write = 40000000; // SPI write clock speed: 40MHz
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
      panel_cfg.pin_cs       = 7;    // Chip Select Pin
      panel_cfg.pin_rst      = 10;   // Reset Pin
      panel_cfg.panel_width  = 320;
      panel_cfg.panel_height = 480;
      panel_cfg.offset_x     = 0;
      panel_cfg.offset_y     = 0;
      panel_cfg.invert       = false;
      panel_cfg.rgb_order    = false;
      
      _panel_instance.config(panel_cfg);
      setPanel(&_panel_instance);
    }
  }
};

LGFX_C3_ST7796 lcd;

// I2C Interrupt Service Routine
void onReceive(int len) {
  if (Wire.available() >= 3) {
    if (Wire.read() == 83) { // Check for header 'S' (ASCII 83)

      // Read remaining bytes
      int i = 0;
      while (Wire.available() && i < (I2C_BUF_SIZE - 1)) {
        i2c_rx_buf[i++] = (char)Wire.read();
      }
      i2c_rx_buf[i] = '\0'; // Null-terminate
      rx_bytes_len = i;
      
      // Check if message starts with "IP" (ASCII 73 and ASCII 80)
      if (i2c_rx_buf[0] == 'I' && i2c_rx_buf[1] == 'P') { 
        strncpy(IP, i2c_rx_buf + 2, sizeof(IP) - 1); //remove chars I P
        IP[sizeof(IP) - 1] = '\0';
        ip_updated = true;
      } else {
        i2c_data_ready = true;
      }
      lastRxMs = millis();
    }
    // Flush remaining buffer
    while (Wire.available()) Wire.read();
  }
}

// GUI Initialization
void drawStaticGUI() {
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

  lcd.drawRect(6, 36, SCR_W - 12, 60, TFT_DARKGREY);
  lcd.setTextColor(TFT_GREENYELLOW, TFT_BLACK);
  lcd.setTextSize(2);
  lcd.drawString("CURRENT ACTION", 14, 42);

  // LOG panel frame (Left side)
  lcd.drawRect(6, 102, 230, 188, TFT_DARKGREY);
  lcd.setTextColor(TFT_CYAN, TFT_BLACK);
  lcd.setTextSize(2);
  lcd.drawString("LOG", 14, 108);

  // RESULTS panel frame (Right side)
  lcd.drawRect(244, 102, 230, 188, TFT_DARKGREY);
  lcd.setTextColor(TFT_MAGENTA, TFT_BLACK);
  lcd.setTextSize(2);
  lcd.drawString("RESULTS", 252, 108);

  // Status bar divider
  lcd.drawFastHLine(0, 296, SCR_W, TFT_DARKGREY);
  lcd.setTextColor(TFT_WHITE, TFT_BLACK);
  lcd.setTextSize(2);
  lcd.drawString("RX", 28, 299);

  // Initial IP display status
  lcd.setTextColor(TFT_ORANGE, TFT_BLACK);
  lcd.drawString("Wait for System to Boot", 200, 299);
}

// Function to push standard actions into the LOG box
void addLogEntry(const char* msg) {
  // Shift array downward to make room for newest entry at index 0
  for (int i = MAX_LOGS - 1; i > 0; i--) {
    strncpy(log_buffer[i], log_buffer[i - 1], I2C_BUF_SIZE);
  }
  strncpy(log_buffer[0], msg, I2C_BUF_SIZE);
  if (log_count < MAX_LOGS) log_count++;

  // Redraw log area inside boundary
  lcd.fillRect(10, 130, 222, 155, TFT_BLACK);
  lcd.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
  lcd.setTextSize(1); 

  for (int i = 0; i < log_count; i++) {
    lcd.drawString(log_buffer[i], 14, 132 + (i * 24));
  }
}

void UpdateScreen() {
  uint32_t current_last_rx;
  noInterrupts();
  current_last_rx = lastRxMs;
  interrupts();

  // RX indicator: green if a message arrived reciently
  bool active = (millis() - current_last_rx) < 1500;
  lcd.fillCircle(14, 305, 6, active ? TFT_GREEN : TFT_ORANGE);

  lcd.startWrite();
  lcd.setTextColor(TFT_WHITE, TFT_BLACK);
  lcd.setTextSize(2);
  lcd.setCursor(28, 299);
  lcd.printf("RX:%-6d", rx_count);
  lcd.endWrite();
}

void setup() {
  Serial.begin(115200);
  
  Wire.begin((uint8_t)I2C_ADDR, SDA_PIN, SCL_PIN, 100000);
  Wire.onReceive(onReceive);

  lcd.init();
  lcd.setRotation(1); // Landscape mode (480x320)
  
  drawStaticGUI();
}

void loop() {
  // Update IP field if fresh IP data arrived
  if (ip_updated) {
    noInterrupts();
    strncpy(local_IP, IP, sizeof(local_IP));
    ip_updated = false;
    interrupts();

    lcd.startWrite();
    // Overwrite bottom status area reserved for IP string
    lcd.fillRect(200, 297, 275, 20, TFT_BLACK);
    lcd.setTextDatum(top_right);
    lcd.setTextColor(TFT_GREEN, TFT_BLACK);
    lcd.setTextSize(2);
    lcd.drawString(local_IP, 470, 299);
    lcd.setTextDatum(top_left);
    lcd.endWrite();
  }

  // Check if new payload packet arrived
  if (i2c_data_ready) {
    char temp_buf[I2C_BUF_SIZE];

    noInterrupts();
    strncpy(temp_buf, i2c_rx_buf, I2C_BUF_SIZE);
    current_len = rx_bytes_len;
    i2c_data_ready = false;
    interrupts();
    
    rx_count++;
    
    Serial.print("I2C Received [");
    Serial.print(rx_count);
    Serial.print("]: ");
    Serial.println(temp_buf);

    lcd.startWrite();
    
    // Push previous input into LOG before overwriting
    if (strlen(current_msg) > 0) {
      addLogEntry(current_msg);
    }
    
    strncpy(current_msg, temp_buf, I2C_BUF_SIZE);

    lcd.fillRect(14, 64, SCR_W - 28, 28, TFT_BLACK);
    lcd.setTextColor(TFT_CYAN, TFT_BLACK);
    lcd.setTextSize(2);
    lcd.drawString(current_msg, 14, 66);
    lcd.endWrite();
  }

  // Periodic GUI update for packet count and length
  static unsigned long last_update = 0;
  if (millis() - last_update > 100) {
    last_update = millis();

    UpdateScreen();
  }
}