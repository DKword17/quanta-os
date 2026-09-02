# Research Report 01: Quantum OS Architecture & Existing Projects

> **Task**: Survey of quantum operating system architectures, open-source quantum computing frameworks, self-evolving compilation systems, and fault-tolerant quantum error correction approaches.
> **Date**: 2026-07-26
> **Scope**: 15+ projects/papers collected with architecture analysis

---

## Table of Contents

1. [Quantum Operating Systems](#1-quantum-operating-systems)
2. [Major Quantum Computing Frameworks](#2-major-quantum-computing-frameworks)
3. [Self-Evolving / Adaptive Quantum Compilation](#3-self-evolving--adaptive-quantum-compilation)
4. [Fault-Tolerant Quantum Computing & Error Correction](#4-fault-tolerant-quantum-computing--error-correction)
5. [Hybrid Classical-Quantum Runtime Systems](#5-hybrid-classical-quantum-runtime-systems)
6. [Comparative Summary Table](#6-comparative-summary-table)

---

## 1. Quantum Operating Systems

### 1.1 QOS — Quantum Operating System (TUM / OSDI '25)

| Field | Detail |
|-------|--------|
| **Link** | [arXiv:2406.19120](https://arxiv.org/abs/2406.19120) / [GitHub: manosgior/QOS](https://github.com/manosgior/QOS) |
| **License** | Open source (no explicit license in repo) |
| **Authors** | Emmanouil Giortamis, Francisco Romão, Nathaniel Tornow, Pramod Bhatotia (TUM) |
| **Venue** | USENIX OSDI 2025 |

**Core Architecture Ideas:**
- Cloud operating system for managing quantum resources across hardware providers
- Hardware-agnostic API for transparent quantum job execution (abstracts IBM, IonQ, etc.)
- **Multi-programming scheduler** that co-locates compatible quantum jobs on the same QPU in space and time
- **Fidelity-utilization tradeoff engine**: systematically balances quantum fidelity vs. resource utilization
- Key insight: some jobs are more compatible than others for multi-programming; sacrificing minimal fidelity (1–3%) can dramatically reduce waiting times

**Hardware Abstraction:**
- Hardware-agnostic job submission API
- Abstract quantum resource model that hides physical topology differences
- Backend adapters for real IBM quantum devices

**Self-Evolution / Adaptation:**
- Scheduler learns job compatibility patterns from runtime metrics
- Adaptive multi-programming that tunes fidelity-utilization tradeoff dynamically

**Key Results (from paper):**
- 2.6–456.5× higher fidelity than baselines
- Up to 9.6× resource utilization improvement
- 5× reduction in waiting times
- Evaluated on 7000+ real quantum runs (70K+ benchmark instances) on IBM hardware

---

### 1.2 BAQIS Quantum Operating System (Beijing Academy of Quantum Information Sciences)

| Field | Detail |
|-------|--------|
| **Link** | [GitHub: BAQIS-Quantum/Qcover](https://github.com/BAQIS-Quantum/Qcover) |
| **License** | Apache 2.0 |

**Core Architecture Ideas:**
- Quantum OS team at BAQIS developing a full quantum computing software stack
- Focus on NISQ-era combinatorial optimization via QAOA
- Provides fast optimal parameter output for shallow QAOA circuits
- Integrates quantum processor control with classical optimization

**Hardware Abstraction:**
- QAOA-specific hardware abstraction layer
- Support for various NISQ processors

**Self-Evolution / Adaptation:**
- Parameter optimization for QAOA circuits; not fully self-evolving but has tuning capabilities

---

### 1.3 quantum-os-org / quantum-os

| Field | Detail |
|-------|--------|
| **Link** | [GitHub: quantumos-org/quantum-os](https://github.com/quantumos-org/quantum-os) |
| **License** | GPL (Linux-based) |

**Core Architecture Ideas:**
- A Linux-kernel-based operating system "made for quantum computers"
- Massive project (1M+ commits, mirrors Linux kernel)
- Appears to be a fork/extension of Linux with quantum computing support
- Includes arch, drivers, kernel, IPC, etc. as standard OS subsystems

**Note:** This project's scope and actual quantum-specific modifications need deeper investigation. It appears to be more of a classical OS adaptation for quantum environments rather than a pure quantum OS.

---

## 2. Major Quantum Computing Frameworks

### 2.1 Qiskit (IBM)

| Field | Detail |
|-------|--------|
| **Link** | [GitHub: Qiskit/qiskit](https://github.com/Qiskit/qiskit) |
| **License** | Apache 2.0 |

**Core Architecture Ideas:**
- SDK for working with quantum computers at the level of extended quantum circuits, operators, and primitives
- **Four-layer architecture**: Build → Compile (transpile) → Run → Analyze
- **Transpiler**: compiles high-level circuits to hardware-native gates with optimization passes (routing, gate decomposition, commutation)
- **Abstraction layer**: vendor-agnostic backend interface allowing circuits to run on any provider's hardware (IBM, IonQ, rigetti, etc.)
- **Qiskit Runtime**: classical-quantum hybrid execution environment for iterative algorithms (VQE, QAOA)
- **Primitives**: Estimator and Sampler as high-level execution abstractions
- **OpenQASM 3.0** as circuit intermediate representation

**Hardware Abstraction:**
- `Backend` interface abstracting all hardware properties (coupling map, basis gates, noise model)
- `Target` object describing a specific device's capabilities
- Transpiler maps logical circuits to physical qubits using device topology
- Backend providers: IBM Q, Aer simulator, and third-party adapters

**Self-Evolution / Adaptation:**
- Optimization levels (0–3) in transpiler provide adaptive compilation quality
- Pulse-level control allows calibration-aware optimization
- Qiskit Runtime Sessions enable adaptive classical-quantum feedback loops
- Error mitigation techniques (readout error mitigation, zero-noise extrapolation)

---

### 2.2 Cirq (Google)

| Field | Detail |
|-------|--------|
| **Link** | [GitHub: quantumlib/Cirq](https://github.com/quantumlib/Cirq) |
| **License** | Apache 2.0 |

**Core Architecture Ideas:**
- Framework for creating, editing, and invoking NISQ circuits
- Python-first design with a focus on making quantum programming natural
- **Device-aware compilation**: Cirq circuits are defined with device constraints in mind
- **Moments** concept: time slices of operations that can execute in parallel
- **Schedulers** map abstract circuits to device timing constraints
- Integration with TensorFlow Quantum for hybrid ML workflows

**Hardware Abstraction:**
- `Device` class encapsulates all physical constraints (qubit grid, gate set, noise)
- `Sampler` interface abstracts execution on simulators or hardware
- Native support for Google's Sycamore processor topology
- Qubit placement and routing optimized for 2D grid architectures

**Self-Evolution / Adaptation:**
- Google's quantum AI team uses Cirq for adaptive calibration of Sycamore
- Cross-entropy benchmarking for real-time fidelity estimation
- Integration with TFQ enables gradient-based circuit parameter optimization

---

### 2.3 PennyLane (Xanadu)

| Field | Detail |
|-------|--------|
| **Link** | [GitHub: XanaduAI/pennylane](https://github.com/XanaduAI/pennylane) |
| **License** | Apache 2.0 |

**Core Architecture Ideas:**
- Cross-platform Python library for quantum machine learning, automatic differentiation, and optimization
- **QNode abstraction**: quantum circuits as differentiable nodes in computational graphs
- **Hybrid quantum-classical** computation: seamlessly blends classical ML (PyTorch, TensorFlow, JAX) with quantum circuits
- **Plugin architecture**: modular device interface supports Qiskit, Cirq, Strawberry Fields, Braket, and more
- **Automatic differentiation** of quantum circuits via parameter-shift rules

**Hardware Abstraction:**
- `Device` plugin system: standard interface for simulators and real hardware
- Currently supports 20+ backends via plugin ecosystem
- `default.qubit` simulator, `lightning.qubit` GPU-accelerated simulator
- Works with Xanadu's photonic hardware (X8, X16)

**Self-Evolution / Adaptation:**
- Gradient-based circuit optimization enables adaptive parameter tuning
- Integration with NVIDIA cuQuantum for GPU-accelerated simulation
- Support for variational quantum algorithms that evolve circuit parameters during training
- Adjoint differentiation for efficient gradient computation

---

### 2.4 ProjectQ

| Field | Detail |
|-------|--------|
| **Link** | [GitHub: ProjectQ-Framework/ProjectQ](https://github.com/ProjectQ-Framework/ProjectQ) |
| **License** | Apache 2.0 |

**Core Architecture Ideas:**
- Open-source compilation framework with a **high-performance simulator** with emulation capabilities
- **Compiler engine pipeline**: modular compilation via chained engines
- `MainEngine` orchestrates compilation and execution
- Each engine performs a specific transformation (optimization, mapping, gate decomposition)
- **Setup** system provides pre-configured engine stacks for different hardware targets
- Hardware-agnostic high-level quantum operations → device-native gates

**Hardware Abstraction:**
- Backend engines for IBM Q, AQT, AWS Braket, Azure Quantum, and local simulators
- `BasicEngine` base class for all compilation/backend components
- Circuit drawing, gate counting, and resource estimation backends

**Self-Evolution / Adaptation:**
- Plugin architecture allows custom compiler passes
- Compilation engine stack can be reconfigured per target
- Emulation mode for debugging large circuits

---

### 2.5 QuEST (Quantum Exact Simulation Toolkit)

| Field | Detail |
|-------|--------|
| **Link** | [GitHub: QuEST-Kit/QuEST](https://github.com/QuEST-Kit/QuEST) |
| **License** | MIT |

**Core Architecture Ideas:**
- High-performance simulator of universal quantum circuits, state-vectors and density matrices
- Written in C with **hybrid parallelization**: OpenMP (multithreading) + MPI (distributed) + GPU (CUDA)
- Designed for laptops to supercomputers
- **Environment-agnostic interface**: same API works across CPU, GPU, and network backends
- Fully deterministic numerical simulation

**Hardware Abstraction:**
- `Qureg` (quantum register) abstraction for state representation
- `QuESTEnv` manages the runtime environment (CPU/GPU/distributed)
- Compile-time selection of multithreading and GPU acceleration
- Simple C API agnostic to underlying parallelization strategy

**Self-Evolution / Adaptation:**
- No self-evolving capability — it's a classical simulator
- Deterministic, purely numerical

---

### 2.6 tket (Quantinuum / Cambridge Quantum)

| Field | Detail |
|-------|--------|
| **Link** | [GitHub: CQCL/tket](https://github.com/CQCL/tket) |
| **License** | Apache 2.0 |

**Core Architecture Ideas:**
- **C++ quantum compiler framework** with Python bindings (pytket)
- Industry-leading **circuit optimizer** and qubit allocation system
- **Transform** system: composable optimization passes with consistent interface
- Unique **Transform Combinator** allows users to design custom compilation pipelines
- **Routing** algorithms that minimize SWAP overhead
- **Architecture-aware** compilation for any target device

**Hardware Abstraction:**
- `Backend` interface: generic API for hardware/simulator interaction
- pytket-extensions system for specific hardware backends (IBM, Rigetti, IonQ, Honeywell, etc.)
- Device characterization data drives optimization decisions

**Self-Evolution / Adaptation:**
- Optimized rerouting capabilities for NISQ-era hardware
- Customizable pass pipelines allow adaptive compilation strategies
- Device-aware optimization that adapts to connectivity constraints

---

### 2.7 Strawberry Fields (Xanadu)

| Field | Detail |
|-------|--------|
| **Link** | [GitHub: XanaduAI/strawberryfields](https://github.com/XanaduAI/strawberryfields) |
| **License** | Apache 2.0 |

**Core Architecture Ideas:**
- Full-stack Python library for **continuous-variable (CV) photonic quantum computing**
- End-to-end differentiable TensorFlow backend for training quantum programs
- World-class simulators based on cutting-edge algorithms for photonic circuits
- High-level functions for graph/network optimization, ML, and chemistry
- Direct execution on Xanadu's photonic quantum hardware

**Hardware Abstraction:**
- Multiple simulator backends: `gaussian`, `fock`, `tf` (TensorFlow)
- Hardware backend for Xanadu's photonic QPUs
- Plugin integration with PennyLane

**Self-Evolution / Adaptation:**
- Differentiable programming enables parameter optimization
- TensorFlow integration for gradient-based circuit learning

---

### 2.8 Amazon Braket SDK

| Field | Detail |
|-------|--------|
| **Link** | [AWS Braket](https://aws.amazon.com/braket/) |
| **License** | Apache 2.0 (SDK) |

**Core Architecture Ideas:**
- Fully managed AWS service for quantum algorithm development
- **Unified development environment** across multiple quantum hardware technologies: Rigetti (superconducting), IonQ (trapped ion), D-Wave (quantum annealing), QuEra (neutral atom)
- **Hybrid quantum-classical** algorithm support with managed Jupyter notebooks
- **Local simulator** + fully managed simulators with/without noise models
- **Braket Direct**: dedicated device access with specialists

**Hardware Abstraction:**
- `QuantumDevice` abstraction across annealing and gate-based systems
- `Device` class with properties, operations, and availability
- Consistent SDK interface regardless of underlying technology
- Priority queue for dedicated device access

---

### 2.9 NVIDIA CUDA-Q

| Field | Detail |
|-------|--------|
| **Link** | [NVIDIA CUDA-Q](https://developer.nvidia.com/cuda-q) / [GitHub: NVIDIA/cuda-quantum](https://github.com/NVIDIA/cuda-quantum) |
| **License** | Open source |

**Core Architecture Ideas:**
- Programming model for **quantum-accelerated supercomputing**
- Leverages CPU, GPU, and QPU in a unified programming model
- **GPU-accelerated quantum circuit simulation** at unprecedented scale
- **NVQLink**: high-speed GPU-QPU interconnect (open universal interconnect)
- Integration with classical HPC workflows
- cuQuantum SDK for accelerating quantum simulators on NVIDIA GPUs

**Hardware Abstraction:**
- Backend-agnostic kernel programming model
- Supports multiple QPU types through the same programming interface
- GPU-simulated backend for development and HPC-backed simulation
- Multi-node distributed quantum simulation

**Self-Evolution / Adaptation:**
- GPU-accelerated variational algorithm optimization
- Integration with AI for quantum-classical hybrid workflows

---

### 2.10 XACC (Extreme-scale ACCeleration)

| Field | Detail |
|-------|--------|
| **Link** | [XACC Documentation](https://xacc.readthedocs.io/) / [GitHub: eclipse/xacc](https://github.com/eclipse/xacc) |
| **License** | Eclipse Public License |

**Core Architecture Ideas:**
- Extreme-scale programming model for **quantum acceleration within HPC**
- **Co-processor model** inspired by OpenCL/CUDA: classical application offloads quantum kernels to QPU accelerators
- **Heterogeneous computing** with multiple QPU types (gate-model, annealing)
- High-level API for classical programs to interact with quantum accelerators
- Eclipse project with formal governance

**Hardware Abstraction:**
- `Accelerator` interface abstracting all QPU types
- `IR` (Intermediate Representation) for quantum circuits
- `Compiler` pipeline for target-specific optimization
- Service-oriented architecture via `xacc::service` registry

**Self-Evolution / Adaptation:**
- Compiler plugin system allows optimization pass customization
- Flexible IR supports multiple quantum programming languages

---

## 3. Self-Evolving / Adaptive Quantum Compilation

### 3.1 Variational Quantum Compiler with RL (Reinforcement Learning)

| Field | Detail |
|-------|--------|
| **Link** | [arXiv:2109.03188](https://arxiv.org/abs/2109.03188) |
| **Year** | 2021 |

**Core Architecture Ideas:**
- Uses **deep reinforcement learning** to augment gradient-based optimization of variational quantum circuits
- RL agent learns optimal optimization trajectories through interaction with noisy quantum hardware
- Significantly outperforms gradient descent in noisy environments
- Demonstrates self-adaptive optimization in NISQ conditions

**Key Insight:**
- RL-augmented optimizers consistently beat vanilla gradient descent when noise is present
- Circuit parameters autonomously adapt based on hardware feedback

---

### 3.2 Quartz — Quantum Compiler with Super-Optimization

| Field | Detail |
|-------|--------|
| **Link** | [GitHub: quantum-compiler/quartz](https://github.com/quantum-compiler/quartz) |
| **License** | MIT |

**Core Architecture Ideas:**
- Quantum circuit **super-optimizer** that explores exhaustive gate-level transformations
- Symbolic parameter support in OpenQASM 3.0
- Circuit verifier for equivalence checking of transformations
- Generator-based exploration of circuit optimization space

**Self-Evolution:**
- Each transformation step can be stored and verified
- Symbolic parameter optimization adapts to runtime conditions
- Can discover novel circuit optimizations automatically

---

### 3.3 Self-Learning Quantum Technologies (LSU Research)

| Field | Detail |
|-------|--------|
| **Link** | [ScitechDaily Article](https://scitechdaily.com/self-learning-self-evolving-smart-quantum-technologies-for-secure-communication/) |
| **Year** | 2021 |

**Core Concepts:**
- Self-learning, self-evolving smart quantum technology for correcting distorted spatial modes of light at the single-photon level
- ML-powered adaptive correction of quantum optical states
- Applicable to quantum communication and quantum sensing
- Demonstrates the concept of **autonomous quantum system optimization**

---

### 3.4 IBM Quantum Error Correction & Adaptive Calibration

| Field | Detail |
|-------|--------|
| **Link** | [IBM Research: QEC](https://research.ibm.com/topics/quantum-error-correction) |

**Core Architecture Ideas:**
- IBM's roadmap to **scalable, error-corrected quantum systems**
- Bottom-up approach: improve physical gates → reduce errors → implement QEC
- **Adaptive calibration**: ML-driven real-time qubit tuning
- **Quantum-centric supercomputing** reference architecture (hybrid classical-quantum)
- Sample-based Quantum Diagonalization (SQD) for practical applications

**Self-Evolution:**
- Calibration adapted based on device drift measurements
- Error mitigation techniques evolve with hardware feedback
- Quantum Runtime enables adaptive circuit execution

---

## 4. Fault-Tolerant Quantum Computing & Error Correction

### 4.1 Micro Blossom — Hardware Accelerated MWPM Decoder

| Field | Detail |
|-------|--------|
| **Link** | [GitHub: yale-paragon/micro-blossom](https://github.com/yale-paragon/micro-blossom) |
| **License** | Open source |

**Core Architecture Ideas:**
- **Hardware-accelerated Minimum-Weight Perfect Matching (MWPM)** decoder for surface code QEC
- Heterogeneous architecture solving exact MWPM in **sub-microsecond latency**
- Vertex and edge-level fine-grained hardware acceleration
- Automatic hardware generation (Verilog/VHDL) from high-level specification
- Based on Fusion Blossom algorithm

**Key Microarchitecture Features:**
- Sub-microsecond decoding latency (real-time QEC)
- FPGA/ASIC implementation
- Exact (not approximate) MWPM solving
- Fully pipelined hardware design

**Self-Evolution:**
- Configurable architecture generation
- Parameters can be tuned per device error profile

---

### 4.2 EdenCode — AI-Powered Real-Time Decoder

| Field | Detail |
|-------|--------|
| **Link** | [The Quantum Insider](https://thequantuminsider.com/2026/01/24/edencode-emerges-from-stealth-with-real-time-ai-decoder-for-quantum-error-correction/) |
| **Year** | 2026 |

**Core Architecture Ideas:**
- AI-powered real-time decoder for quantum error correction
- Reduces latency and improves accuracy for fault-tolerant computing
- ML-based decoding that adapts to device-specific noise characteristics
- Commercial product targeting the fault-tolerant era

**Self-Evolution:**
- Neural network decoder continuously adapts to changing noise profiles
- Learns device-specific error correlations

---

### 4.3 Real-Time Fault-Tolerant QEC (Honeywell/Quantinuum)

| Field | Detail |
|-------|--------|
| **Link** | [arXiv:2107.07505](https://arxiv.org/pdf/2107.07505.pdf) |
| **Year** | 2021 |

**Core Architecture Ideas:**
- First realization of **real-time fault-tolerant quantum error correction** on trapped-ion hardware
- Low-level primitives: single/two-qubit ops, mid-circuit measurement, real-time measurement processing, conditional gates
- Three mutually unbiased bases encoding
- **Average logical SPAM error**: 1.7(2)×10⁻³ (vs physical SPAM 2.4(8)×10⁻³)
- Successful real-time feedback loop for error correction

**Architecture Requirements:**
- Mid-circuit measurements without disturbing adjacent qubits
- Classical FPGA-based real-time decoders
- Conditional gate execution based on syndrome measurements

---

### 4.4 Fusion Blossom Algorithm for Surface Code

| Field | Detail |
|-------|--------|
| **Link** | [GitHub: yale-paragon/fusion-blossom](https://github.com/yale-paragon/fusion-blossom) |
| **Year** | 2022+ |

**Core Architecture Ideas:**
- Novel MWPM algorithm optimized for surface code decoding
- **Fusion-based** approach: incrementally merges matching components
- Significantly faster than traditional Blossom V implementation
- Enables real-time decoding for large distance surface codes
- Used as foundation for the Micro Blossom hardware decoder

**Architecture Features:**
- O(n log n) complexity for surface code decoding
- Support for weighted edges and arbitrary lattice geometries
- Python/C hybrid for performance

---

### 4.5 IBM Heavy Hex Surface Code Architecture

| Field | Detail |
|-------|--------|
| **Link** | [IBM Blog: Future of QEC](https://www.ibm.com/quantum/blog/future-quantum-error-correction) |

**Core Architecture Ideas:**
- IBM's **heavy-hex** qubit topology designed for surface code implementation
- Efficient mapping of surface code to heavy-hex lattice
- T-shaped routing reduces crosstalk and enables better QEC
- **Bottom-up approach**: improving physical qubit fidelity first
- Demonstrated logical memory with error suppression

**Architecture Features:**
- Hardware topology optimized for QEC
- Scalable roadmap to 1000+ logical qubits
- Integration with Qiskit Runtime for QEC circuits

---

## 5. Hybrid Classical-Quantum Runtime Systems

### 5.1 Quantum Machines Open Acceleration Stack

| Field | Detail |
|-------|--------|
| **Link** | [Quantum Machines](https://www.quantum-machines.co/) / [News Article](https://so.html5.qq.com/page/real/search_news?docid=70000021_40269c23f5645052) |
| **Year** | 2026 |

**Core Architecture Ideas:**
- **First open acceleration stack** integrating classical XPU with quantum control
- **OPX network interface card (OPNIC)** + NVIDIA NVQLink technology
- **Pulse Processing Unit (PPU)**: classical architecture quantum controller
- **Microsecond-level low-latency** connection between GPU/CPU/FPGA/ASIC and QPU
- Native support for quantum error correction and AI workloads

**Architecture Features:**
- GPU-accelerated quantum-classical feedback loops
- FPGA-based real-time pulse generation and measurement
- Classical-quantum co-processing at microsecond scale

---

### 5.2 IBM Quantum-Centric Supercomputing Reference Architecture

| Field | Detail |
|-------|--------|
| **Link** | [IBM Research Blog](https://research.ibm.com/blog/quantum-centric-supercomputing-system-reference-architecture) |
| **Year** | 2026 |

**Core Architecture Ideas:**
- **First reference architecture** for quantum-centric supercomputing (QCSC)
- Hybrid classical-quantum workflow integration
- SQD (Sample-based Quantum Diagonalization) algorithm demonstrated on 300-atom protein simulation
- **Scaling**: quantum simulations up to 33 orbitals, 919-orbital classical preprocessing
- Comparable results to CCSD (coupled cluster) methods

**Architecture Components:**
- Classical HPC + QPU co-processing
- Quantum Runtime for job scheduling and management
- Error mitigation integrated into all layers

---

### 5.3 Intel Quantum SDK / Hybrid Programming

| Field | Detail |
|-------|--------|
| **Link** | [Intel HPDC 2023](https://www.intel.cn/content/www/cn/zh/developer/community/event/hpdc-2023.html) |

**Core Architecture Ideas:**
- **C-based quantum extension** for hybrid classical-quantum programming
- Compiler and runtime system for integrating quantum operations in classical C programs
- Focus on spin qubit architecture (Intel's qubit technology)
- Simulator + real hardware path

---

## 6. Comparative Summary Table

| # | Project/Paper | Category | HAL | Self-Evolution | License | Key Innovation |
|---|---|---|---|---|---|---|
| 1 | **QOS** | Quantum OS | ✓ Hardware-agnostic API | ✓ Adaptive multi-programming scheduler | Open (GitHub) | Fidelity-utilization tradeoff for multi-programming |
| 2 | **BAQIS Qcover** | Quantum OS | ✓ NISQ processor abstraction | ✓ QAOA parameter optimization | Apache 2.0 | Combinatorial optimization on NISQ |
| 3 | **Qiskit** | Framework | ✓ Vendor-agnostic Backend | ✓ Optimization levels + error mitigation | Apache 2.0 | Four-stage Build→Compile→Run→Analyze |
| 4 | **Cirq** | Framework | ✓ Device-aware Device class | ✓ Calibration-aware compilation | Apache 2.0 | Moments-based circuit scheduling |
| 5 | **PennyLane** | Framework | ✓ Plugin-based Device system | ✓ Gradient-based circuit optimization | Apache 2.0 | Differentiable quantum computing |
| 6 | **ProjectQ** | Framework | ✓ Engine pipeline abstraction | ✓ Compile-time optimization passes | Apache 2.0 | Modular engine architecture |
| 7 | **QuEST** | Simulator | ✓ Environment-agnostic API | ✗ (deterministic) | MIT | Multi-platform HPC simulation |
| 8 | **tket** | Compiler | ✓ Generic Backend interface | ✓ Customizable pass pipelines | Apache 2.0 | Transform combinator / qubit allocation |
| 9 | **Strawberry Fields** | Framework | ✓ CV photonic backends | ✓ Differentiable TF backend | Apache 2.0 | Photonic CV quantum computing |
| 10 | **Amazon Braket** | Cloud Service | ✓ Multi-technology Device | ✗ (platform-level) | Apache 2.0 | Multi-vendor hardware access |
| 11 | **NVIDIA CUDA-Q** | Platform | ✓ GPU+QPU kernel model | ✓ GPU-accelerated optimization | Open | NVQLink quantum-classical interconnect |
| 12 | **XACC** | Framework | ✓ Co-processor Accelerator | ✓ Plugin compiler system | EPL | HPC quantum co-processor model |
| 13 | **RL Variational Compiler** | Compiler/RL | ✓ Noise-aware optimization | ✓ Self-adaptive RL agent | — | RL-enhanced VQC optimization |
| 14 | **Quartz** | Compiler | ✓ Super-optimization | ✓ Automatic circuit generation | MIT | Gate-level circuit super-optimization |
| 15 | **Micro Blossom** | QEC Hardware | ✓ Hardware-generated decoder | ✓ Configurable per error model | Open | Sub-μs MWPM on FPGA/ASIC |
| 16 | **EdenCode** | QEC Decoder | ✓ AI decoder | ✓ Adaptive neural decoder | Commercial | AI-powered real-time QEC |
| 17 | **Quantinuum RT-QEC** | QEC System | ✓ Real-time feedback | ✓ Syndrome-based adaptation | — | First real-time fault-tolerant QEC demo |
| 18 | **Fusion Blossom** | QEC Algorithm | ✓ Topology-agnostic | ✗ (algorithmic only) | Open | Fast surface code MWPM |
| 19 | **Quantum Machines Stack** | Runtime | ✓ Open accelerator stack | ✓ Classical-quantum feedback | Open | μs-latency QPU/GPU interconnect |
| 20 | **IBM QCSC Architecture** | Reference Arch | ✓ Hybrid workflow | ✓ Integrated error mitigation | — | Quantum-centric supercomputing blueprint |

---

## Key Takeaways for Quanta-OS Design

### Architectural Patterns Observed:

1. **Hardware Abstraction Layer (HAL)** is universal — every system defines a device abstraction that isolates user code from physical QPU specifics.

2. **Modular Compiler Pipelines** dominate — systems like tket, ProjectQ, and Qiskit all use composable optimization passes (transforms, engines, transpiler stages).

3. **Multi-Programming / Scheduler** is a critical OS function — QOS demonstrates that intelligent job scheduling across space-time on QPUs is a core OS service, achieving 9.6× utilization gains.

4. **Classical-Quantum Hybrid Runtime** is essential — Qiskit Runtime, CUDA-Q, Braket, and Quantum Machines stack all emphasize tight integration between classical CPUs/GPUs and QPUs.

5. **Self-Evolution Gap**: No existing system has a truly autonomous self-evolving compilation loop. Current "adaptation" is limited to:
   - Pre-defined optimization levels (Qiskit)
   - Gradient-based parameter tuning (PennyLane)
   - RL-augmented optimization (RL Compiler)
   - Customizable compiler passes (tket, ProjectQ)
   → **This is a major design opportunity for Quanta-OS.**

6. **Real-Time QEC requires hardware acceleration** — Micro Blossom and EdenCode both use dedicated hardware (FPGA/ASIC/AI) for sub-microsecond decoding latency.

7. **No pure "Quantum OS" exists** — QOS comes closest but focuses on cloud job management. There is no system that manages quantum memory, I/O, process isolation, and device drivers in the sense of a classical OS microkernel.

### Recommended Focus Areas for Quanta-OS:

- **Self-evolving compilation**: Learn from RL-enhanced compilers and super-optimizers
- **Microkernel architecture**: None of the existing projects uses a microkernel design; this is a unique position
- **Hardware abstraction with self-calibration**: Adaptive HAL that evolves with device drift
- **Real-time QEC as a kernel service**: Micro Blossom-style hardware decoders as OS components
- **Quantum-classical co-scheduler**: Extend QOS's multi-programming with fidelity-aware scheduling

---

*End of Research Report 01*
