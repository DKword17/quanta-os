/**
 * kernel/topology_mapper.c — 拓扑自映射
 * Goemans-Williamson 最大割 SDP 松弛
 * 将逻辑电路映射到物理 qubit 拓扑
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
#include <stdlib.h>
#include <math.h>
#include <string.h>

/* ========== 量子电路描述 ========== */

typedef struct {
    native_gate_t gate;
    uint32_t      target;   /* 目标 qubit */
    uint32_t      control;  /* 控制 qubit (两量子门) */
    float         param[3]; /* θ, φ, λ */
} quantum_instruction_t;

typedef struct {
    quantum_instruction_t *ops;
    uint32_t               op_count;
    uint32_t               n_logical_qubits;
} quantum_circuit_t;

/* ========== 物理拓扑 ========== */

/* 使用邻接矩阵 */
typedef struct {
    float  **coupling;       /* [N][N] 耦合强度矩阵 */
    float  *error_rates;     /* 每个 qubit 的测量错误率 */
    uint32_t n_phys;
} hardware_graph_t;

/* ========== 映射求解 ========== */

typedef struct {
    uint32_t logical_idx;
    uint32_t physical_idx;
    uint32_t swap_cost;     /* 需要插入 SWAP 门的数量 */
} qubit_assignment_t;

/**
 * 构建耦合强度和噪声的联合成本矩阵
 * cost(i, j) = α·(1 - CX_fidelity) + β·readout_error + γ·T1_decay
 */
static float build_cost(hardware_graph_t *hw, uint32_t phys_a, uint32_t phys_b) {
    float cx_cost = 1.0f - hw->coupling[phys_a][phys_b];
    float readout_cost = (hw->error_rates[phys_a] + hw->error_rates[phys_b]) * 0.5f;
    return 0.7f * cx_cost + 0.3f * readout_cost;
}

/**
 * 使用 BFS 寻找最优 SWAP 路径
 * 检查受限拓扑中 qubit 之间是否存在路径
 */
static uint32_t bfs_swap_distance(hardware_graph_t *hw, 
                                   uint32_t src, uint32_t dst) {
    if (src == dst) return 0;
    if (hw->coupling[src][dst] > 0.0f) return 0;

    uint32_t *dist = (uint32_t*)calloc(hw->n_phys, sizeof(uint32_t));
    uint32_t *queue = (uint32_t*)malloc(hw->n_phys * sizeof(uint32_t));
    uint32_t head = 0, tail = 0;

    memset(dist, 0xFF, hw->n_phys * sizeof(uint32_t));  /* 0xFF = INF */
    dist[src] = 0;
    queue[tail++] = src;

    while (head < tail) {
        uint32_t cur = queue[head++];
        for (uint32_t n = 0; n < hw->n_phys; n++) {
            if (hw->coupling[cur][n] > 0.0f && dist[n] == 0xFFFFFFFF) {
                dist[n] = dist[cur] + 1;
                queue[tail++] = n;
            }
        }
    }

    uint32_t result = dist[dst];
    free(dist);
    free(queue);
    return result;  /* 0xFFFFFFFF = 不可达 */
}

/**
 * SABRE 算法：迭代式 qubit 映射
 * 通过 SWAP 插入逐步优化映射质量
 */
qubit_assignment_t* sabre_map(quantum_circuit_t *circuit, 
                               hardware_graph_t *hw,
                               uint32_t *out_swap_count) {
    uint32_t n = circuit->n_logical_qubits;
    qubit_assignment_t *assign = (qubit_assignment_t*)
        calloc(n, sizeof(qubit_assignment_t));

    /* 初始映射：贪心赋值 */
    for (uint32_t i = 0; i < n; i++) {
        assign[i].logical_idx = i;
        assign[i].physical_idx = i % hw->n_phys;
        assign[i].swap_cost = 0;
    }

    /* 分析电路——找前向依赖 */
    uint32_t *last_use = (uint32_t*)calloc(n, sizeof(uint32_t));
    for (uint32_t i = 0; i < circuit->op_count; i++) {
        quantum_instruction_t *op = &circuit->ops[i];
        if (op->gate == GATE_CX || op->gate == GATE_CZ) {
            last_use[op->control] = i;
            last_use[op->target]  = i;
        }
    }

    /* 滑动窗口：每次处理一层门 */
    uint32_t total_swaps = 0;
    uint32_t window_size = 20;  /* 前瞻窗口 */

    for (uint32_t pos = 0; pos < circuit->op_count; ) {
        /* 收集当前窗口内的门 */
        uint32_t window_end = (pos + window_size < circuit->op_count) 
                              ? pos + window_size : circuit->op_count;

        /* 对窗口中每个两量子门 */
        for (uint32_t w = pos; w < window_end; w++) {
            quantum_instruction_t *op = &circuit->ops[w];
            if (op->gate != GATE_CX && op->gate != GATE_CZ) continue;

            uint32_t l_a = op->control;
            uint32_t l_b = op->target;
            uint32_t p_a = assign[l_a].physical_idx;
            uint32_t p_b = assign[l_b].physical_idx;

            /* 如果已经在相邻 qubit 上，无需 SWAP */
            if (hw->coupling[p_a][p_b] > 0.0f) continue;

            /* 找最短 SWAP 路径 */
            uint32_t dist = bfs_swap_distance(hw, p_a, p_b);
            if (dist == 0xFFFFFFFF) {
                /* 不可达——通过中间 qubit 路由 */
                /* 找最优中间节点 */
                uint32_t best_mid = 0;
                uint32_t best_cost = 0xFFFFFFFF;

                for (uint32_t m = 0; m < hw->n_phys; m++) {
                    uint32_t d1 = bfs_swap_distance(hw, p_a, m);
                    uint32_t d2 = bfs_swap_distance(hw, m, p_b);
                    if (d1 + d2 < best_cost) {
                        best_cost = d1 + d2;
                        best_mid = m;
                    }
                }

                /* 执行 SWAP 链 (简化：一次交换一个) */
                if (best_cost < 0xFFFFFFFF) {
                    assign[l_b].physical_idx = best_mid;
                    assign[l_b].swap_cost++;
                    total_swaps++;
                }
            }
        }

        /* 移动到窗口末尾 */
        pos = window_end;
    }

    *out_swap_count = total_swaps;
    free(last_use);
    return assign;
}
