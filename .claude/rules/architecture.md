# Architecture Rules

- Keep the exporter, formatter, and client layers decoupled. Exporters depend on `CtrlMapClient` and formatters, but formatters must not depend on exporters or the client.
- One exporter class per ControlMap domain (policies, governance, procedures, risks), each inheriting `BaseExporter`.
- One formatter class per output format, each inheriting `BaseFormatter`.
- Configuration is always read into an `AppConfig` dataclass — never pass raw dicts or configparser objects between layers.
- The CLI layer (`cli.py`) is the only place that orchestrates exporters. Exporters do not call each other.
