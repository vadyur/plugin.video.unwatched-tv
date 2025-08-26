from datetime import datetime as dt
from enum import Enum
import time

from typing import Any, Callable, Dict, Iterable, List, Optional

from vdlib.torrspy.detect import update_video_info_from_tmdb

from .SeasonItem import SeasonItem
from .TVShowItem import TVShowItem
from .UnwatchedOpts import OptsTypes, UnwatchedOpts

from vdlib.kodi.jsonrpc_requests import VideoLibrary
from vdlib.scrappers.movieapi import TMDB_API

from vdlib.util.caching import cached, mem_cached

@cached(duration=60)
def get_tvshow_from_tmdb(tmdb_id: str) -> TMDB_API:
    tmdb = TMDB_API(tmdb_id=tmdb_id, type="tv", append_to_response="season")
    return tmdb


@cached(duration=60)
def get_episodes_from_tmdb(tmdb_id: str, season_number: int):
    tmdb = TMDB_API(
        tmdb_id=tmdb_id, type="tv", append_to_response=f"season/{season_number}"
    )
    return tmdb.episodes(season_number)


def update_tvshow_in_video_library(show: Dict[str, Any]):
    tmdb = show.get("uniqueid", {}).get("tmdb", "")
    if tmdb:
        params = { key: show[key] for key in ["tvshowid", "uniqueid"] }
        VideoLibrary.SetTVShowDetails(**params)


def update_video_info_if_need(show: Dict[str, Any]):
    if "uniqueid" not in show:
        update_video_info_from_tmdb(show)
        update_tvshow_in_video_library(show)


def get_tvshows() -> Iterable[TVShowItem]:
    @mem_cached(duration="10s")
    def get_tvshows_cached():
        return VideoLibrary.GetTVShows(
            properties=[
                "imdbnumber",
                "uniqueid",
                "art",
                "title",
                "year",
                "originaltitle",
                "watchedepisodes",
                "episode"
            ])
    result = get_tvshows_cached()

    for show in result["tvshows"]:
        uniqueid: Dict[str, str] = show.get("uniqueid", {})
        tmdb = uniqueid.get("tmdb", "")
        update_video_info_if_need(show)
        if tmdb:
            yield TVShowItem(
                label=show["label"],
                tvshowid=show["tvshowid"],
                imdb=uniqueid.get("imdb", ""),
                tmdb=tmdb,
                tvdb=uniqueid.get("tvdb", ""),
                art=show["art"],
                watched_episodes=show["watchedepisodes"],
                episodes_count=show["episode"])


@mem_cached(duration="10s")
def get_tvshow_details(tvshow_id: int) -> Dict[str, Any]:
    result: Any = VideoLibrary.GetTVShowDetails(
        tvshowid=tvshow_id,
        properties=[
            "title",
            "genre",
            "year",
            "rating",
            "plot",
            "file",
            "studio",
            "mpaa",
            "cast",
            "premiered",
            "originaltitle",
            "sorttitle",
            "runtime",
        ],
    )
    return result.get("tvshowdetails", {})


@mem_cached(duration="10s")
def get_poster(art: Dict) -> str:
    return art.get("poster", art.get("tvshow.poster", ""))


def get_seasons(tvshow_id: int) -> Iterable[SeasonItem]:
    @mem_cached(duration="10s")
    def get_seasons_cached():
        return VideoLibrary.GetSeasons(
            tvshowid=tvshow_id,
            properties=["season", "watchedepisodes", "episode", "showtitle", "art"],
        )
    result = get_seasons_cached()

    for season in result["seasons"]:
        yield SeasonItem(
            episode_count=season["episode"],
            season_number=season["season"],
            watched_count=season["watchedepisodes"],
            seasonid=season["seasonid"],
            poster=get_poster(season["art"]),
        )

def get_episodes(tvshow_id: int, season_number: int):
    result = VideoLibrary.GetEpisodes(
        tvshowid=tvshow_id,
        season=season_number,
        properties=["title", "file", "episode"],
    )
    return result.get("episodes", [])

def find_season(seasons, season_number: int) -> Optional[SeasonItem]:
    return next((x for x in seasons if season_number == x.season_number), None)

def find_episode(episodes: List[Dict[str, Any]], episode_number: int) -> Optional[Dict[str, Any]]:
    return next((x for x in episodes if episode_number == x["episode"]), None)

def strptime(string_date, format="%Y-%m-%d"):
    try:
        return dt.strptime(string_date, format)
    except TypeError:
        return dt(*(time.strptime(string_date, format)[0:6]))


def is_aired(date: str) -> bool:
    try:
        aired = strptime(date, "%Y-%m-%d")
        now = dt.now()
        return aired < now
    except TypeError:
        return False


class TVShowOpts(Enum):
    SUGGESTIONS = "SUGGESTIONS"
    ALL = "all"


class TVShowItemTMDB(TVShowItem):
    def __init__(self, tvshow: TVShowItem):
        for key, value in tvshow.__dict__.items():
            setattr(self, key, value)

        self._seasons = None
        self._source = tvshow

        self._tmdb_api = get_tvshow_from_tmdb(self.tmdb)
        self.episodes_count = self.get_aired_episodes_count() #_tmdb_api.tmdb_data["number_of_episodes"]

    def get_aired_episodes_count(self) -> int:
        tmdb_data = self._tmdb_api.tmdb_data
        last_aired_episode = tmdb_data["last_episode_to_air"]
        result = 0
        for season in tmdb_data["seasons"]:
            if season["season_number"] == 0:
                continue
            if season["season_number"] == last_aired_episode["season_number"]:
                result += last_aired_episode["episode_number"]
                break
            else:
                result += season["episode_count"]
        return result

    def merge_seasons(self, tmdb_seasons: List[SeasonItem]):
        for season in tmdb_seasons:
            library_season = self.find_season(season.season_number)
            if library_season:
                season.merge(library_season)

        self._seasons = tmdb_seasons

    def process_seasons(self):
        seasons: Any = self._tmdb_api.tmdb_data["seasons"]
        def filterAired(season: Dict) -> bool:
            return is_aired(season["air_date"]) and season["season_number"] != 0
        aired_seasons = filter(filterAired, seasons)
        if isinstance(self._seasons, list):
            out_seasons: list[SeasonItem] = []
            for season in aired_seasons:
                poster_path = season["poster_path"]
                out_seasons.append(
                    SeasonItem(
                        episode_count=season["episode_count"],
                        season_number=season["season_number"],
                        overview=season["overview"],
                        poster=f"https://image.tmdb.org/t/p/original{poster_path}",
                    )
                )
            self.merge_seasons(out_seasons)


    @property
    def seasons(self) -> Iterable[SeasonItem]:
        if self._seasons is None:
            self._seasons = list(self._source.seasons)
            self.process_seasons()
        return self._seasons

class Unwatched(object):
    def __init__(self, opts: UnwatchedOpts) -> None:
        self.opts = opts

    @property
    def tvshows(self) -> Iterable[TVShowItem]:
        return get_tvshows()

    def find_tvshow(self, tvshowid: int) -> Optional[TVShowItem]:
        return next((x for x in self.tvshows if tvshowid == x.tvshowid), None)

    def getTVShowListing(
        self,
        type: OptsTypes = OptsTypes.ALL,
        opts: TVShowOpts = TVShowOpts.ALL,
        progressFn: Optional[Callable] = None,
    ) -> Iterable[dict]:
        def tvshowListItem(tvshow: TVShowItemTMDB):
            video_info = get_tvshow_details(tvshow.tvshowid)
            video_info["playcount"] = int(tvshow.watched)
            video_info["mediatype"] = "tvshow"
            video_info["dbid"] = tvshow.tvshowid

            default_icon = "image://DefaultFolder.png/"
            icon = default_icon
            if (
                opts == TVShowOpts.SUGGESTIONS
                and tvshow.art.get("icon") == default_icon
            ):
                icon = tvshow.art.get("poster", default_icon)
                tvshow.art["icon"] = icon

            if progressFn:
                progressFn(tvshow.label)

            return {
                "label": tvshow.label,
                "info": {"video": video_info},
                "icon": icon,
                "thumb": icon,
                "art": tvshow.art,
                "url": tvshow.tvshowid,
            }

        watchingIds = set()
        if opts == TVShowOpts.SUGGESTIONS:
            for tvshow in self.tvshows:
                if self.opts.is_in_junk(tvshow.tvshowid):
                    continue
                tvshow_tmdb = TVShowItemTMDB(tvshow)
                if not tvshow_tmdb.watching:
                    continue

                watchingIds.add(tvshow.tvshowid)
                yield tvshowListItem(tvshow_tmdb)

        for tvshow in self.tvshows:
            if tvshow.tvshowid in watchingIds:
                continue
            if type == OptsTypes.WISH and not self.opts.is_in_wish(tvshow.tvshowid):
                continue
            if type == OptsTypes.JUNK and not self.opts.is_in_junk(tvshow.tvshowid):
                continue
            if type != OptsTypes.JUNK and self.opts.is_in_junk(tvshow.tvshowid):
                continue
            tvshow_tmdb = TVShowItemTMDB(tvshow)
            if opts == TVShowOpts.SUGGESTIONS and tvshow_tmdb.watched:
                continue

            yield tvshowListItem(tvshow_tmdb)

    def getSeasonsListing(self, tvshowid: int) -> Iterable[dict]:
        tvshow = self.find_tvshow(tvshowid)
        if tvshow:
            tvshow_tmdb = TVShowItemTMDB(tvshow)
            for season in tvshow_tmdb.seasons:
                art = tvshow_tmdb.art.copy()
                if season.poster:
                    art.update({"poster": season.poster})
                yield {
                    "label": f"Сезон {season.season_number}",
                    "info": {
                        "video": {
                            "playcount": int(season.watched),
                            "plot": season.overview,
                            "mediatype": "season",
                        }
                    },
                    "art": art,
                    "url": season,
                }

    def getEpisodesListing(self, tvshowid: int, season_number: int):
        tvshow: Optional[TVShowItem] = self.find_tvshow(tvshowid)
        if tvshow:
            show_video_info = get_tvshow_details(tvshowid)

            episodes = get_episodes_from_tmdb(tvshow.tmdb, season_number=season_number)
            for episode in episodes:
                art = tvshow.art.copy()
                thumb = f"https://image.tmdb.org/t/p/w780{episode['still_path']}"
                art.update(
                    {
                        "icon": thumb,
                        "thumb": thumb,
                        "landscape": thumb,
                        # "poster": thumb
                    }
                )

                video_info = show_video_info.copy()
                video_info.update(
                    {
                        "file": "",
                        "plot": episode["overview"],
                        "firstaired": episode["air_date"],
                        "label": episode["name"],
                        "title": episode["name"],
                        "rating": episode["vote_average"],
                        "season": season_number,
                        "episode": episode["episode_number"],
                        "showtitle": tvshow.label,
                        # "cast",
                        "tvshowid": tvshowid,
                        "mediatype": "episode",
                    }
                )
                stream_info = (
                    {"video": {"duration": episode["runtime"] * 60}}
                    if episode["runtime"]
                    else {}
                )
                yield {
                    "label": episode["name"],
                    "info": {"video": video_info},
                    "art": art,
                    "stream_info": stream_info,
                    "url": episode,
                    "is_folder": False,
                    "is_playable": True,
                }
