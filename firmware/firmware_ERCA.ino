/**
 * ERCA Real-Time Telemetry Streamer
 */

#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "driver/ledc.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_timer.h"

class TelemetryStreamer {
private:
    // --- PIN & PERIPHERAL DESIGNATIONS ---
    static constexpr gpio_num_t MOTOR_IN1        = GPIO_NUM_25;
    static constexpr gpio_num_t MOTOR_IN2        = GPIO_NUM_26;
    static constexpr ledc_channel_t PWM_CHANNEL  = LEDC_CHANNEL_0;
    
    // --- CALIBRATION & MATHEMATICAL MATRIX ---
    static constexpr float SENSOR_SENSITIVITY    = 0.185f; 
    static constexpr float TERMINAL_RESISTANCE   = 3.5f;   
    static constexpr float MOTOR_KV              = 130.0f; 

    adc_oneshot_unit_handle_t adc_handle;
    adc_channel_t adc_chan;
    uint32_t active_pwm_val;

public:
    TelemetryStreamer(adc_channel_t channel) : adc_chan(channel), active_pwm_val(220) {}

    void init_hardware() {
        // Initialize GPIO pins for H-Bridge Direction Controller
        gpio_reset_pin(MOTOR_IN1);
        gpio_reset_pin(MOTOR_IN2);
        gpio_set_direction(MOTOR_IN1, GPIO_MODE_OUTPUT);
        gpio_set_direction(MOTOR_IN2, GPIO_MODE_OUTPUT);
        
        gpio_set_level(MOTOR_IN1, 1);
        gpio_set_level(MOTOR_IN2, 0);

        // Configure ESP32 Native LEDC Peripheral for High-Frequency PWM
        ledc_timer_config_t ledc_timer = {
            .speed_mode       = LEDC_LOW_SPEED_MODE,
            .duty_resolution  = LEDC_TIMER_8_BIT,
            .timer_num        = LEDC_TIMER_0,
            .freq_hz          = 5000,
            .clk_cfg          = LEDC_AUTO_CLK
        };
        ledc_timer_config(&ledc_timer);

        ledc_channel_config_t ledc_channel = {
            .gpio_num       = GPIO_NUM_27,
            .speed_mode     = LEDC_LOW_SPEED_MODE,
            .channel        = PWM_CHANNEL,
            .intr_type      = LEDC_INTR_DISABLE,
            .timer_sel      = LEDC_TIMER_0,
            .duty           = active_pwm_val,
            .hpoint         = 0
        };
        ledc_channel_config(&ledc_channel);

        // Initialize Low-Level ADC Oneshot Driver Unit
        adc_oneshot_unit_init_cfg_t init_config = { .unit_id = ADC_UNIT_1 };
        adc_oneshot_new_unit(&init_config, &adc_handle);

        adc_oneshot_chan_cfg_t config = {
            .atten = ADC_ATTEN_DB_12, // Supports full 0-3.3V dynamic range
            .bitwidth = ADC_BITWIDTH_12
        };
        adc_oneshot_config_channel(adc_handle, adc_chan, &config);
    }

    /**
     * @brief High-Fidelity Non-Blocking Telemetry Streaming Worker
     * Executed within a dedicated FreeRTOS Thread Task Context.
     */
    static void telemetry_task_worker(void* pvParameters) {
        TelemetryStreamer* instance = static_cast<TelemetryStreamer*>(pvParameters);
        TickType_t last_wake_time = xTaskGetTickCount();
        const TickType_t sampling_period_ticks = pdMS_TO_TICKS(50); // Hard deterministic 20Hz frequency

        while (true) {
            int raw_adc = 0;
            adc_oneshot_read(instance->adc_handle, instance->adc_chan, &raw_adc);
            
            // Execute State-Observer calculations
            float sample_v = (raw_adc / 4095.0f) * 3.3f;
            float unscaled_sensor_v = sample_v * 1.5f; 
            float current_ma = ((unscaled_sensor_v - 2.5f) / SENSOR_SENSITIVITY) * 1000.0f;
            if (current_ma < 0.0f) current_ma = 0.0f;

            float applied_voltage = (instance->active_pwm_val / 255.0f) * 12.0f;
            float back_emf = applied_voltage - ((current_ma / 1000.0f) * TERMINAL_RESISTANCE);
            float estimated_rpm = (back_emf < 0) ? 0.0f : back_emf * MOTOR_KV;

            // Stream Structured Protocol Array out via VFS Console
            printf("DATA_FRAME,%lld,%.1f,%.1f,%lu\n", 
                   esp_timer_get_time() / 1000, // Native microseconds downscaled to Epoch MS
                   current_ma, 
                   estimated_rpm, 
                   instance->active_pwm_val);

            // Relinquish CPU slice deterministically
            vTaskDelayUntil(&last_wake_time, sampling_period_ticks);
        }
    }
};

// Allocate the tracking object globally in the sketch scope
// Change ADC_CHANNEL_6 if your sensor is on pin 34 (ADC_CHANNEL_0 maps to pin 36)
static TelemetryStreamer streamer(ADC_CHANNEL_6); 

void setup() {
    // Note: Serial.begin() is handled under the hood by the core framework initialization,
    // but we can let the application engine complete boot sequence.
    delay(1000); 

    streamer.init_hardware();

    // Spawn a dedicated, prioritized FreeRTOS telemetry thread
    xTaskCreatePinnedToCore(
        TelemetryStreamer::telemetry_task_worker,
        "ERCA_Telemetry_Task",
        4096,                       // Stack size safety headroom
        &streamer,                  // Handle context pass-through
        configMAX_PRIORITIES - 2,     // High priority execution scheduling
        nullptr,
        1                           // Pinned to Core 1
    );
}

void loop() {
    // Keep this completely empty. 
    // The execution loop has been offloaded entirely to the real-time FreeRTOS task worker thread above.
    vTaskDelay(pdMS_TO_TICKS(1000)); // Sleep background thread safely to keep watchdog happy
}
