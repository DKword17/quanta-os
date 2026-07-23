# Quanta OS — Architectural Overview

**Document Reference:** QOS-ARCH-001  
**Author:** William Thorpe, MEng (Cantab.)  
**Date:** 26th July 2026  
**Status:** Draft for Review  
**Version:** 0.9.1  

---

## 1. Scope and Purpose

This document describes the high-level architecture of the Quanta OS
system, a microkernel-based operating environment for executing,
scheduling, and calibrating quantum computations across heterogeneous
physical backends.

The intended readership includes systems architects, kernel engineers,
and principal investigators evaluating the platform for deployment in
academic or industrial quantum computing facilities.

**Key design objectives:**

 - **Portability:** Support for seven distinct qubit modalities via a
   unified hardware abstraction layer (see §3.2).
 - **Determinism:** Real-time pulse generation through FPGA-coupled
   kernel primitives, with worst-case interrupt latency below 1 μs.
 - **Composability:** A protocol-agnostic middleware layer that permits
   the simultaneous operation of multiple compilation strategies,
   scheduling policies, and error-correction codes.

---

## 2. System Architecture

Quanta OS follows a layered architecture, in which each layer
communicates with its immediate neighbours through well-defined
interfaces. Figure 2.1 below illustrates the principal layers.

```
 ┌───────────────────────────────────────────────────────────────┐
 │                     User / Cloud Interface                     │
 │  (REST API, gRPC, Python SDK, CLI)                            │
 ├───────────────────────────────────────────────────────────────┤
 │               Compiler & Optimisation Middleware                │
 │  QASM parsing  →  Gate decomposition  →  Topology mapping     │
 ├───────────────────────────────────────────────────────────────┤
 │              Resource Scheduler & Job Manager                   │
 │  Priority queues  →  Compatibility packing  →  Load balancing │
 ├───────────────────────────────────────────────────────────────┤
 │                 Error Correction & Calibration                  │
 │  Surface code encoding  →  Kalman filtering  →  RB fidelity   │
 ├───────────────────────────────────────────────────────────────┤
 │                   Hardware Abstraction Layer                    │
 │     Superconducting  ·  Ion Trap  ·  Photonic  ·  Neutral      │
 │     Silicon Spin  ·  NV Centre  ·  Topological                 │
 ├───────────────────────────────────────────────────────────────┤
 │                  Kernel (Microkernel, ≤ 64 KB)                  │
 │  Memory management  ·  FPGA DMA control  ·  ISR dispatching    │
 │  Zero-copy IPC  ·  Hardware timer  ·  Bootstrapping           │
 └───────────────────────────────────────────────────────────────┘
```

*Figure 2.1 — Quanta OS layered architecture*

Each layer is described in detail in the sections that follow.

### 2.1 Microkernel Design Philosophy

The microkernel — inspired by the L4 family [Liedtke, 1995] and,
more recently, by seL4 [Klein et al., 2009] — implements only those
primitives that cannot safely reside in user space:

 - **Address-space management:** The kernel manages page tables and
   TLB coherency, but delegates all page-fault handling to user-space
   pager tasks.
 - **IPC:** Synchronous, zero-copy message-passing between protection
   domains, with a maximum payload of 4096 bytes.
 - **Interrupt dispatch:** Kernel-provided IRQ handlers forward
   hardware interrupts (e.g., ADC-ready, DMA-complete) to user-space
   driver tasks.
 - **Timer:** A single-shot hardware timer with 1 μs resolution,
   usable for pulse scheduling and watchdog tasks.

All other functionality — device drivers, file systems, network stacks,
and, indeed, the quantum compilation pipeline — runs as user-space
servers. This design minimises the trusted computing base (TCB).

### 2.2 Formal Verification Considerations

Whilst a full seL4-style formal verification of Quanta OS is not
currently within scope, we have adopted several verification-friendly
practices:

 - **Typed assembly:** The kernel is written in a restricted subset of C
   which can, in principle, be translated to Coq or Isabelle/HOL.
 - **Well-defined invariants:** Every kernel object (capability, thread,
   memory region) has a documented invariant that is asserted at
   compile time and, optionally, at run time.
 - **Absence of undefined behaviour:** The kernel codebase is compiled
   with `-Wall -Wextra -Wpedantic -Werror` under GCC 14 and passes the
   CompCert verified compiler without warnings.

---

## 3. The Hardware Abstraction Layer (HAL)

The HAL provides a uniform interface to quantum processing units
irrespective of their underlying physical implementation.

### 3.1 Supported Backend Types

The HAL currently supports seven backends, summarised in Table 3.1.

| ID | Modality         | Representative Hardware       | Native Gates        | T₂ (typical) |
|----|------------------|-------------------------------|---------------------|--------------|
| 1  | Superconducting  | Origin悟空 180, IBM Heron     | CX, CZ, single-qubit| 30–100 μs    |
| 2  | Trapped Ion      | Quantinuum H2, IonQ Forte     | MS, single-qubit    | 0.5–5 s      |
| 3  | Photonic         | Xanadu Borealis, PsiQuantum   | BS, PS, Squeezing   | N/A (flight) |
| 4  | Neutral Atom     | QuEra Aquila, Pasqal Fresnel  | CZ, Rydberg block   | 1–10 s       |
| 5  | Silicon Spin     | Intel Tunnel Falls, Diraq     | CX, single-qubit    | 0.1–1 ms     |
| 6  | NV Centre        | Quantum Brilliance, 国仪量子  | single-qubit, CZ    | 0.5–10 ms    |
| 7  | Topological      | Microsoft Station Q           | Braiding, Clifford  | Theoretical  |

*Table 3.1 — Supported backend modalities*

### 3.2 Backend Registration Protocol

Backend instances are discovered at boot time by the
`backend_selector` component, which probes:

 1. **PCIe vendor/device IDs** for FPGA-attached QPUs (e.g., Keysight
    M3202A, Quantum Machines OPX1000);
 2. **USB descriptors** for benchtop control electronics (e.g.,
    Zurich Instruments UHFLI);
 3. **Network mDNS announcements** from remote QPU servers (e.g.,
    Origin Quantum cloud endpoints).

Once discovered, the backend registers itself with the scheduler and
calibration subsystems. The registration handshake is specified in
document QOS-HAL-002.

---

## 4. Compilation Pipeline

The compilation pipeline transforms a user-supplied quantum circuit
from OpenQASM 3.0 into a sequence of backend-native pulses. The
pipeline comprises four passes:

### 4.1 Gate Decomposition

Arbitrary unitary operations are decomposed into the backend's native
gate set using a combination of:

 - The KAK decomposition [Smith et al., 2008] for two-qubit unitaries,
   which achieves the minimal CNOT count of three;
 - The Solovay–Kitaev algorithm [Dawson & Nielsen, 2006] for
   single-qubit gates, yielding sequences with length
   O(log^{3.97}(1/ε)).

### 4.2 Topology-Aware Optimisation

Where possible, the compiler applies peephole optimisations that
exploit the backend's specific coupling topology:

 - Cancellation of adjacent inverse gates (HH = I, XX = I, etc.);
 - Commutation of single-qubit gates past two-qubit gates where the
   latter act on disjoint qubit indices;
 - SWAP insertion (or, where the backend supports it, bridge gates).

### 4.3 Qubit Routing (SABRE)

Qubit routing is performed using the SABRE algorithm [Li et al., 2019,
DAC '19], which iteratively reorders SWAP gates to minimise the number
of additional routing operations whilst respecting the hardware
coupling graph.

### 4.4 Pulse Scheduling

After routing, the circuit is scheduled onto the backend's timing
grid. The scheduler respects:

 - Gate latency (measured per gate type from calibration data);
 - Qubit coherence limits (T₁ and T₂*);
 - Readout resonator ring-down times.

---

## 5. Calibration Subsystem

The calibration subsystem — documented in full in the
`kalibrierung_protokoll.py` module — performs routine characterisation
of each qubit's coherence properties.

### 5.1 Measurement Protocols

Three standard protocols are provided:

 1. **T₁ (Inversion Recovery):** Measures longitudinal relaxation by
    fitting an exponential decay P₀(τ) = 1 - A·exp(-τ/T₁).
 2. **T₂* (Ramsey Interferometry):** Measures dephasing by fitting
    a damped cosine oscillation.
 3. **Randomized Benchmarking:** Measures average gate fidelity by
    extrapolating the Clifford decay curve [Magesan et al., 2011].

### 5.2 Drift Correction

Between successive calibrations, the system applies a Kalman filter
[Kalman, 1960, Trans. ASME] whose state vector comprises the qubit's
resonance frequency, T₁, and T₂*. The filter converges within 10 to
15 measurement epochs under typical noise conditions.

---

## 6. Scheduling Policies

The resource scheduler implements three policies, selectable at run
time:

| Policy                  | Description                                           | Best For                     |
|-------------------------|-------------------------------------------------------|------------------------------|
| FIFO                    | Jobs are processed in order of arrival.               | Quick, best-effort runs      |
| Priority                | Higher-priority jobs pre-empt lower-priority ones.    | Multi-user cloud platforms   |
| Compatibility Packing  | Jobs are co-located on the same QPU if their circuits have overlapping gate sets and complementary qubit counts. | Maximising throughput in data-centre deployments |

*Table 6.1 — Scheduling policies*

The Compatibility Packing policy is inspired by the QOS system
[Giortamis et al., OSDI '25], which demonstrated a 2.6× improvement in
throughput with a fidelity penalty of less than 3 %.

---

## 7. Conclusion and Open Questions

Quanta OS represents a ground-up re-imagining of what a quantum
operating system ought to be: neither a cloud scheduler repackaged,
nor a monolithic control stack, but a genuinely minimal microkernel
with clean interfaces for compilation, calibration, and scheduling.

A number of open questions remain, and we invite contributions and
discussion on the following topics:

 - **Verification:** How might a full seL4-style proof of correctness
   be scoped for the microkernel component?
 - **Multi-tenancy:** What resource-isolation guarantees can be offered
   to mutually distrusting users sharing a single QPU?
 - **Classical feedback:** How should measurement-based conditional
   branch instructions be represented in the scheduler's job model?

---

## References

 1. Dawson, C. M. & Nielsen, M. A. (2006). "The Solovay–Kitaev
    Algorithm." *Quantum Information & Computation*, 6(1), 81–95.
 2. Giortamis, E. et al. (2025). "QOS: A Quantum Operating System."
    *USENIX OSDI '25*.
 3. Kalman, R. E. (1960). "A New Approach to Linear Filtering and
    Prediction Problems." *Trans. ASME—J. Basic Engineering*, 82, 35–45.
 4. Klein, G. et al. (2009). "seL4: Formal Verification of an OS
    Kernel." *ACM SOSP '09*.
 5. Li, G. et al. (2019). "Tackling the Qubit Mapping Problem for
    NISQ-Era Quantum Devices." *ACM DAC '19*.
 6. Liedtke, J. (1995). "On μ-Kernel Construction." *ACM SOSP '95*.
 7. Magesan, E. et al. (2011). "Randomized Benchmarking of Quantum
    Gates." *Phys. Rev. Lett.*, 106, 180504.
 8. Nielsen, M. A. & Chuang, I. L. (2010). *Quantum Computation and
    Quantum Information* (10th Anniversary Ed.). CUP.
 9. Smith, R. et al. (2008). "Optimal Two-Qubit Compilation."
    *arXiv:0806.3241*.
