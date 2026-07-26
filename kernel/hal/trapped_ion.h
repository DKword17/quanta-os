/**
 * kernel/hal/trapped_ion.h
 * 离子阱量子比特架构参数
 * 覆盖: IonQ, Quantinuum (Honeywell), 启科量子
 */

#include "qubit_abstract.h"

typedef struct {
    const char *vendor;
    const char *model;
    uint32_t   qubits;
    float      t1_us;        /* 离子阱 T1 = 相干时间极长 */
    float      t2_us;        /* 相位相干秒级 */
    float      gate_fidelity_1q;
    float      gate_fidelity_2q;
    float      gate_time_us;  /* 离子阱门耗时 μs 级 */
    uint8_t    all_to_all;    /* 全连通? */
    uint8_t    laser_based;   /* 1=激光, 0=微波 */
} trapped_ion_vendor_t;

static const trapped_ion_vendor_t known_trapped_ion[] = {
    /* IonQ — Yb+ 离子阱，激光驱动，全连通 */
    {"IonQ",        "IonQ Aria",     25,  1e6, 5e5, 0.9997, 0.996, 200, 1, 1},
    {"IonQ",        "IonQ Forte",    36,  1e6, 5e5, 0.9998, 0.997, 180, 1, 1},
    {"IonQ",        "IonQ Tempo",    64,  1e6, 5e5, 0.9999, 0.998, 150, 1, 1},
    
    /* Quantinuum (Honeywell) — Yb+，CCD 架构，微波+激光 */
    {"Quantinuum",  "H2",            56,  2e6, 1e6, 0.9999, 0.9995, 100, 1, 0},
    {"Quantinuum",  "H1 5.0",        20,  1e6, 1e5, 0.9995, 0.993, 300, 1, 0},
    
    /* 启科量子 */
    {"启科量子", "AbaQ v1",         16,  5e5, 2e5, 0.9990, 0.990, 250, 1, 1},
    
    {NULL}
};

void trapped_ion_get_defaults(architecture_spec_t *spec);
