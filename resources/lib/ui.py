import sys
from vdlib.scrappers.movieapi import TMDB_Episode
import xbmcplugin, xbmcgui
from simpleplugin import Plugin

from .unwatched.UnwatchedOpts import OptsTypes
from .unwatched.medialibrary import TVShowOpts, Unwatched, UnwatchedOpts
from .unwatched.SeasonItem import SeasonItem

from vdlib.kodi.simpleplugin3_suport import create_listing
from vdlib.util.log import debug

plugin = Plugin()
unwatched_opts = UnwatchedOpts()
_ = plugin.initialize_gettext()

debug("=============== enter ================")


@plugin.action()
def root(params):
    # import vsdbg; vsdbg.breakpoint()

    listing = [
        {
            "label": _("All"),
            "url": plugin.get_url(action="all"),
        },
        {
            "label": _("Wish"),
            "url": plugin.get_url(action="wish"),
        },
        {
            "label": _("Suggestions"),
            "url": plugin.get_url(action="suggestions"),
        },
        {
            "label": _("Junk"),
            "url": plugin.get_url(action="junk"),
        },
    ]
    create_listing(listing)


# @plugin.mem_cached(30)
def listing_tvshow(type: OptsTypes, uw: Unwatched, opts: TVShowOpts = TVShowOpts.ALL):
    context_menu = [OptsTypes.WISH, OptsTypes.JUNK]
    progressDlg = xbmcgui.DialogProgressBG()
    progressDlg.create(plugin.name)

    def update(label: str):
        progressDlg.update(message=label)

    listing = list(uw.getTVShowListing(type, opts, progressFn=update))
    for item in listing:
        tvshowid = int(item["url"])
        item["url"] = plugin.get_url(action="seasons", tvshowid=tvshowid)

        context_menu_out = []
        for ctx_item in context_menu:
            target: OptsTypes = ctx_item
            action = (
                "removefrom" if unwatched_opts.is_in(target, tvshowid) else "moveto"
            )
            what = _("Move to") if action == "moveto" else _("Remove from")
            where = _("Wish") if target == OptsTypes.WISH else _("Junk")
            menu_label = f'{what} "{where}"'
            command = "RunPlugin(%s)" % plugin.get_url(
                action=action, tvshowid=tvshowid, target=target
            )
            context_menu_out.append((menu_label, command))
        item["context_menu"] = context_menu_out
    return listing


def listing_tvshow_all():
    uw = Unwatched(unwatched_opts)
    return listing_tvshow(OptsTypes.ALL, uw)


def listing_tvshow_wish():
    uw = Unwatched(unwatched_opts)
    return listing_tvshow(OptsTypes.WISH, uw)


def listing_tvshow_suggestions():
    uw = Unwatched(unwatched_opts)
    return listing_tvshow(OptsTypes.WISH, uw, TVShowOpts.SUGGESTIONS)


def listing_tvshow_junk():
    uw = Unwatched(unwatched_opts)
    return listing_tvshow(OptsTypes.JUNK, uw)


@plugin.action()
def moveto(params):
    debug("=============== MOVE TO ===================")
    debug(params)

    if params["target"] == "OptsTypes.WISH":
        unwatched_opts.move_to_wish(int(params["tvshowid"]))
    if params["target"] == "OptsTypes.JUNK":
        unwatched_opts.move_to_junk(int(params["tvshowid"]))


@plugin.action()
def removefrom(params):
    debug("=============== REMOVE FROM ===================")
    debug(params)

    if params["target"] == "OptsTypes.WISH":
        unwatched_opts.remove_from_wish(int(params["tvshowid"]))
    if params["target"] == "OptsTypes.JUNK":
        unwatched_opts.remove_from_junk(int(params["tvshowid"]))


@plugin.action()
def all(params):
    xbmcplugin.setContent(int(sys.argv[1]), "tvshows")
    create_listing(listing_tvshow_all())


@plugin.action()
def wish(params):
    xbmcplugin.setContent(int(sys.argv[1]), "tvshows")
    create_listing(listing_tvshow_wish())


@plugin.action()
def suggestions(params):
    xbmcplugin.setContent(int(sys.argv[1]), "tvshows")
    create_listing(listing_tvshow_suggestions())


@plugin.action()
def junk(params):
    xbmcplugin.setContent(int(sys.argv[1]), "tvshows")
    create_listing(listing_tvshow_junk())


# @plugin.mem_cached(30)
def listing_seasons(tvshowid: int):
    uw = Unwatched(unwatched_opts)
    debug(tvshowid)
    listing = list(uw.getSeasonsListing(tvshowid))
    for item in listing:
        season: SeasonItem = item["url"]
        seasonid = season.seasonid
        if seasonid:
            item["url"] = f"videodb://tvshows/titles/{tvshowid}/{season.season_number}/?tvshowid={tvshowid}"
        else:
            item["url"] = plugin.get_url(action="episodes", tvshowid=tvshowid, season_number=season.season_number)
    return listing


@plugin.action()
def seasons(params):
    debug(params)
    xbmcplugin.setContent(int(sys.argv[1]), "tvshows")
    create_listing(listing_seasons(int(params["tvshowid"])))


def listing_episodes(tvshowid: str, season_number: str, **kvargs):
    debug(f"listing_episodes({tvshowid}, {season_number})")

    # import vsdbg; vsdbg.breakpoint()

    uw = Unwatched(unwatched_opts)
    listing = list(uw.getEpisodesListing(int(tvshowid), int(season_number)))
    debug(f"listing_episodes:\t{listing}")

    for item in listing:
        episode: TMDB_Episode = item["url"]
        item["url"] = plugin.get_url(action="episode", season_number=season_number, episode_number=episode["episode_number"])
    return listing


@plugin.action()
def episodes(params):
    debug(params)
    create_listing(listing_episodes(**params), content="episodes")


@plugin.action()
def episode(params):
    xbmcgui.Dialog().ok(plugin.name, _("Episode S{}E{} isn't in media library")
                        .format(params['season_number'], params['episode_number']))


def main():
    plugin.run()
    unwatched_opts.save()
    debug("=============== exit =================")
