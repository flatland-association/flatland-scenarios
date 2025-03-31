import os
import tempfile
import zipfile
from pathlib import Path
from typing import Callable

import pandas as pd
from flatland.env_generation.env_generator import env_generator
from flatland.envs.persistence import RailEnvPersister
from yaml import safe_load


def create_envs_from_metadata(metadata_template_file: Path, outdir: Path = None, initial_seed: int = 42):
    metadata = pd.read_csv(metadata_template_file)
    print(metadata.to_markdown())
    if outdir is None:
        outdir = Path.cwd()

    metadata["seed"] = initial_seed + metadata.index

    assert os.path.exists(outdir)

    with tempfile.TemporaryDirectory() as tmpdirname:
        print('Using temporary directory', tmpdirname)

        for k, v in metadata.iterrows():
            test_id = v["test_id"]
            env_id = v["env_id"]
            seed = v["seed"]
            print(f"Generating env for {test_id}/{env_id}")
            print(f"   seed: {seed}")
            print(f"   data: {v}")

            os.makedirs(f"{tmpdirname}/{test_id}", exist_ok=True)

            env, _, _ = env_generator(
                n_agents=v["n_agents"],
                x_dim=v["x_dim"],
                y_dim=v["y_dim"],
                n_cities=v["n_cities"],
                max_rail_pairs_in_city=v["max_rail_pairs_in_city"],
                grid_mode=v["grid_mode"],
                max_rails_between_cities=v["max_rails_between_cities"],
                malfunction_duration_min=v["malfunction_duration_min"],
                malfunction_duration_max=v["malfunction_duration_max"],
                malfunction_interval=v["malfunction_interval"],
                speed_ratios=safe_load(v["speed_ratios"]),
                seed=seed)
            RailEnvPersister.save(env, f"{tmpdirname}/{test_id}/{env_id}.pkl")

        metadata.to_csv(f"{tmpdirname}/metadata.csv")

        zip_directory(tmpdirname, outdir / "environments.zip")


def zip_directory(directory_path, zip_path, filter: Callable[[Path], bool] = None):
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                if filter is None or filter(file):
                    arcname = os.path.relpath(os.path.join(root, file), directory_path)
                    zipf.write(os.path.join(root, file), arcname)


if __name__ == '__main__':
    create_envs_from_metadata(Path("./metadata.csv"))
