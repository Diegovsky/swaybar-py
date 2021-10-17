import asyncio
from asyncio.exceptions import CancelledError
import json
import sys
import random
import signal
import string
from dataclasses import dataclass
from dataclasses_json import dataclass_json, Undefined
from typing import Optional, Union 
import aioconsole

Number = Union[int, float]

# This will ignore any non specified fields.
@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class ClickEvent:
    name: str
    x: Number 
    y: Number
    button: int
    event: int
    relative_x: Number
    relative_y: Number
    width: Number
    height: Number
    instance: Optional[str] = None


class Module:
    def __init__(self, bar: 'Bar'):
        self._bar = bar
        self._id = bar.reserve_id()

    # You should override this.
    async def run(self):
        """ This method is called once after initialising the bar.
            You must override this."""
        raise NotImplemented

    async def _run(self):
        """ This method calls `self.run` and prevents exceptions from messing with the bar."""
        try:
            await self.run()
        except Exception as e:
            self.print("An exception '{}' has occoured.".format(repr(e)))

    def print(self, text, sync=True) -> None:
        """ Outputs text to the bar. """
        self._bar.output[self._id] = text
        if sync:
            self._bar.print_status()

    async def mouse_event(self, info: ClickEvent) -> None:
        """ This method is called when the module is clicked. """
        pass

    def hide(self, sync=False):
        """ Hides the module from the bar.  """
        try:
            self._bar.output.pop(self._id)
            # Immediatelly remove it from the output if sync is True.
            if sync:
                self._bar.print_status()
        except KeyError:
            pass

class Bar:
    # This is plenty, onless you have a million modules in one bar (16k display?).
    ID_LEN=2
    __CHARTABLE = string.ascii_letters + string.digits

    def __init__(self):
        self.modules: dict[str, Module] = {}
        self.output: dict[str, str] = {}
        self._should_exit = False
        self.tasks: list[asyncio.Task]
        self.instance = Bar.__gen_id()

    def print_status(self):
        body = []
        for id, element in self.output.items():
            if type(element) is not list:
                element = [element]
            for val in element:
                body.append(dict(full_text=val, urgent=False, name=id))
        
        sys.stdout.write(json.dumps(body)+',')
        sys.stdout.flush()

    def add_module(self, cls):
        module = cls(self)
        self.modules[module._id] = module

    @classmethod
    def __gen_id(cls):
        return ''.join(random.choices(cls.__CHARTABLE, k=cls.ID_LEN))

    def reserve_id(self):
        id = ''
        while True:
            id = Bar.__gen_id()
            if id not in self.output:
                break

        return id

    def handle_signal(self, _signum, _frame):
        for task in self.tasks:
            task.cancel()
        return

    async def oversee(self):
        """ Reads stdin to receive swaybar click events. """
        try:
            while True:
                line = await aioconsole.ainput()
                line = line.strip()
                # swaybar also sends an infinite array of events.
                if line == '[':
                    continue
                try:
                    # Remove trailing comma if it is there.
                    line = line if line[0] != ',' else line[1:]
                    evt = ClickEvent.from_json(line)
                    try:
                        await self.modules[evt.name].mouse_event(evt)
                    except KeyError:
                        pass
                except json.JSONDecodeError:
                    pass

        # If stdin is closed, quit.
        except EOFError:
            return
               
    async def _run(self):
        """ Starts the main event loop.
            Also, installs signal handlers for SIGINT """
        signal.signal(signal.SIGINT, self.handle_signal)
        print(json.dumps(dict(
            version = 1,
            click_events = True,
            stop_signal = signal.SIGINT,
        )))
        self._loop = asyncio.get_event_loop()
        # swaybar wants an infinite array, so we emulate that,
        # since it's not possible only using the json module.
        sys.stdout.write('[')
        self.tasks = list(map(
        lambda module: self._loop.create_task(
                module._run(),
                name=module.__class__.__name__,
            ), self.modules.values()))
        self.tasks.append(asyncio.create_task(self.oversee(), name='overseer'))
        for task in self.tasks:
            try:
                await task
            except CancelledError:
                pass

    def run(self):
        asyncio.run(self._run())
