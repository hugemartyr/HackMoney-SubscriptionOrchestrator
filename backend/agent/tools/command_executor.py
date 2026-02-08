import asyncio
import os
from typing import AsyncGenerator, Tuple, Optional, Dict, Any

from services.sandbox_fs_service import require_root

async def execute_command(
    command: str, 
    cwd: Optional[str] = None,
    timeout: int = 300
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Execute a command in the local sandbox using subprocess.
    Streams output line by line.
    
    Yields events:
    - {"type": "output", "data": "line of output"}
    - {"type": "exit", "code": 0}
    - {"type": "error", "message": "error description"}
    """
    root = require_root()
    working_dir = str(root / cwd) if cwd else str(root)
    
    # Ensure working dir exists
    if not os.path.exists(working_dir):
        yield {"type": "error", "message": f"Directory not found: {working_dir}"}
        return

    try:
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=working_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT, # Merge stderr into stdout
            shell=True
        )
        
        # Read output line by line
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            
            decoded = line.decode('utf-8', errors='replace')
            yield {"type": "output", "data": decoded}
            
        # Wait for exit
        try:
            exit_code = await asyncio.wait_for(process.wait(), timeout=timeout)
            yield {"type": "exit", "code": exit_code}
        except asyncio.TimeoutError:
            process.terminate()
            yield {"type": "error", "message": f"Command timed out after {timeout} seconds"}
            
    except Exception as e:
        yield {"type": "error", "message": str(e)}
