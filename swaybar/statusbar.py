import asyncio
import json
import sys
import random
import signal
import string

import collections

__CHARTABLE = string.ascii_letters + string.digits

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
        """ This method is called once after initialising the bar."""
        raise NotImplemented

    def print(self, text, sync=True):
        """ Outputs text to the bar. """
        self._bar.output[self._id] = text
        if sync:
            self._bar.print_status()

    async def mouse_event(self, info: ClickEvent):
        """ This method is called when the module is clicked. """
        pass

    async def exit(self):
        """ This method is called when swaybar asks to exit. """
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

    def __init__(self):
        self.tasks: list[Module] = []
        self.output: dict[str, str] = {}
        self._should_exit = False
        self._loop = asyncio.get_event_loop()

    def print_status(self):
        body = []
        for element in self.output.values():
            if type(element) is not list:
                element = [element]
            for val in element:
                body.append(dict(full_text=val, urgent=False))
        
        sys.stdout.write(json.dumps(body)+',')
        sys.stdout.flush()

    @classmethod
    def __gen_id(cls):
        return ''.join(random.choices(__CHARTABLE, k=cls.ID_LEN))


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
        if self._should_exit:
            await asyncio.wait(
                map(
                    lambda mod: mod.exit(),
                    self.tasks
                )
            )
            self._loop.stop()

    def run(self):
        """ Starts the main event loop.
            Also, installs signal handlers for SIGINT """
        signal.signal(signal.SIGINT, self.handle_signal)
        print(json.dumps(dict(
            version = 1,
            click_events = True,
            stop_signal = signal.SIGINT,
        )))
        # swaybar wants an infinite array, so we emulate that,
        # since it's not possible only using the json module.
        sys.stdout.write('[')
        try:
            self._loop.run_until_complete(asyncio.wait(map(
                lambda task: self._loop.create_task(task.run()),
                self.tasks
            )))

        finally:
                self._loop.close()
