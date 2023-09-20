from dataclasses import dataclass
from typing import Optional, Any


@dataclass
class SeasonItem:
    episode_count: int    # count of episodes
    season_number: int    # season number
    watched_count: int    # count of watched episodes
    seasonid: Optional[int] = None

    def merge(self, season: Any):
        assert self.season_number == season.season_number
        self.episode_count = max(self.episode_count, season.episode_count)
        self.watched_count = max(self.watched_count, season.watched_count)
        if season.seasonid:
            self.seasonid = season.seasonid

    @property
    def watched(self) -> bool:
        return self.watched_count >= self.episode_count