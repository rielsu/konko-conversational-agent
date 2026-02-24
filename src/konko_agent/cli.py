"""Interactive CLI for the Konko agent."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from konko_agent.config.loader import load_config
from konko_agent.infrastructure.llm_client import KonkoLLMClient
from konko_agent.infrastructure.state_store import InMemoryStateStore
from konko_agent.orchestration.runtime import AgentRuntime


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Konko Agent interactive demo")
    p.add_argument("--config", "-c", required=True, help="Path to agent YAML config")
    p.add_argument("--session", "-s", default="cli-session", help="Session ID")
    return p.parse_args()


async def run_interactive(runtime: AgentRuntime, session_id: str) -> None:
    # Start the session and show the configured greeting from state.
    greeting = await runtime.start_session(session_id)
    print(greeting)
    print()
    while True:
        try:
            line = input("You: ").strip()
        except EOFError:
            break
        if not line:
            continue
        if line.lower() in ("quit", "exit", "q"):
            print("Goodbye.")
            break
        reply = await runtime.handle_message(session_id, line)
        print(f"Agent: {reply}")
        print()


def main() -> int:
    args = parse_args()
    try:
        config = load_config(args.config)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    base_url = config.llm_base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com")
    api_key = os.environ.get("OPENAI_API_KEY", "")

    llm = KonkoLLMClient(base_url=base_url, model=config.llm_model, api_key=api_key or None)
    store = InMemoryStateStore()
    runtime = AgentRuntime(config, llm, store)

    asyncio.run(run_interactive(runtime, args.session))
    return 0


if __name__ == "__main__":
    sys.exit(main())
