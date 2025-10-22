# LabSync

A cross-platform PySide6 application that manages laboratory equipment.

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![GitHub tag (latest by date)](https://img.shields.io/github/v/tag/BeaNotedttlz/LabSync)

## Overview

LabSync centralizes the management of different Lab devices to reduce complexity.
This provides a more simple and intuitive interface for controlling different devices simultaneously.

LabSync allows for the following features:

* **Unified Control** - Single interface for multiple devices
* **Multi-Device support** - Compatible with various instrument types
* **Real-Time Data Acquisition** - Live data streaming and visualization
* **Preset Saving/Loading** - Save device parameters and load them again

For this the following device backends are included:

* **JAT EcoVario 114D** - Linear Stage (primarily motor decoder) 
* **Omicron LuxX+** - Laser
* **TTi Instruments TGA1244** - 4 Channel Frequencygenerator (RS232 Backend) 
* **Rhode & Schwarz FSV3000** - Spectrum-Analyzer (TCPIP Backend)

## Quick Start

### Prerequisites

To run the following needs to be installed:

* Python 3.8 or higher
* pip (Python Package installer)

### 1. Install
```bash
# Clone the repository
git clone https://github.com/BeaNotedttlz/LabSync.git
# Otherwise download 'LabSync.zip' from releases

# Install required Python packages
cd LabSync
pip install -r requirements.txt
```

### 2. Run based on your OS:
```bash
# Windows:
python LabSync-Win.pyw
# Note that double click also works

# Unix:
./LabSync
# Or run to enable double click to launch:
chmod +x LabSync-Unix  
```
### Virtual environment (Optional but Recommended)
```bash
python -m venv venv

# Windows:
venv\Scripts\activate

# Unix:
source venv/bin/activate

cd LabSync
pip install -r requirements.txt
```

## General Usage

### 1. First Startup

When first starting LabSync you get the following Window:

![LabSync normal tab](NormTab.png)

On this page you can:

* See panel information (Left side)
  * Port status
  * Open/Close device ports
  * Laser information pop-up window with crucial information
  * Laser emission and Stage poistioning status
* Standard Stage controls
  * View current position and target position
  * Set new position (Write to Target Press: <kbd>Enter</kbd>)
  * Set new Stage speed
  * Start/Stop Stage
  * View current error-code
* Standard Laser control
  * Laser controls:
    * Modulation modes (Standy, CW, Analog, Digital)
    * Control modes [If applicable] (ACC, APC)
    * Laser power (0-100%)
  * TGA controls:
    * Modulation Frequency (0Hz-40MHz)
    * Select Lockmode (indep, maser, slave, off)
    * Select Channel (0-4)
