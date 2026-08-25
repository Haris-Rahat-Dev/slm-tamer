.PHONY: core-install app-install core-dev app-dev

core-install:
	cd core && uv sync

app-install:
	cd app && pnpm install

core-dev:
	cd core && uv run python -m slmtamer

app-dev:
	cd app && pnpm tauri dev
