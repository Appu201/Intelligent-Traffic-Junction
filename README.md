# Intelligent Traffic Junction Simulation

A Python and Pygame-based **3-road traffic junction simulation** featuring timed traffic signals, realistic vehicle movement, queues, and real-time traffic density monitoring.

## Overview

The simulation contains three roads:

* **Road A:** Vehicles enter from the bottom.
* **Road B:** Vehicles enter from the top.
* **Road C:** Vehicles enter from the right.

Vehicles move through the junction according to traffic signals and form queues when the signal is red.

## Features

* 3-road top-down traffic junction
* Realistic vehicle movement
* Continuous vehicle generation
* Vehicle queues and safe spacing
* RED / YELLOW / GREEN traffic signals
* Real-time signal countdown
* Road-wise vehicle counts
* Total vehicle count
* Traffic monitoring dashboard
* Start, pause, and reset controls
* Smooth ~60 FPS simulation

## Traffic Signal Sequence

Only one road is green at a time:

```text
Road A → Road B → Road C → Road A → ...
```

Each road follows:

```text
GREEN  = 30 seconds
YELLOW = 3 seconds
RED    = until its next turn
```

Vehicles stop at the stop line during red signals and move smoothly when the signal becomes green.

## Traffic Monitoring

The dashboard displays the current signal state, countdown timer, vehicle count for each road, total vehicles, and simulation time.

Vehicle-count information is maintained through Python functions, providing a foundation for future communication with external systems.

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

Run the simulation:

```bash
python main.py
```

## Controls

| Key     | Action         |
| ------- | -------------- |
| `SPACE` | Pause / Resume |
| `R`     | Reset          |

## Future Development

The current version focuses on the basic traffic simulation. Future versions will integrate:

* TCP communication
* QNX RTOS
* Raspberry Pi
* Adaptive traffic signal control
* Emergency vehicle priority
* AI/YOLO vehicle detection
* Real-time traffic data

## Technology

**Python 3 • Pygame • Object-Oriented Programming**
