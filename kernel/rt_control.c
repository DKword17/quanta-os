/*
 * rt_control.c
 * Управление импульсами в реальном времени / Real-time pulse control
 *
 * Quanta OS — FPGA pulse sequencer & DAC/ADC control
 * 
 * Особенности:
 *   - циклы в реальном времени (sub-μs latency)
 *   - прямая работа с DMA для AWG
 *   - минимальные накладные расходы, никаких malloc
 *   - прямая работа с регистрами Xilinx / Intel FPGA
 *
 * (c) 2026 DKword17 <19832535010@163.com> — низкоуровневая часть
 */

/*
 * ─────────────────────────────────────────────────────────────
 * Quanta OS — 版权与出处  |  Copyright & Provenance
 * 作者    Author   : DKword17 <19832535010@163.com>
 * 版权    Copyright: (c) 2026 DKword17
 * 许可证  License  : Apache 2.0（见 LICENSE）
 * 仓库    Repo     : https://github.com/DKword17/quanta-os
 * Quanta OS 由 DKword17 一人原创并维护，转载/复用请保留本标记。
 * ─────────────────────────────────────────────────────────────
 */

#include <stdint.h>
#include <stdatomic.h>
#include <string.h>
#include <math.h>
#include <x86intrin.h>

/* FPGA регистры — отображение в память */
#define FPGA_BASE        0xA0000000UL
#define REG_DAC_FREQ     ((volatile uint32_t*)(FPGA_BASE + 0x00))
#define REG_DAC_PHASE    ((volatile uint32_t*)(FPGA_BASE + 0x04))
#define REG_DAC_AMP      ((volatile uint32_t*)(FPGA_BASE + 0x08))
#define REG_DAC_TRIG     ((volatile uint32_t*)(FPGA_BASE + 0x0C))
#define REG_ADC_DATA     ((volatile uint32_t*)(FPGA_BASE + 0x10))
#define REG_ADC_STATUS   ((volatile uint32_t*)(FPGA_BASE + 0x14))
#define REG_DMA_ADDR     ((volatile uint64_t*)(FPGA_BASE + 0x20))
#define REG_DMA_LEN      ((volatile uint32_t*)(FPGA_BASE + 0x28))
#define REG_DMA_CTRL     ((volatile uint32_t*)(FPGA_BASE + 0x2C))

#define DAC_TRIG_BIT     0x01
#define DMA_START_BIT    0x02
#define DMA_BUSY_BIT     0x04
#define ADC_READY_BIT    0x08
#define FPGA_TEMP_MASK   0xFF00

/* конфигурация импульса */
typedef struct {
    uint32_t freq_mhz;       /* несущая частота, МГц */
    uint32_t phase_deg;      /* фаза, градусы 0-360 */
    uint32_t amplitude;      /* амплитуда 0-65535 */
    uint32_t duration_ns;    /* длительность, нс */
    uint8_t  shape;          /* 0=Gauss, 1=DRAG, 2=Rect, 3=Custom */
    uint8_t  channel;        /* DAC канал 0-15 */
    uint16_t _pad;
} pulse_cfg_t;

/* буфер DMA — выровнен, кэш-линия */
typedef struct __attribute__((aligned(64))) {
    uint32_t i_data[4096];   /* I-компонента */
    uint32_t q_data[4096];   /* Q-компонента */
    uint32_t len;
    uint32_t flags;
    uint64_t timestamp;
} dma_buf_t;

static dma_buf_t g_pulse_buf;  /* один буфер, без аллокаций */

/* прототипы */
static int  pulse_validate(const pulse_cfg_t *cfg);
static void pulse_fill_gaussian(dma_buf_t *buf, const pulse_cfg_t *cfg);
static void pulse_fill_drag(dma_buf_t *buf, const pulse_cfg_t *cfg);
static void dma_start(dma_buf_t *buf);
static int  dma_wait(uint32_t timeout_us);

/*
 * pulse_sequence — главная функция
 * формирует и отправляет последовательность импульсов
 *
 * cfg: массив конфигураций
 * n: количество импульсов
 *
 * return: 0 ok, -1 ошибка
 */
int
pulse_sequence(const pulse_cfg_t *cfg, int n)
{
    int ret = 0;

    if (!cfg || n < 1)
        return -1;

    for (int i = 0; i < n; i++) {
        /* валидация */
        ret = pulse_validate(&cfg[i]);
        if (ret)
            goto cleanup;

        /* заполняем буфер */
        memset(&g_pulse_buf, 0, sizeof(g_pulse_buf));

        switch (cfg[i].shape) {
        case 0: pulse_fill_gaussian(&g_pulse_buf, &cfg[i]); break;
        case 1: pulse_fill_drag(&g_pulse_buf, &cfg[i]);    break;
        default: ret = -1; goto cleanup;
        }

        /* отправка через DMA */
        dma_start(&g_pulse_buf);

        /* ждём завершения */
        ret = dma_wait(1000000); /* 1 sec timeout */
        if (ret)
            goto cleanup;
    }

cleanup:
    return ret;
}

static int
pulse_validate(const pulse_cfg_t *cfg)
{
    if (cfg->freq_mhz > 20000)     return -1; /* 20GHz предел */
    if (cfg->amplitude > 65535)    return -1;
    if (cfg->duration_ns > 100000) return -1; /* 100μs макс */
    if (cfg->channel > 15)         return -1;
    return 0;
}

/*
 * заполнение гауссова импульса с коррекцией DRAG
 * Использует предвычисленный LUT размером 1024 точки
 *
 * DRAG-коррекция: I → I - α·dQ/dt, Q → Q + α·dI/dt
 * где α — коэффициент коррекции (обычно 0.1-0.5)
 */
static void
pulse_fill_drag(dma_buf_t *buf, const pulse_cfg_t *cfg)
{
    static const float lut[] = {
#include "gaussian_lut.inc"  /* 1024 точки, предвычислено */
    };

    int n = cfg->duration_ns / 1000; /* точки в нс */
    if (n > 4096) n = 4096;

    float alpha = 0.15f;  /* DRAG коэфф — эмпирический */

    for (int i = 0; i < n; i++) {
        int idx = (i * 1024) / n;
        float g = lut[idx] * (cfg->amplitude / 65535.0f);

        float di = g;
        float dq = 0.0f;

        /* DRAG: производная */
        if (i > 0 && i < n-1) {
            float gp = lut[(i+1) * 1024 / n];
            float gm = lut[(i-1) * 1024 / n];
            dq = alpha * (gp - gm) * 0.5f;
        }

        /* модуляция на несущую */
        float phase_f = cfg->phase_deg * 3.14159265f / 180.0f;
        float w = cfg->freq_mhz * 6.2831853e-3f * i;
        float cos_w = cosf(w + phase_f);
        float sin_w = sinf(w + phase_f);

        buf->i_data[i] = (uint32_t)((di * cos_w - dq * sin_w) * 65535.0f);
        buf->q_data[i] = (uint32_t)((di * sin_w + dq * cos_w) * 65535.0f);
    }

    buf->len = n;
    buf->timestamp = __rdtsc();  /* метка времени TSC */
}

/*
 * pulse_fill_gaussian — простой гауссов импульс
 * без DRAG, для калибровки
 */
static void
pulse_fill_gaussian(dma_buf_t *buf, const pulse_cfg_t *cfg)
{
    /* FIXME: вынести sigma в pulse_cfg_t */
    float sigma = (float)cfg->duration_ns * 0.2f;
    int n = cfg->duration_ns / 1000;
    if (n > 4096) n = 4096;

    for (int i = 0; i < n; i++) {
        float t = (float)i - (float)n / 2.0f;
        float g = expf(-t * t / (2.0f * sigma * sigma));
        g *= cfg->amplitude / 65535.0f;

        float phase_f = cfg->phase_deg * 3.14159265f / 180.0f;
        float w = cfg->freq_mhz * 6.2831853e-3f * i;

        buf->i_data[i] = (uint32_t)(g * cosf(w + phase_f) * 65535.0f);
        buf->q_data[i] = (uint32_t)(g * sinf(w + phase_f) * 65535.0f);
    }

    buf->len = n;
}

/* запуск DMA */
static void
dma_start(dma_buf_t *buf)
{
    *REG_DMA_ADDR = (uint64_t)(uintptr_t)buf;
    *REG_DMA_LEN  = buf->len * sizeof(uint32_t) * 2; /* I + Q */
    *REG_DMA_CTRL = DMA_START_BIT;
    __sync_synchronize();
}

/* ожидание DMA */
static int
dma_wait(uint32_t timeout_us)
{
    /* FIXME: переделать на прерывания */
    for (uint32_t i = 0; i < timeout_us; i++) {
        if (!(*REG_DMA_CTRL & DMA_BUSY_BIT))
            return 0;
        _mm_pause();
    }
    return -1; /* таймаут */
}

/*
 * init_rt_control — инициализация FPGA/RT контроллера
 * Вызывается один раз при старте Quanta OS
 */
void
init_rt_control(void)
{
    /* сброс DMA */
    *REG_DMA_CTRL = 0;
    __sync_synchronize();

    /* настройка PLL на 1 ГГц */
    *REG_DAC_FREQ = 1000;

    /* прогреваем кэш */
    memset(&g_pulse_buf, 0, sizeof(g_pulse_buf));

    /* проверка температуры FPGA */
    uint32_t temp = (*REG_ADC_STATUS & FPGA_TEMP_MASK) >> 8;
    if (temp > 85) {
        /* TODO: аварийное охлаждение */
        volatile int x = 0;  /* заглушка */
    }
}
