from datetime import datetime as dt
from enum import Enum
import time

from typing import Any, Callable, Dict, Iterable, List, Optional  # , Protocol

from .SeasonItem import SeasonItem
from .TVShowItem import TVShowItem
from .UnwatchedOpts import OptsTypes, UnwatchedOpts

from vdlib.kodi.jsonrpc_requests import VideoLibrary
from vdlib.scrappers.movieapi import TMDB_API


def get_tvshow_from_tmdb(tmdb_id: str) -> TMDB_API:
    tmdb = TMDB_API(tmdb_id=tmdb_id, type="tv", append_to_response="season")
    return tmdb


def get_episodes_from_tmdb(tmdb_id: str, season_number: int):
    tmdb = TMDB_API(
        tmdb_id=tmdb_id, type="tv", append_to_response=f"season/{season_number}"
    )
    return tmdb.episodes(season_number)


def get_tvshows() -> Iterable[TVShowItem]:
    result = VideoLibrary.GetTVShows(properties=["imdbnumber", "uniqueid", "art"])
    for show in result["tvshows"]:
        uniqueid: dict[str, str] = show["uniqueid"]
        yield TVShowItem(
            label=show["label"],
            tvshowid=show["tvshowid"],
            imdb=uniqueid["imdb"],
            tmdb=uniqueid["tmdb"],
            tvdb=uniqueid["tvdb"],
            art=show["art"],
        )


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


def get_poster(art: Dict) -> str:
    return art.get("poster", art.get("tvshow.poster", ""))


def get_seasons(tvshow_id: int) -> Iterable[SeasonItem]:
    result = VideoLibrary.GetSeasons(
        tvshowid=tvshow_id,
        properties=["season", "watchedepisodes", "episode", "showtitle", "art"],
    )

    for season in result["seasons"]:
        yield SeasonItem(
            episode_count=season["episode"],
            season_number=season["season"],
            watched_count=season["watchedepisodes"],
            seasonid=season["seasonid"],
            poster=get_poster(season["art"]),
        )


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


class Unwatched(object):
    def __init__(self, opts: UnwatchedOpts) -> None:
        def init_seasons(tvshow: TVShowItem):
            tvshow.seasons = list(get_seasons(tvshow.tvshowid))

        def init_tvshows() -> List[TVShowItem]:
            tvshows = list(get_tvshows())
            for tvshow in tvshows:
                init_seasons(tvshow)
            return tvshows

        # init members
        self.tvshows = init_tvshows()
        self.opts = opts

    def find_tvshow(self, tvshowid: int) -> Optional[TVShowItem]:
        return next((x for x in self.tvshows if tvshowid == x.tvshowid), None)

    def process_tmdb(self, tvshow: TVShowItem):
        tmdb_data: TMDB_API = get_tvshow_from_tmdb(tvshow.tmdb)
        seasons: Any = tmdb_data.tmdb_data["seasons"]
        def filterFn(season: Dict) -> bool:
            return is_aired(season["air_date"]) and season["season_number"] != 0
        filtered_seasons = list(filter(filterFn, seasons))
        if len(filtered_seasons) > len(tvshow.seasons):
            out_seasons: list[SeasonItem] = []
            for season in filtered_seasons:
                poster_path = season["poster_path"]
                out_seasons.append(
                    SeasonItem(
                        episode_count=season["episode_count"],
                        season_number=season["season_number"],
                        watched_count=0,
                        overview=season["overview"],
                        poster=f"https://image.tmdb.org/t/p/original{poster_path}",
                    )
                )
            self.merge_seasons(tvshow, out_seasons)

    def merge_seasons(self, tvshow: TVShowItem, tmdb_seasons: List[SeasonItem]):
        for season in tmdb_seasons:
            library_season = tvshow.find_season(season.season_number)
            if library_season:
                season.merge(library_season)

        tvshow.seasons = tmdb_seasons

    def getTVShowListing(
        self,
        type: OptsTypes = OptsTypes.ALL,
        opts: TVShowOpts = TVShowOpts.ALL,
        progressFn: Optional[Callable] = None,
    ) -> Iterable[dict]:
        def tvshowListItem(tvshow: TVShowItem):
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
                if not tvshow.watching:
                    continue

                watchingIds.add(tvshow.tvshowid)
                yield tvshowListItem(tvshow)

        for tvshow in self.tvshows:
            if tvshow.tvshowid in watchingIds:
                continue
            if type == OptsTypes.WISH and not self.opts.is_in_wish(tvshow.tvshowid):
                continue
            if type == OptsTypes.JUNK and not self.opts.is_in_junk(tvshow.tvshowid):
                continue
            if type != OptsTypes.JUNK and self.opts.is_in_junk(tvshow.tvshowid):
                continue

            self.process_tmdb(tvshow)
            if opts == TVShowOpts.SUGGESTIONS and tvshow.watched:
                continue

            yield tvshowListItem(tvshow)

    def getSeasonsListing(self, tvshowid: int) -> Iterable[dict]:
        tvshow = self.find_tvshow(tvshowid)
        if tvshow:
            self.process_tmdb(tvshow)
            for season in tvshow.seasons:
                art = tvshow.art.copy()
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
