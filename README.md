# swaybar-py
A python API to customize your swaybar status.

# Getting Started
To get started you need to subclass `swaybar.Module` and override the `run` method:

```python3
import datetime
import asyncio
import swaybar

class Time(swaybar.Module):
    async def run(self):
        while True:
            time = datetime.datetime.now()
            self.print(time.strftime("%R")
            await asyncio.sleep(60)
```

Then, add it to your `Bar`:

```python3
bar = swaybar.Bar()
bar.add_module(Time)

# This will run an asyncio eventloop for you.
bar.run()

```

Just set sway's swaybar status_command to your new shiny script and you're good to go:

```
 bar {
    ...
    status_command "yourscript.py"
 }
```
![image](https://user-images.githubusercontent.com/46163903/133635644-fafb773c-0301-4e17-a80e-ab62ada01451.png)

## How does this relate to [py3status](https://github.com/ultrabug/py3status)?
I started this mainly for personal use so I didn't search if there were any better alternatives, just wanted to make a quick and fun project.

Py3status is really good and comprehensive and includes a lot of modules out of the box. This library aims to facilitate the outputting of modules to `swaybar`, nothing else.
