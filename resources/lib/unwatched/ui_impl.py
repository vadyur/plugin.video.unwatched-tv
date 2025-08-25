from typing import Any, Callable, Dict, Optional
from .SeasonItem import SeasonItem
from .UnwatchedOpts import UnwatchedOpts
from .medialibrary import Unwatched, get_episodes
from vdlib.scrappers.movieapi import TMDB_Episode
from vdlib.util.log import debug


def listing_seasons_impl(tvshowid: int, unwatched_opts: UnwatchedOpts, get_url: Callable):
    uw = Unwatched(unwatched_opts)
    debug(tvshowid)
    listing = list(uw.getSeasonsListing(tvshowid))
    for item in listing:
        season: SeasonItem = item["url"]
        seasonid = season.seasonid

        episodes = get_episodes(tvshowid, season.season_number)

        if seasonid and len(episodes) == season.episode_count:
            item["url"] = f"videodb://tvshows/titles/{tvshowid}/{season.season_number}/?tvshowid={tvshowid}"
        else:
            item["url"] = get_url(action="episodes", tvshowid=tvshowid, season_number=season.season_number)
    return listing

def listing_episodes_impl(
    tvshowid: int,
    season_number: int,
    unwatched_opts: UnwatchedOpts,
    get_url: Callable
):
    from .medialibrary import find_episode
    debug(f"listing_episodes({tvshowid}, {season_number})")

    episodes = get_episodes(tvshowid, season_number)

    uw = Unwatched(unwatched_opts)
    listing = list(uw.getEpisodesListing(int(tvshowid), int(season_number)))
    debug(f"listing_episodes:\t{listing}")

    for item in listing:
        episode_tmdb: TMDB_Episode = item["url"]
        episode_kodi: Optional[Dict[str, Any]] = find_episode(episodes, episode_tmdb["episode_number"])
        if episode_kodi:
            item["url"] = episode_kodi["file"]
        else:
            item["url"] = get_url(action="episode", season_number=season_number, episode_number=episode_tmdb["episode_number"])

    return listing

