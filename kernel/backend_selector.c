/**
 * kernel/backend_selector.c
 * Quanta OS — 自动后端选择器
 * 
 * 启动时通过硬件探测自动选择最优后端，
 * 也支持手动指定 vendor/model。
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

#include "hal/qubit_abstract.h"
#include <string.h>

/* Local helpers, defined below the call sites — forward-declared here so the
 * calls above are properly prototyped (avoids implicit-declaration warnings). */
static uint32_t probe_hardware_id(void);
static qubit_physical_type_t identify_controller_type(void);
static int read_control_register(uint32_t addr, uint32_t *value);

backend_registry_t g_backends = {0};

int register_backend(quanta_backend_t *backend) {
    if (g_backends.count >= MAX_BACKENDS)
        return -1;  /* 注册表满 */
    
    g_backends.backends[g_backends.count++] = backend;
    return 0;
}

int select_backend(const char *name) {
    for (uint32_t i = 0; i < g_backends.count; i++) {
        if (g_backends.backends[i]->name &&
            strcmp(g_backends.backends[i]->name, name) == 0) {
            g_backends.active = g_backends.backends[i];
            return 0;
        }
    }
    return -1;  /* 未找到 */
}

/**
 * 自动检测硬件并选择最优后端
 *
 * 检测流程:
 * 1. 扫描 PCI/SPI 总线查找 FPGA 控制卡
 * 2. 读取硬件 ID 寄存器
 * 3. 匹配已注册后端
 * 4. 执行校准 → 验证可行性
 * 5. 激活最佳匹配
 */
quanta_backend_t* detect_and_select(void) {
    uint32_t hw_id = probe_hardware_id();
    
    /* 探测硬件类型 */
    qubit_physical_type_t detected = QUBIT_TYPE_UNKNOWN;
    
    /* 尝试读取 qubit 控制器的识别寄存器 */
    /* 每种架构有唯一的控制接口特征 */
    detected = identify_controller_type();
    
    if (detected == QUBIT_TYPE_UNKNOWN) {
        /* 无法自动识别 → 回退到手动指定或模拟模式 */
        return NULL;
    }
    
    /* 在注册表中找匹配 */
    for (uint32_t i = 0; i < g_backends.count; i++) {
        quanta_backend_t *be = g_backends.backends[i];
        if (be->spec.qubit_type == detected) {
            if (be->init(be) == 0) {
                g_backends.active = be;
                return be;
            }
        }
    }
    
    return NULL;
}

/**
 * 探测控制器类型
 * 读取 FPGA/MCU 硬件 ID 寄存器来判断连接了什么量子处理器
 */
static qubit_physical_type_t identify_controller_type(void) {
    /* 尝试读取标准硬件 ID 寄存器 (地址 0x7F00) */
    uint32_t hw_id = 0;
    int ret = read_control_register(0x7F00, &hw_id);
    
    if (ret != 0) {
        /* 可能没有真实硬件 → 运行在模拟模式 */
        return QUBIT_TYPE_UNKNOWN;
    }
    
    /* 硬件 ID → 架构映射 */
    switch (hw_id & 0xFF) {
        case 0x01: return QUBIT_TYPE_TRANSMON;        /* IBM/本源超导 */
        case 0x02: return QUBIT_TYPE_XMON;            /* Google Xmon */
        case 0x10: return QUBIT_TYPE_TRAPPED_ION_LASER;  /* IonQ */
        case 0x11: return QUBIT_TYPE_TRAPPED_ION_MICROWAVE; /* Quantinuum */
        case 0x20: return QUBIT_TYPE_PHOTONIC_SQUEEZED;  /* Xanadu */
        case 0x21: return QUBIT_TYPE_PHOTONIC_SINGLE;  /* PsiQuantum */
        case 0x30: return QUBIT_TYPE_RYDBERG_LASER;    /* QuEra */
        case 0x40: return QUBIT_TYPE_SI_DOT;           /* Intel */
        case 0x41: return QUBIT_TYPE_DONOR;            /* Diraq */
        case 0x50: return QUBIT_TYPE_NV_CENTER;        /* Quantum Brilliance */
        default:   return QUBIT_TYPE_UNKNOWN;
    }
}

/* 简化硬件寄存器读写（实际实现依赖具体平台） */
static int read_control_register(uint32_t addr, uint32_t *value) {
    /* 在实际硬件上这里做 PCI MMIO 或 SPI 读取 */
    /* 开发/模拟模式：返回 -1 表示无硬件 */
    return -1;
}

static uint32_t probe_hardware_id(void) {
    uint32_t id = 0;
    if (read_control_register(0x7FF0, &id) != 0)
        return 0;
    return id;
}
