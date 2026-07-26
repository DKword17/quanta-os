/**
 * kernel/hal/qubit_abstract.h
 * Quanta OS — 量子比特硬件抽象层 (HAL)
 *
 * 定义所有量子计算架构的通用接口。
 * 每家芯片商实现一个 hal_backend_t，注册到全局后端表。
 */

#ifndef QUANTA_HAL_H
#define QUANTA_HAL_H

#include <stdint.h>
#include <stddef.h>

/* ========== 量子比特物理实现类型 ========== */

typedef enum {
    QUBIT_TYPE_UNKNOWN = 0,
    
    /* 超导量子比特 (Superconducting) */
    QUBIT_TYPE_TRANSMON,        /* 传输子 (IBM, Google, Rigetti, 本源量子) */
    QUBIT_TYPE_XMON,            /* Xmon (Google) */
    QUBIT_TYPE_FLUXONIUM,       /* 磁通量子比特 */
    QUBIT_TYPE_FLUX_QUBIT,      /* 磁通量子比特 (中科院/国盾) */
    
    /* 离子阱 (Trapped Ion) */
    QUBIT_TYPE_TRAPPED_ION_LASER,    /* 激光驱动 (IonQ) */
    QUBIT_TYPE_TRAPPED_ION_MICROWAVE, /* 微波驱动 (Quantinuum/Honeywell) */
    
    /* 光量子 (Photonic) */
    QUBIT_TYPE_PHOTONIC_SQUEEZED,    /* 压缩态 (Xanadu) */
    QUBIT_TYPE_PHOTONIC_SINGLE,      /* 单光子 (PsiQuantum, 图灵量子) */
    
    /* 中性原子 (Neutral Atom) */
    QUBIT_TYPE_RYDBERG_LASER,        /* Rydberg 激光 (QuEra, Pasqal) */
    QUBIT_TYPE_OPTICAL_TWEEZER,      /* 光镊 (Atom Computing) */
    
    /* 硅基自旋 (Silicon Spin) */
    QUBIT_TYPE_SI_DOT,               /* Si/SiGe 量子点 (Intel) */
    QUBIT_TYPE_DONOR,                /* 施主量子比特 (Diraq) */
    
    /* 金刚石NV色心 (NV Center) */
    QUBIT_TYPE_NV_CENTER,            /* 室温 NV 色心 (Quantum Brilliance, 国仪量子) */
    
    /* 拓扑 (Topological) */
    QUBIT_TYPE_MAJORANA,             /* Majorana 零模 (Microsoft Station Q) */
    
    /* 其他 */
    QUBIT_TYPE_NMR,                  /* 核磁共振 (实验室) */
    QUBIT_TYPE_COUNT
} qubit_physical_type_t;

/* ========== 架构特性描述 ========== */

typedef struct {
    const char         *vendor_name;         /* 厂商/项目名 */
    qubit_physical_type_t qubit_type;
    uint32_t           max_qubits;           /* 最大 qubit 数 */
    uint32_t           n_physical_qubits;    /* 当前物理 qubit 数 */
    
    /* 操作温度 */
    float              operating_temp_mk;    /* mK (0 = 室温) */
    
    /* 门集特征 */
    uint32_t           native_gate_count;
    float              typical_1q_fidelity;  /* 单量子门保真度 */
    float              typical_2q_fidelity;  /* 两量子门保真度 */
    float              readout_fidelity;     /* 读出保真度 */
    
    /* 相干时间 */
    float              t1_us;               /* 能量弛豫 (μs) */
    float              t2_us;               /* 相位弛豫 (μs) */
    
    /* 控制方式 */
    uint8_t            control_channels_per_qubit; /* 控制通道数 */
    float              gate_speed_ns;        /* 单门典型耗时 (ns) */
    
    /* 拓扑 */
    uint8_t            max_connectivity;     /* 最大连通度 */
    uint8_t            is_all_to_all;        /* 全连通? (离子阱) */
    
    /* 特殊能力 */
    uint8_t            supports_mid_circuit_measurement;
    uint8_t            supports_feedforward; /* 实时反馈 */
    uint8_t            supports_quantum_networking; /* 量子网络 */
    
    /* 运行环境 */
    uint8_t            requires_dilution_fridge;  /* 需要稀释制冷机? */
    uint8_t            requires_vacuum;           /* 需要真空? */
    uint8_t            requires_laser;            /* 需要激光? */
} architecture_spec_t;

/* ========== 原生门集枚举 (全架构统一) ========== */

typedef enum {
    /* 单量子门 */
    NATIVE_GATE_I,         /* Identity */
    NATIVE_GATE_X,         /* Pauli-X (π pulse) */
    NATIVE_GATE_Y,         /* Pauli-Y */
    NATIVE_GATE_Z,         /* Pauli-Z (virtual or physical) */
    NATIVE_GATE_H,         /* Hadamard */
    NATIVE_GATE_S,         /* Phase (π/2) */
    NATIVE_GATE_T,         /* T (π/4) */
    NATIVE_GATE_SX,        /* Sqrt(X) */
    NATIVE_GATE_U3,        /* 任意单量子门 U(θ,φ,λ) */
    
    /* 两量子门 */
    NATIVE_GATE_CX,        /* CNOT (受控X) */
    NATIVE_GATE_CZ,        /* CZ (受控Z) */
    NATIVE_GATE_SWAP,      /* SWAP */
    NATIVE_GATE_ISWAP,     /* iSWAP (超导) */
    NATIVE_GATE_FSWAP,     /* fSWAP (费米子) */
    NATIVE_GATE_XX,        /* XX 交互 (离子阱) */
    NATIVE_GATE_YY,        /* YY 交互 */
    NATIVE_GATE_ZZ,        /* ZZ 交互 */
    NATIVE_GATE_MS,        /* Molmer-Sorensen (离子阱多体) */
    NATIVE_GATE_CCZ,       /* Toffoli (CCZ) */
    
    /* 测量 */
    NATIVE_GATE_MEASURE,   /* 投影测量 */
    NATIVE_GATE_MEASURE_RESET, /* 测量+复位 */
    
    /* 光量子专用 */
    NATIVE_GATE_SQZ,       /* 压缩操作 (Xanadu) */
    NATIVE_GATE_BS,        /* 分束器 (photonic) */
    NATIVE_GATE_PS,        /* 相移器 (photonic) */
    
    /* 控制 */
    NATIVE_GATE_RESET,     /* 复位到|0⟩ */
    NATIVE_GATE_BARRIER,   /* 同步屏障 */
    
    NATIVE_GATE_COUNT
} native_gate_id_t;

/* ========== 脉冲参数 ========== */

typedef struct {
    native_gate_id_t   gate_id;
    float              amplitude;            /* 脉冲幅度 (归一化 0~1) */
    float              duration_ns;          /* 脉冲宽度 (ns) */
    float              frequency_offset_mhz; /* 频率偏移 */
    float              phase;                /* 载波相位 (rad) */
    float              sigma_ratio;          /* 高斯脉冲 sigma ratio */
    float              drag_coefficient;     /* DRAG 修正系数 */
    uint8_t            target_qubits[2];     /* 目标 qubit */
    uint8_t            n_targets;            /* 目标数 */
} pulse_profile_t;

/* ========== 校准参数 ========== */

typedef struct {
    float  rabi_frequency_mhz;      /* Rabi 频率 */
    float  pi_pulse_amplitude;      /* π 脉冲幅度 */
    float  pi_half_amplitude;       /* π/2 脉冲幅度 */
    float  t1_us;                   /* 最新 T1 */
    float  t2_us;                   /* 最新 T2 */
    float  readout_angle;           /* 读出旋转角 */
    float  anharmonicity_mhz;       /* 非简谐性 */
    float  ac_stark_shift;          /* AC Stark 偏移 */
} qubit_calibration_t;

/* ========== 后端操作接口 ========== */

/* 每个物理架构实现这个接口 */
typedef struct quanta_backend {
    const char *name;                       /* 后端名称，如 "ibm_superconducting" */
    architecture_spec_t spec;               /* 架构规格 */
    
    /* 生命周期 */
    int  (*init)(struct quanta_backend *self);         /* 硬件初始化 */
    int  (*calibrate)(struct quanta_backend *self);    /* 全芯片校准 */
    void (*shutdown)(struct quanta_backend *self);     /* 安全关闭 */
    
    /* 脉冲执行 */
    int  (*apply_pulse)(struct quanta_backend *self, const pulse_profile_t *pulse);
    int  (*apply_pulse_sequence)(struct quanta_backend *self, const pulse_profile_t *seq, uint32_t n);
    
    /* 测量 */
    int  (*measure)(struct quanta_backend *self, uint32_t qubit, uint32_t *result);
    int  (*measure_all)(struct quanta_backend *self, uint32_t *results, uint32_t n);
    
    /* 校准更新 */
    int  (*update_calibration)(struct quanta_backend *self, uint32_t qubit, qubit_calibration_t *cal);
    
    /* 拓扑信息 */
    int  (*get_topology)(struct quanta_backend *self, uint32_t **coupling_map, uint32_t *n_edges);
    
    /* 自演化钩子 */
    int  (*self_evolve_step)(struct quanta_backend *self, float feedback_fidelity);
    
    /* 私有数据 */
    void *priv;
} quanta_backend_t;

/* ========== 全局后端注册表 ========== */

#define MAX_BACKENDS 16

typedef struct {
    quanta_backend_t *backends[MAX_BACKENDS];
    uint32_t          count;
    quanta_backend_t *active;     /* 当前活跃后端 */
} backend_registry_t;

extern backend_registry_t g_backends;

/* 后端注册/选择 */
int  register_backend(quanta_backend_t *backend);
int  select_backend(const char *name);
quanta_backend_t* detect_and_select(void);  /* 自动检测硬件 */

/* ========== 内置后端声明 ========== */

/* 超导 */
int  superconducting_init(quanta_backend_t *be, const char *variant);

/* 离子阱 */
int  trapped_ion_init(quanta_backend_t *be, const char *variant);

/* 光量子 */
int  photonic_init(quanta_backend_t *be, const char *variant);

/* 中性原子 */
int  neutral_atom_init(quanta_backend_t *be, const char *variant);

/* 硅基自旋 */
int  silicon_spin_init(quanta_backend_t *be, const char *variant);

/* NV 色心 */
int  nv_center_init(quanta_backend_t *be, const char *variant);

/* 拓扑 */
int  topological_init(quanta_backend_t *be);

#endif /* QUANTA_HAL_H */
