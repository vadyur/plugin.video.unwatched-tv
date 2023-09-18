from enum import Enum
import json
from typing import List

from vdlib.kodi.compat import translatePath
from vdlib.util import filesystem

class OptsTypes(Enum):
    ALL = "all"
    WISH = "wish"
    JUNK = "junk"

class UnwatchedOpts(object):
    def __init__(self) -> None:
        self.filename = translatePath("special://userdata/addon_data/plugin.video.unwatched-tv/opts.json")
        self.opts = {}
        self.load()

    def load(self) -> None:
        self.prev = self.opts.copy()
        if filesystem.exists(self.filename):
            with filesystem.fopen(self.filename, "r") as file:
                self.opts = json.load(file)

    def save(self) -> None:
        if (self.prev != self.opts):
            with filesystem.fopen(self.filename, "w") as file:
                json.dump(self.opts, file)

    def move_to(self, where: OptsTypes, tvshowid: int):
        IDs: List[int] = self.opts.get(where.value, [])
        if tvshowid not in IDs:
            IDs.append(tvshowid)
        self.opts[where.value] = IDs
        if where == OptsTypes.JUNK:
            self.remove_from_wish(tvshowid)
        elif where == OptsTypes.WISH:
            self.remove_from_junk(tvshowid)

    def move_to_junk(self, tvshowid: int):
        self.move_to(OptsTypes.JUNK, tvshowid)

    def move_to_wish(self, tvshowid: int):
        self.move_to(OptsTypes.WISH, tvshowid)

    def remove_from(self, where: OptsTypes, tvshowid: int):
        IDs: List[int] = self.opts.get(where.value, [])
        if tvshowid in IDs:
            IDs.remove(tvshowid)
        self.opts[where.value] = IDs

    def remove_from_junk(self, tvshowid: int):
        self.remove_from(OptsTypes.JUNK, tvshowid)

    def remove_from_wish(self, tvshowid: int):
        self.remove_from(OptsTypes.WISH, tvshowid)

    def is_in(self, where: OptsTypes, tvshowid: int) -> bool:
        IDs: List[int] = self.opts.get(where.value, [])
        return tvshowid in IDs

    def is_in_junk(self, tvshowid: int) -> bool:
        return self.is_in(OptsTypes.JUNK, tvshowid)

    def is_in_wish(self, tvshowid: int) -> bool:
        return self.is_in(OptsTypes.WISH, tvshowid)
