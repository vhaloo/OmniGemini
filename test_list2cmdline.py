import asyncio
import subprocess
async def test():
    cli_path = 'gemini'
    model_choice = 'flash'
    prompt = 'Hello "quotes" and C:\\paths'
    cmd_str = subprocess.list2cmdline([cli_path, "--yolo", "--model", model_choice, prompt])
    print('Command string:', cmd_str)
    
    try:
        p = await asyncio.create_subprocess_shell(
            cmd_str,
            stdout=asyncio.subprocess.PIPE, 
            stderr=asyncio.subprocess.STDOUT
        )
        out, _ = await p.communicate()
        print('Output:', out.decode('utf-8', errors='replace')[:100])
    except Exception as e:
        print('Error:', e)

asyncio.run(test())
