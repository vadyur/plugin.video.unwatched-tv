from .SeasonItem import SeasonItem

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TVShowItem:
    label: str
    tvshowid: int
    imdb: str
    tmdb: str
    tvdb: str
    art: Dict[str, str]
    seasons: List[SeasonItem] = field(default_factory=list)

    def find_season(self, season_number: int) -> Optional[SeasonItem]:
        return next((x for x in self.seasons if season_number == x.season_number), None)

    @property
    def watched(self) -> bool:
        for season in self.seasons:
            if not season.watched:
                return False
        return True