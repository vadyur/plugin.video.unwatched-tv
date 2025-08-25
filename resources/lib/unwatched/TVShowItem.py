from .SeasonItem import SeasonItem

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional


@dataclass
class TVShowItem:
    label: str
    tvshowid: int
    imdb: str
    tmdb: str
    tvdb: str
    art: Dict[str, str]

    watched_episodes: Optional[int] = None
    episodes_count: Optional[int] = None

    @property
    def seasons(self) -> Iterable[SeasonItem]:
        from .medialibrary import get_seasons
        return get_seasons(self.tvshowid)

    def find_season(self, season_number: int) -> Optional[SeasonItem]:
        return next((x for x in self.seasons if season_number == x.season_number), None)

    @property
    def watched(self) -> bool:
        if self.watched_episodes is not None and self.watched_episodes == 0:
            return False

        if self.watched_episodes is not None and self.episodes_count is not None:
            return self.watched_episodes == self.episodes_count

        for season in self.seasons:
            if not season.watched:
                return False

        return True

    @property
    def watching(self) -> bool:
        if self.watched_episodes is not None and self.watched_episodes == 0:
            return False

        if self.watched_episodes is not None and self.episodes_count is not None:
            return self.watched_episodes < self.episodes_count

        for season in self.seasons:
            if not season.watching:
                return False

        return True
