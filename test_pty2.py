import asyncio
import subprocess
import shutil
import sys

async def test():
    cli_path = shutil.which('gemini')
    prompt = 'run a simple powershell command to list files in C:\\'
    
    args_list = [cli_path, '--yolo', '--model', 'flash', '-p', prompt]
    cmd_str = subprocess.list2cmdline(args_list)
    print('Command:', cmd_str)
    
    try:
        p = await asyncio.create_subprocess_shell(
            cmd_str,
            stdout=asyncio.subprocess.PIPE, 
            stderr=asyncio.subprocess.STDOUT,
            stdin=subprocess.DEVNULL, # Test with DEVNULL and CREATE_NO_WINDOW
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        out, _ = await p.communicate()
        res = out.decode('utf-8', errors='replace')
        if 'AttachConsole failed' in res:
            print('FAILED: AttachConsole error detected.')
        else:
            print('SUCCESS: No AttachConsole error.')
        print('Tail Output:', res[-500:])
    except Exception as e: print(e)

asyncio.run(test())
