# Dynamic and Resource-Aware SDN Network Slicing

**Project overview**

The project aims to develop an SDN-based network slicing system that enables users to dynamically create, activate and deactivate network slices while managing available network resources and bandwidth allocation.

**Main objectives**

- **Dynamic slice management (Module 2 – Engineering Programmable and Sustainable Networks):** Implement on-demand slice creation, activation and deactivation through a CLI. Define slices using configurations specifying flows, topology and allocated link capacity.
- **Bandwidth allocation (Next Generation Networks):** Implement flow-level bandwidth allocation with admission control, ensuring that requested flows do not exceed available link capacity.
- **SDN control:** Use the RYU controller to install and remove flow rules, track residual capacity and, where feasible, apply bandwidth limits using OpenFlow meters.
- **Performance evaluation:** Use `iperf` to measure throughput and compare network performance with and without bandwidth-aware admission control. Present the results using graphs.

**Implementation approach**

The system will be implemented using Python, RYU and Kathará for network emulation, subject to approval of the emulation environment. A modular architecture will separate slice management, resource allocation and SDN control.

**Expected outcome**

A working prototype demonstrating dynamic network slice management, bandwidth-aware flow allocation and measurable improvements in resource management compared with a baseline approach.
