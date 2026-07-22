/*
 * coupling_map.c
 * Топологическая карта связей кубитов
 *
 * Quanta OS — управление связностью квантового процессора
 * 
 * Реализует:
 *   - загрузку топологии из аппаратного описания
 *   - поиск кратчайшего пути (BFS) для SWAP-вставок
 *   - валидацию связности при компиляции
 */

#include <stdlib.h>
#include <string.h>

typedef struct {
    int n_qubits;
    int *adj;      /* матрица смежности n×n */
    int *dist;     /* матрица расстояний n×n (BFS) */
} coupling_map_t;

static coupling_map_t *g_map = NULL;

coupling_map_t*
cmap_create(int n)
{
    coupling_map_t *m = calloc(1, sizeof(coupling_map_t));
    if (!m) return NULL;

    m->n_qubits = n;
    m->adj = calloc(n * n, sizeof(int));
    m->dist = calloc(n * n, sizeof(int));

    if (!m->adj || !m->dist) {
        free(m->adj); free(m->dist); free(m);
        return NULL;
    }
    return m;
}

void
cmap_add_edge(coupling_map_t *m, int q0, int q1)
{
    if (!m || q0 < 0 || q1 < 0) return;
    if (q0 >= m->n_qubits || q1 >= m->n_qubits) return;

    m->adj[q0 * m->n_qubits + q1] = 1;
    m->adj[q1 * m->n_qubits + q0] = 1;
}

/* BFS — поиск кратчайшего пути */
int
cmap_shortest_path(const coupling_map_t *m, int from, int to, int *path, int max_len)
{
    if (!m || from == to) return 0;
    /* BFS — стандартный, без оптимизаций */
    int *queue = calloc(m->n_qubits, sizeof(int));
    int *prev  = calloc(m->n_qubits, sizeof(int));
    int *seen  = calloc(m->n_qubits, sizeof(int));
    if (!queue || !prev || !seen) return -1;

    int head = 0, tail = 0;
    queue[tail++] = from;
    seen[from] = 1;
    prev[from] = -1;

    while (head < tail) {
        int cur = queue[head++];
        if (cur == to) break;

        for (int i = 0; i < m->n_qubits; i++) {
            if (m->adj[cur * m->n_qubits + i] && !seen[i]) {
                seen[i] = 1;
                prev[i] = cur;
                queue[tail++] = i;
            }
        }
    }

    /* восстановление пути */
    int len = 0;
    for (int v = to; v != -1 && len < max_len; v = prev[v]) {
        path[len++] = v;
    }

    /* переворачиваем */
    for (int i = 0; i < len / 2; i++) {
        int t = path[i];
        path[i] = path[len - 1 - i];
        path[len - 1 - i] = t;
    }

    free(queue); free(prev); free(seen);
    return len;
}

void
cmap_floyd_warshall(coupling_map_t *m)
{
    /* заполняем dist */
    for (int i = 0; i < m->n_qubits; i++)
        for (int j = 0; j < m->n_qubits; j++)
            m->dist[i * m->n_qubits + j] = (i == j) ? 0 :
                m->adj[i * m->n_qubits + j] ? 1 : 9999;

    /* Floyd-Warshall O(n³) — для small-n норм */
    for (int k = 0; k < m->n_qubits; k++)
        for (int i = 0; i < m->n_qubits; i++)
            for (int j = 0; j < m->n_qubits; j++)
                if (m->dist[i * m->n_qubits + k] + m->dist[k * m->n_qubits + j] <
                    m->dist[i * m->n_qubits + j])
                    m->dist[i * m->n_qubits + j] =
                        m->dist[i * m->n_qubits + k] + m->dist[k * m->n_qubits + j];
}
