import os
import random
import yaml


def generate_test_yaml(
    num_robots: int,
    output_dir: str = "config",
    sim_speed: int = 1,
    floors=(3, 4, 5, 6),
    seed: int = 42,
):
    """
    Generate scenario yaml with:
      - num_robots robots
      - num_robots schedule_work tasks
      - task floors assigned in round-robin over `floors` and shuffled
    """

    os.makedirs(output_dir, exist_ok=True)

    output_file = os.path.join(
        output_dir,
        f"scenario_{num_robots}robots.yaml"
    )

    rng = random.Random(seed)

    # -----------------------
    # Robots
    # -----------------------
    robots = [
        {
            "name": f"rob{i+1}",
            "floor": 2,
            "position": [0, 0, 0],
        }
        for i in range(num_robots)
    ]

    # -----------------------
    # Tasks: round-robin floors
    # -----------------------
    base_floors = list(floors) * ((num_robots + len(floors) - 1) // len(floors))
    base_floors = base_floors[:num_robots]

    # Shuffle to avoid fixed patterns
    rng.shuffle(base_floors)

    tasks = []
    for i in range(num_robots):
        tasks.append({
            "task_no": i + 1,
            "task_floor": base_floors[i],
            "task_name": "schedule_work"
        })

    # -----------------------
    # Config
    # -----------------------
    config = {
        "service_robots": robots,

        "tasks": tasks,

        "elevators": [
            {
                "name": "elv",
                "floor": 1,
                "door": "close",
                "movingStatus": "stay",
                "inDrivingPermission": False,
            }
        ],

        "attack_scenario": [
            {"scenario_name": "None", "target": "None"}
        ],

        "protocol": "MQTT",

        "sim_speed": sim_speed,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            config,
            f,
            sort_keys=False,
            allow_unicode=True
        )

    print(f"[YAML] Generated -> {output_file}")
    return output_file
