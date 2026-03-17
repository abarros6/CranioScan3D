"""Utility subpackage for CranioScan3D.

Contains four utility modules used across all pipeline stages:

- logging:    setup_logging() — configures the root logger with console
              and optional rotating file handlers at pipeline startup.

- shell:      run_command() — wraps subprocess.run() with logging,
              timeout enforcement, and RuntimeError on non-zero exit.
              All COLMAP and OpenMVS calls go through this function.

- io:         read_mesh(), write_mesh(), read_json(), write_json() —
              centralised file I/O so the rest of the pipeline doesn't
              import Open3D or json directly.

- validation: validate_input_video(), validate_dependencies() —
              called at pipeline startup to fail fast with clear error
              messages if the input or external tools are missing.
"""
