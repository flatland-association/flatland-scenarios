# Scenario generator

This is a tool to help you create Flatland environments and generate customized scenarios.

Scenarios 1-3 are added as examples. They were used as playground examples to test the drawing tool and the [deadlock avoidance heuristic](https://github.com/flatland-association/flatland-baselines/tree/main/flatland_baselines/deadlock_avoidance_heuristic). 

## Data Model and Data Flow

### Glossary

| Term             | Description                                                                                                                                                                                        |
|------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Scenario         | Rail, lines, Services and malfunction parameters fixed (each train has a set of stops with routing flexibility and a time window at each stop).                                                    |
| Initial Scenario | Defines services all starting at zero, malfunction usually empty.                                                                                                                                  |
| Metadata         | Defines services: a service template from the initial scenario and schedule specs on how to instantiate the scenario.                                                                              |
| Line             | A line is a sequence of stops with routing flexibility at intermediates and target but not initial (in strict Flatland sense, lines are agents with stops already assigned and max speeds as well) |
| Train Category   | Used to differentiate schedule specs for different train categories.                                                                                                                               |
| Service          | Corresponds to a Flatland agent with the stops to serve in a given time-windows (Flatland Timetable).                                                                                              |
| Scene            | A set of lines.                                                                                                                                                                                    |

### Data Model

```mermaid
classDiagram
  class metadata {
    ScheduleSpecs defaults.scheduleSpecs
  }
  class scenario {
    ScheduleSpecs scheduleSpecs
  }
  metadata "1" --> "1..*" level
  level "1" --> "1..*" scenario
  scenario "1" --> "1..*" Service
  class ScheduleSpecs {
    ScheduleSpec IR
    ScheduleSpec RE
    ScheduleSpec S
    ScheduleSpec C
  }
  class ScheduleSpec {
    int "initialShift"
    int "periodicity"
    int "times"
    int "travelFactor"
  }
  class Service {
    string name
    Scenario template
    Optional[ScheduleSpec] scheduleSpec
  }

  class Scenario {
    gridDimensions
    grid
    overpasses
    stations
    nextStationId
    lines
    schedules
    trainCategories
    flatlandLine
    flatlandTimetable
  }

```

### From Initial Scenario to Set of Scenarios

```mermaid
flowchart LR
  H(tbd.py) --> F
  B(flatland_environment_drawing_tool.html) --> C[scenario_initial.json]
  C --> D(gen_comp_from_metadata_and_initial_scenario.py)
  F[metadata.json] --> D
  D --> E[level_X/level_X_scenario_Y.json]
  D --> f[level_X/level_X_scenario_Y.pkl]
```

### From Initial Scenario to `RailEnv` (`reset` drawing from distribution in metadata)

```mermaid
flowchart LR
  H(tbd.py) --> F
  B(flatland_environment_drawing_tool.html) --> C[scenario_initial.json]
  C --> D(tbd.py)
  F[metadata.json] --> D
  D --> I[RailEnv with rail/line/schedule generator]
```

## Drawing Tool

| workflow                                        |
|-------------------------------------------------|
| [`Initialize grid`](#initialize-grid)           |
| [`Draw grid-world`](#draw-grid-world)           |
| [`Create Lines`](#create-lines)                 |
| [`Define train classes`](#define-train-classes) |
| [`Create Schedules`](#create-schedules)         |
| [`Export environment`](#export-environment)     |

### Initialize grid

Choose the number of rows and columns and how large they should be displayed on the screen. You can always resize both cell size and grid dimensions.

:warning: By shrinking the size of your grid you can delete parts of it (cannot be undone)!

You can also import previously exported JSON files which include both grid and cell size. You can use the *raw data import* at the bottom to only import the
grid, overpasses or stations.

### Draw grid-world

Use the **left mouse button to draw**, the **right mouse button to delete**. You can use your mouse or keyboard to alter, rotate or flip elements, define train
stations or overpasses.

Use the arrow keys to navigate on the grid and the keyboard shortcuts listed in the tool for more efficient drawing.

:bulb: Station-cells adjacent to each other have the same station-id, i.e. belong to the same station.

### Create Lines

To create Lines click the *Lines & Schedules* button. Each Line has

- a unique **name**
- an **ordered list of stations** (can be created by clicking on the map or comma separated manual input)
- **start cell** and **end cell** (intermediate stations are identified through all corresponding cells to allow for the use of this flexibility)

Once a Line is created, you can display the shortest path lengths between the stations and the Line can be

- edited
- copied
- reversed
- deleted

### Define train classes

In order to choose what train is running your Lines you can create classes of trains whose sole parameter is **maximum speed**. There are 4 predefined train
classes.

### Create Schedules

To create Schedules click the *Lines & Schedules* button.

- give it a **name**
- select a **Line**
- select a **train class**
- choose the **travel factor** (this factor is multiplied with the length of the shortest path connecting to the subsequent station to add time flexibility)
- choose the **dwell time** [default: 2] (the dwell time is the number of time steps between the *latest arrival* and the *earliest departure* used in the
  automatic filling of the schedule)
- apply a **shift** to the whole schedule (this is mainly used when copying a Schedule to then shift the copy)

Schedules can be copied (and then shifted) within the drawing tool. However, to create scenarios with lots of shifted Schedules on the same lines, use
`generate_scenario.py` with your customized duplication function (see below).

### Export environment

Export your creation to save it or to use it when finished by clicking the *Export All (.json)* button.

You can use the *raw data import* at the bottom to only export the grid, overpasses or stations.

Click the *Flatland Download* button to download `flatland_import.py` to create the Flatland environment and save it as .pkl to then run your simulation. (If
you use `generate_scenario.py` to generate your scenario, do this before running `flatland_import.py`.)

## Generate scenario

Use the `generate_scenario.py` script to duplicate the initial Schedules to create a complete schedule:

- the **initial_shift** defines the first *earliest departure*
- the **shift** defines the shift from one Schedule to the next
- **times** defines how many times the Schedule should be created (it is technically not copied, so `times=1` results in only one Schedule)

Using this method you only need to create each unique Schedules once in the drawing tool.

:warning: To use this script without much customization, name your schedules *XY 1.1*, *XY 2.1*, etc. (e.g. *IC 1.1*, *IC 2.1*, *RE 1.1*, *RE 2.1*).