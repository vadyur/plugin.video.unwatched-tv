from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class SeasonItem:
    episode_count: int                      # count of episodes
    season_number: int                      # season number
    watched_count: Optional[int] = None     # count of watched episodes
    seasonid: Optional[int] = None
    overview: str = ''
    poster: str = ''

    def merge(self, season: "SeasonItem"):
        assert self.season_number == season.season_number
        self.episode_count = max(self.episode_count, season.episode_count)
        self.watched_count = max(self.watched_count or 0, season.watched_count or 0)
        if season.seasonid:
            self.seasonid = season.seasonid
        if (season.overview):
            self.overview = season.overview
        if (season.poster):
            self.poster = season.poster

    @property
    def watched(self) -> bool:
        if self.seasonid is None:
            return False
        assert self.watched_count is not None
        return self.watched_count >= self.episode_count

    @property
    def watching(self) -> bool:
        if self.seasonid is None:
            return False
        assert self.watched_count is not None
        return self.watched_count > 0 and self.watched_count < self.episode_count