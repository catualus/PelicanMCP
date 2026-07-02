from __future__ import annotations

from fastmcp import FastMCP


def register_prompts(mcp: FastMCP) -> None:
    @mcp.prompt(
        name="troubleshoot_server",
        description="Guided diagnostic walkthrough for a Pelican server.",
    )
    def troubleshoot_server(server_identifier: str) -> str:
        return (
            f"You are diagnosing issues with Pelican server `{server_identifier}`.\n\n"
            "Work through these steps in order and stop early once you've identified the most "
            "likely cause:\n\n"
            "1. Resolve the server\n"
            "   - If the identifier looks like a UUID, short identifier, or external ID, call "
            "`pelican_ai_search_servers` with it first.\n"
            "   - Otherwise call `pelican_ai_get_server_summary` directly with the numeric id.\n\n"
            "2. Read the summary\n"
            "   - Note `suspended`, `id`, `identifier`, `uuid`, and any external_id.\n"
            "   - If suspended, that is almost always the answer — surface it and stop.\n\n"
            "3. Inspect node health\n"
            "   - Fetch the full server with `pelican_app_get_servers_server` (note the node id).\n"
            "   - Call `pelican_app_get_nodes_node` to confirm the node exists and is not in "
            "maintenance.\n\n"
            "4. Check databases\n"
            "   - Call `pelican_app_get_servers_server_databases` and confirm the expected DBs exist.\n\n"
            "5. (Optional) Live state\n"
            "   - If you have an Account (pacc_) key configured, use `pelican_client_server_status` "
            "with the server UUID for current_state + resource usage, and "
            "`pelican_client_console_tail` to read recent console output.\n\n"
            "6. Summarize\n"
            "   - Output: (a) what you found, (b) most likely cause, (c) one concrete next "
            "action the operator should take. Do not modify anything without explicit user "
            "confirmation."
        )

    @mcp.prompt(
        name="provision_user_and_server",
        description="Guided workflow to create a Pelican user and then a server for them.",
    )
    def provision_user_and_server(username: str, email: str, egg_id: int) -> str:
        return (
            f"Goal: provision a new Pelican user `{username}` (email `{email}`) and a server "
            f"running egg `{egg_id}`.\n\n"
            "Pelican notes: eggs are top-level (there are no nests), and the Application API has "
            "no locations — deploy by node capacity directly.\n\n"
            "Follow this sequence and PAUSE for explicit user confirmation before any write call.\n\n"
            "1. Pre-flight checks (read-only — no confirmation needed)\n"
            "   - `pelican_ai_search_users` with the email and username; if a user already exists, "
            "stop and surface them instead of creating a duplicate.\n"
            "   - `pelican_ai_list_eggs` (or `pelican_app_get_eggs_egg` with "
            f"`egg={egg_id}`) to confirm the egg exists and capture its default startup, docker "
            "image, and required env variables.\n"
            "   - `pelican_app_get_nodes_deployable` to find a node with capacity.\n"
            "   - `pelican_app_get_nodes_node_allocations` on that node to find an unassigned "
            "allocation (the `default` allocation id for the server).\n\n"
            "2. Confirm with the operator\n"
            "   - Echo back the planned user payload and server payload (memory, disk, cpu, "
            "allocation id, egg, docker_image, startup, environment, feature_limits). Ask for "
            "explicit approval before proceeding.\n\n"
            "3. Create the user\n"
            "   - `pelican_app_post_users` with `body` containing `username`, `email`, "
            "`first_name`, `last_name`, `password` (or omit to trigger an email reset).\n\n"
            "4. Create the server\n"
            "   - `pelican_app_post_servers` with `body` including `user`, `egg`, `docker_image`, "
            "`startup`, `environment`, `limits`, `feature_limits`, and `allocation.default`.\n\n"
            "5. Report\n"
            "   - Output a compact summary of the created user (id, email) and server "
            "(id, identifier, uuid, allocation). Recommend the operator verify in-panel."
        )
