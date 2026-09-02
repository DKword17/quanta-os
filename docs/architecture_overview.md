# Quanta OS 鈥?Architectural Overview

**Document Reference:** QOS-ARCH-001  
**Author:** DKword17  
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
   unified hardware abstraction layer (see 搂3.2).
 - **Determinism:** Real-time pulse generation through FPGA-coupled
   kernel primitives, with worst-case interrupt latency below 1 渭s.
 - **Composability:** A protocol-agnostic middleware layer that permits
   the simultaneous operation of multiple compilation strategies,
   scheduling policies, and error-correction codes.

---

## 2. System Architecture

Quanta OS follows a layered architecture, in which each layer
communicates with its immediate neighbours through well-defined
interfaces. Figure 2.1 below illustrates the principal layers.

```
 鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹?                    User / Cloud Interface                     鈹? 鈹? (REST API, gRPC, Python SDK, CLI)                            鈹? 鈹溾攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹?              Compiler & Optimisation Middleware                鈹? 鈹? QASM parsing  鈫? Gate decomposition  鈫? Topology mapping     鈹? 鈹溾攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹?             Resource Scheduler & Job Manager                   鈹? 鈹? Priority queues  鈫? Compatibility packing  鈫? Load balancing 鈹? 鈹溾攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹?                Error Correction & Calibration                  鈹? 鈹? Surface code encoding  鈫? Kalman filtering  鈫? RB fidelity   鈹? 鈹溾攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹?                  Hardware Abstraction Layer                    鈹? 鈹?    Superconducting  路  Ion Trap  路  Photonic  路  Neutral      鈹? 鈹?    Silicon Spin  路  NV Centre  路  Topological                 鈹? 鈹溾攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹?                 Kernel (Microkernel, 鈮?64 KB)                  鈹? 鈹? Memory management  路  FPGA DMA control  路  ISR dispatching    鈹? 鈹? Zero-copy IPC  路  Hardware timer  路  Bootstrapping           鈹? 鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?```

*Figure 2.1 鈥?Quanta OS layered architecture*

Each layer is described in detail in the sections that follow.

### 2.1 Microkernel Design Philosophy

The microkernel 鈥?inspired by the L4 family [Liedtke, 1995] and,
more recently, by seL4 [Klein et al., 2009] 鈥?implements only those
primitives that cannot safely reside in user space:

 - **Address-space management:** The kernel manages page tables and
   TLB coherency, but delegates all page-fault handling to user-space
   pager tasks.
 - **IPC:** Synchronous, zero-copy message-passing between protection
   domains, with a maximum payload of 4096 bytes.
 - **Interrupt dispatch:** Kernel-provided IRQ handlers forward
   hardware interrupts (e.g., ADC-ready, DMA-complete) to user-space
   driver tasks.
 - **Timer:** A single-shot hardware timer with 1 渭s resolution,
   usable for pulse scheduling and watchdog tasks.

All other functionality 鈥?device drivers, file systems, network stacks,
and, indeed, the quantum compilation pipeline 鈥?runs as user-space
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

| ID | Modality         | Representative Hardware       | Native Gates        | T鈧?(typical) |
|----|------------------|-------------------------------|---------------------|--------------|
| 1  | Superconducting  | Origin鎮熺┖ 180, IBM Heron     | CX, CZ, single-qubit| 30鈥?00 渭s    |
| 2  | Trapped Ion      | Quantinuum H2, IonQ Forte     | MS, single-qubit    | 0.5鈥? s      |
| 3  | Photonic         | Xanadu Borealis, PsiQuantum   | BS, PS, Squeezing   | N/A (flight) |
| 4  | Neutral Atom     | QuEra Aquila, Pasqal Fresnel  | CZ, Rydberg block   | 1鈥?0 s       |
| 5  | Silicon Spin     | Intel Tunnel Falls, Diraq     | CX, single-qubit    | 0.1鈥? ms     |
| 6  | NV Centre        | Quantum Brilliance, 鍥戒华閲忓瓙  | single-qubit, CZ    | 0.5鈥?0 ms    |
| 7  | Topological      | Microsoft Station Q           | Braiding, Clifford  | Theoretical  |

*Table 3.1 鈥?Supported backend modalities*

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
 - The Solovay鈥揔itaev algorithm [Dawson & Nielsen, 2006] for
   single-qubit gates, yielding sequences with length
   O(log^{3.97}(1/蔚)).

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
 - Qubit coherence limits (T鈧?and T鈧?);
 - Readout resonator ring-down times.

---

## 5. Calibration Subsystem

The calibration subsystem 鈥?documented in full in the
`calibration_protocol.py` module 鈥?performs routine characterisation
of each qubit's coherence properties.

### 5.1 Measurement Protocols

Three standard protocols are provided:

 1. **T鈧?(Inversion Recovery):** Measures longitudinal relaxation by
    fitting an exponential decay P鈧€(蟿) = 1 - A路exp(-蟿/T鈧?.
 2. **T鈧? (Ramsey Interferometry):** Measures dephasing by fitting
    a damped cosine oscillation.
 3. **Randomized Benchmarking:** Measures average gate fidelity by
    extrapolating the Clifford decay curve [Magesan et al., 2011].

### 5.2 Drift Correction

Between successive calibrations, the system applies a Kalman filter
[Kalman, 1960, Trans. ASME] whose state vector comprises the qubit's
resonance frequency, T鈧? and T鈧?. The filter converges within 10 to
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

*Table 6.1 鈥?Scheduling policies*

The Compatibility Packing policy is inspired by the QOS system
[Giortamis et al., OSDI '25], which demonstrated a 2.6脳 improvement in
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

 1. Dawson, C. M. & Nielsen, M. A. (2006). "The Solovay鈥揔itaev
    Algorithm." *Quantum Information & Computation*, 6(1), 81鈥?5.
 2. Giortamis, E. et al. (2025). "QOS: A Quantum Operating System."
    *USENIX OSDI '25*.
 3. Kalman, R. E. (1960). "A New Approach to Linear Filtering and
    Prediction Problems." *Trans. ASME鈥擩. Basic Engineering*, 82, 35鈥?5.
 4. Klein, G. et al. (2009). "seL4: Formal Verification of an OS
    Kernel." *ACM SOSP '09*.
 5. Li, G. et al. (2019). "Tackling the Qubit Mapping Problem for
    NISQ-Era Quantum Devices." *ACM DAC '19*.
 6. Liedtke, J. (1995). "On 渭-Kernel Construction." *ACM SOSP '95*.
 7. Magesan, E. et al. (2011). "Randomized Benchmarking of Quantum
    Gates." *Phys. Rev. Lett.*, 106, 180504.
 8. Nielsen, M. A. & Chuang, I. L. (2010). *Quantum Computation and
    Quantum Information* (10th Anniversary Ed.). CUP.
 9. Smith, R. et al. (2008). "Optimal Two-Qubit Compilation."
    *arXiv:0806.3241*.
