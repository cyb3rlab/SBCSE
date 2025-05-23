# Implementation Details

This file presents implementation details regarding the main modules of SBCSE.

## Simulator Module

The simulator module simulates/emulates the four main components of the system, namely the Building Operating System (BOS), elevators (ELV), robots (ROB), and Robot Platform (RPF). The corresponding functionality is implemented in the files indicated below, which are located in `simulator/`.

| File name    | Functionality               |
|--------------|-----------------------------| 
| `bossim.py`  | Emulate the BOS component   |
| `elvsim.py`  | Simulate the ELV component  |
| `robsim.py`  | Simulate the ROB component  |
| `rpfsim.py`  | Emulate the RPF component   |


## Network Communication Module

The network communication module implements the communication protocols and communication-related data processing. It mainly includes defining and managing the logic for sending and receiving communication messages, the system's data model and structure, and the MQTT message handling for each component. The corresponding functionality is implemented in the files indicated below, which are located in `mqtt_communication_module/`.

| File name                | Functionality                                   |
|--------------------------|-------------------------------------------------|
| `Authenticator/`         | Functions related to user authentication        |
| `certs/`                 | Examples of private keys and CA certificates    |
| `Scenario_msg_handler/`  | Communication simulation for the attack module  |
| `bosmsghandler.py`       | MQTT message handling for the BOS component     |
| `datamodel.py`           | Defines the data models and structures          |
| `elvmsghandler.py`       | MQTT message handling for the ELV component     |
| `mqtt_msghandler.py`     | Base class for handling MQTT messages           |
| `robmsghandler.py`       | MQTT message handling for the ROB component     |
| `rpfmsghandler.py`       | MQTT message handling for the RPF component     |


## Device Motion Module

The device motion module defines and configure various scenarios and simulation conditions for robots, elevators, such as the operation mode of elevators, the task allocation strategy for robots, etc. The corresponding functionality is implemented in the files indicated below, which are located in `device_motion_module/`.

| File name          | Functionality                                                         |
|--------------------|-----------------------------------------------------------------------|
| `routes/`          | Store and manage robot path information and map data                  |
| `elevator.py`      | Define and manage the basic properties and behaviors of the elevator  |
| `servicerobot.py`  | Define and manage the basic properties and behaviors of the robot     |


## Security Attack Module

The security attack module encapsulates the logic flow of various simulated attacks, and it is used via the main control program through function interfaces to implement attack simulation. The corresponding functionality is implemented in the files indicated below, which are located in `security_attack_module/`.


| File name            | Functionality                            |
|----------------------|------------------------------------------|
| `BAC/`               | Definitions related to BAC attacks       |
| `DDoS.py`            | Definitions related to DDoS attacks      |
| `MITM.py`            | Definitions related to MITM attacks      |
| `scene_switcher.py`  | Attack scenario selection functionality  |


## Fuzzing Module

The fuzzing module contains files created based on the target files from other modules for which fuzzing was conducted. The corresponding functionality is implemented in the files indicated below, which are located in `fuzzer/` and its subdirectories.

| File name               | Functionality                        |
|-------------------------|--------------------------------------|
| *`bosfuzzer/`*          |                                      |
| - `fbosmsghandler.py`   | Corresponds to `bosmsghandler.py`    |
| - `fbosnormalmode.py`   | Corresponds to `BOS_normal_mode.py`  |
| - `fbossim.py`          | Corresponds to `bossim.py`           |
| *`elvfuzzer/`*          |                                      |
| - `felvmsghandler.py`   | Corresponds to `elvmsghandler.py`    |
| - `felvmsghandler2.py`  | Corresponds to `elvmsghandler.py`    |
| - `felvsim.py`          | Corresponds to `elvsim.py`           |
| - `felvsim2.py`         | Corresponds to `elvsim.py`           |
| *`robfuzzer/`*          |                                      |
| - `frobmsghandler.py`   | Corresponds to `frpmsghandler.py`    |
| - `frobmsghandler2.py`  | Corresponds to `frpmsghandler.py`    |
| - `frobsim.py`          | Corresponds to `robsim.py`           |
| - `frobsim2.py`         | Corresponds to `robsim.py`           |
| *`rpffuzzer/`*          |                                      |
| - `frcp.py`             | Corresponds to `rcp.py`              |
| - `frpfmsghandler.py`   | Corresponds to `frpmsghandler.py`    |
| - `frpfmsghandler2.py`  | Corresponds to `frpmsghandler.py`    |
| - `frpfnormalmode.py`   | Corresponds to `RPF_normal_mode.py`  |
| - `frpfnormalmode2.py`  | Corresponds to `RPF_normal_mode.py`  |
| - `frpfsim.py`          | Corresponds to `rpfsim.py`           |
| - `frpfsim2.py`         | Corresponds to `rpfsim.py`           |


## Other Modules

SBCSE includes several other modules that are located in different directories, as follows. In `control_protocol/` are contained the message control protocol definitions for RPF. In `database/` are stored the user database and generated logs. In `utils/` are placed functions related to log management and formatting, as well as configuration files and time management files. For more details, see the corresponding files.
