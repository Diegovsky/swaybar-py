import asyncio
from asyncio.exceptions import CancelledError
import json
import sys
import random
import signal
import string

import collections


ClickEvent = collections.namedtuple('ClickEvent',
    ['name', 'instance', 'x', 'y', 'button', 'event',
     'relative_x', 'relative_y', 'width', 'height']
)

class Module:
    def __init__(self, bar: 'Bar'):
        self._bar = bar
        self._id = bar.reserve_id()

    # You should override this.
    async def run(self):
        """ This method is called once after initialising the bar.
            You must override this."""
        raise NotImplemented

    def print(self, text, sync=True):
        """ Outputs text to the bar. """
        self._bar.output[self._id] = text
        if sync:
            self._bar.print_status()

    async def mouse_event(self, info: ClickEvent):
        """ This method is called when the module is clicked. """
        pass

    def hide(self):
        """ Hides the module from the bar.  """
        try:
            self._bar.output.pop(self._id)
        except KeyError:
            pass

class Bar:
    # This is plenty, onless you have a million modules in one bar (16k display?).
    ID_LEN=2
    __CHARTABLE = string.ascii_letters + string.digits

    def __init__(self):
        self.modules: list[Module] = []
        self.output: dict[str, str] = {}
        self._should_exit = False
        self.tasks: list[asyncio.Task]

    def print_status(self):
        body = []
        for element in self.output.values():
            if type(element) is not list:
                element = [element]
            for val in element:
                body.append(dict(full_text=val, urgent=False))
        
        sys.stdout.write(json.dumps(body)+',')
        sys.stdout.flush()

    def add_module(self, cls):
        self.modules.append(cls(self))

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
        self._should_exit = True

    async def oversee(self):
        while True:
            if self._should_exit:
                for task in self.tasks:
                    task.cancel()
                return
            else:
                await asyncio.sleep(1)

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
                module.run(),
                name=module.__class__.__name__,
            ),
        self.modules))
        overseer = asyncio.shield(self.oversee())
        for task in self.tasks:
            try:
                await task
            except CancelledError:
                pass
        await overseer

    def run(self):
        asyncio.run(self._run())
