"""Run the complete banking analytics and recommendation pipeline."""

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
DBT_DIRECTORY = PROJECT_ROOT / "dbt"


def run_step(step_name, command, working_directory):
    """Run one pipeline step and stop immediately if it fails."""

    print("\n" + "=" * 72)
    print(step_name)
    print("=" * 72)

    subprocess.run(
        command,
        cwd=working_directory,
        check=True,
    )


def main():
    """Execute the complete pipeline in dependency order."""

    run_step(
        "STEP 1: BUILD CUSTOMER SEGMENTATION FEATURES",
        [
            "dbt",
            "run",
            "--select",
            "+mart_customer_segmentation_features",
            "--profiles-dir",
            ".",
        ],
        DBT_DIRECTORY,
    )

    run_step(
        "STEP 2: TRAIN CUSTOMER SEGMENTATION MODEL",
        [
            sys.executable,
            "-m",
            "src.segmentation.train_segmentation",
        ],
        PROJECT_ROOT,
    )

    run_step(
        "STEP 3: BUILD CUSTOMER SEGMENT MART",
        [
            "dbt",
            "run",
            "--select",
            "mart_customer_segments",
            "--profiles-dir",
            ".",
        ],
        DBT_DIRECTORY,
    )

    run_step(
        "STEP 4: GENERATE PRODUCT RECOMMENDATIONS",
        [
            sys.executable,
            "-m",
            "src.recommendations.generate_recommendations",
        ],
        PROJECT_ROOT,
    )

    run_step(
        "STEP 5: BUILD AND TEST COMPLETE DBT PROJECT",
        [
            "dbt",
            "build",
            "--profiles-dir",
            ".",
        ],
        DBT_DIRECTORY,
    )

    print("\n" + "=" * 72)
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 72)


if __name__ == "__main__":
    main()