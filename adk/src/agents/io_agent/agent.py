from shared.agent_factory import create_se_agent
from shared.tools.design_date import current_date
from shared.tools.design_filesystem import (
    save_artifact,
    check_lock,
    release_lock,
    list_versions,
    promote_artifact,
    read_file,
    list_staging_files,
    clear_staging_folder,
    check_active_blocks,
)
from . import prompt

agent = create_se_agent(
    name="io_agent",
    description=prompt.description,
    instruction=prompt.instruction,
    tools=[
        save_artifact,
        check_lock,
        release_lock,
        list_versions,
        promote_artifact,
        read_file,
        current_date,
        list_staging_files,
        clear_staging_folder,
        check_active_blocks,
    ],
    agent_subdir="io_agent",
)

root_agent = agent
