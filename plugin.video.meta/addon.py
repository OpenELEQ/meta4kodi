#!/usr/bin/python
# -*- coding: utf-8 -*-
if __name__ == '__main__':
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'resources', 'lib'))

import os
import time
import shutil
import traceback

from xbmcswift2 import xbmcplugin

from meta import plugin
from meta.utils.properties import get_property, set_property, clear_property
from meta.gui import dialogs
from meta.play import updater
from meta.play.players import get_players, ADDON_SELECTOR 

import meta.navigation.movies
import meta.navigation.tvshows
import meta.navigation.live
import meta.navigation.lists
from meta.navigation.base import get_icon_path
from meta.play.base import active_players

import meta.library.tvshows
import meta.library.movies

from language import get_string as _
from settings import *

@plugin.route('/')
def root():
    """ Root directory """
    items = [
        {
            'label': _("Movies"),
            'path': plugin.url_for("movies"),
            'icon': get_icon_path("movies"),
        },
        {
            'label': _("TV Shows"),
            'path': plugin.url_for("tv"),
            'icon': get_icon_path("tv"),
        },
        {
            'label': _("Live"),
            'path': plugin.url_for("live"),
            'icon': get_icon_path("live"),
        },
        {
            'label': _("Lists"),
            'path': plugin.url_for("lists"),
            'icon': get_icon_path("lists"),
        }
    ]
    
    fanart = plugin.addon.getAddonInfo('fanart')
    for item in items:
        item['properties'] = {'fanart_image' : fanart}
        
    return items
    
@plugin.route('/clear_cache')
def clear_cache():
    """ Clear all caches """
    for filename in os.listdir(plugin.storage_path):
        file_path = os.path.join(plugin.storage_path, filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception, e:
            traceback.print_exc()

@plugin.route('/update_library')
def update_library():
    is_updating = get_property("updating_library")
    
    now = time.time()
    if is_updating and now - int(is_updating) < 120:
        plugin.log.debug("Skipping library update")
        return
        
    try:
        set_property("updating_library", int(now))
        meta.library.tvshows.update_library()
        meta.library.movies.update_library()
    finally:
        clear_property("updating_library")

@plugin.route('/authenticate_trakt')
def trakt_authenticate():
    from trakt import trakt
    trakt.trakt_authenticate()
    
@plugin.route('/settings/players/<media>')
def settings_set_players(media):
    playericon = get_icon_path("player")
    if media == "all":
        medias = ["movies","tvshows","live"]
        for media in medias:
            mediatype = media.replace('es','e ').replace('ws','w ').replace('all','').replace('ve','ve ')
            players = get_players(media)
            selected = [p.id for p in players]
            if selected is not None:
                if media == "movies":
                    plugin.set_setting(SETTING_MOVIES_ENABLED_PLAYERS, selected)
                elif media == "tvshows":
                    plugin.set_setting(SETTING_TV_ENABLED_PLAYERS, selected)
                elif media == "live":
                    plugin.set_setting(SETTING_LIVE_ENABLED_PLAYERS, selected)
                else:
                    raise Exception("invalid parameter %s" % media)
            plugin.notify(msg=_('All '+mediatype+'players'), title=_('Enabled'), delay=1000, image=get_icon_path("player"))
        plugin.notify(msg=_('All players'), title=_('Enabled'), delay=1000, image=get_icon_path("player"))
        return
    else:
        mediatype = media.replace('es','e ').replace('ws','w ').replace('all','').replace('ve','ve ')
        players = get_players(media)
        players = sorted(players,key=lambda player: player.clean_title.lower())
        version = xbmc.getInfoLabel('System.BuildVersion')
        if version.startswith('16') or version.startswith('17'):
            msg = "Do you want to enable all "+mediatype+"players?"
            if dialogs.yesno(_("Enable all "+mediatype+"players"), _(msg)):
                selected = [p.id for p in players]
            else:
                result = dialogs.multiselect(_("Select "+mediatype+"players to enable"), [p.clean_title for p in players])
                if result is not None:
                    selected = [players[i].id for i in result]
        else:
            selected = None
            msg = "Kodi 16 is required for multi-selection. Do you want to enable all "+mediatype+"players instead?"
            if dialogs.yesno(_("Enable all "+mediatype+"players"), _(msg)):
                selected = [p.id for p in players]
            else:
                result = dialogs.multichoice(_("Select "+mediatype+"players to enable"), [p.clean_title for p in players])
                if result is not None:
                    selected = [players[i].id for i in result]
        if selected is not None:
            if media == "movies":
                plugin.set_setting(SETTING_MOVIES_ENABLED_PLAYERS, selected)
            elif media == "tvshows":
                plugin.set_setting(SETTING_TV_ENABLED_PLAYERS, selected)
            elif media == "live":
                plugin.set_setting(SETTING_LIVE_ENABLED_PLAYERS, selected)
            else:
                raise Exception("invalid parameter %s" % media)
        plugin.notify(msg=_('All '+mediatype+'players'), title=_('Updated'), delay=1000, image=get_icon_path("player"))
    
@plugin.route('/settings/default_player/<media>')
def settings_set_default_player(media):
    players = active_players(media)
    players.insert(0, ADDON_SELECTOR)
    
    selection = dialogs.select(_("Select player"), [p.title for p in players])
    if selection >= 0:
        selected = players[selection].id
        if media == "movies":
            plugin.set_setting(SETTING_MOVIES_DEFAULT_PLAYER, selected)
        elif media == "tvshows":
            plugin.set_setting(SETTING_TV_DEFAULT_PLAYER, selected)
        else:
            raise Exception("invalid parameter %s" % media)
    
    plugin.open_settings()
    
@plugin.route('/settings/default_player_fromlib/<media>')
def settings_set_default_player_fromlib(media):
    players = active_players(media)
    players.insert(0, ADDON_SELECTOR)
    
    selection = dialogs.select(_("Select player"), [p.title for p in players])
    if selection >= 0:
        selected = players[selection].id
        if media == "movies":
            plugin.set_setting(SETTING_MOVIES_DEFAULT_PLAYER_FROM_LIBRARY, selected)
        elif media == "tvshows":
            plugin.set_setting(SETTING_TV_DEFAULT_PLAYER_FROM_LIBRARY, selected)
        else:
            raise Exception("invalid parameter %s" % media)
    
    plugin.open_settings()
    
@plugin.route('/settings/default_player_fromcontext/<media>')
def settings_set_default_player_fromcontext(media):
    players = active_players(media)
    players.insert(0, ADDON_SELECTOR)
    
    selection = dialogs.select(_("Select player"), [p.title for p in players])
    if selection >= 0:
        selected = players[selection].id
        if media == "movies":
            plugin.set_setting(SETTING_MOVIES_DEFAULT_PLAYER_FROM_CONTEXT, selected)
        elif media == "tvshows":
            plugin.set_setting(SETTING_TV_DEFAULT_PLAYER_FROM_CONTEXT, selected)
        else:
            raise Exception("invalid parameter %s" % media)
    
    plugin.open_settings()
@plugin.route('/update_players')
def update_players():
    url = plugin.get_setting(SETTING_PLAYERS_UPDATE_URL)
    if updater.update_players(url):
        plugin.notify(msg=_('Players'), title=_('Updated'), delay=1000, image=get_icon_path("player"))
    else:
        plugin.notify(msg=_('Players update'), title=_('Failed'), delay=1000, image=get_icon_path("player"))
    plugin.open_settings()
        
@plugin.route('/total')
def total():
    xbmc.executebuiltin('SetProperty(running,totalmeta,home)')
    plugin.notify(msg=_('Automated install'), title=_('Started'), delay=1000, image=get_icon_path("meta"))
    url = "https://api.github.com/repos/OpenELEQ/unofficial-meta-players-verified/zipball"
    if updater.update_players(url):
        plugin.notify(msg=_('Players'), title=_('Updated'), delay=1000, image=get_icon_path("player"))
    else:
        plugin.notify(msg=_('Players update'), title=_('Failed'), delay=1000, image=get_icon_path("player"))
    xbmc.executebuiltin("RunPlugin(plugin://plugin.video.meta/settings/players/all/)")
    movielibraryfolder = plugin.get_setting(SETTING_MOVIES_LIBRARY_FOLDER)
    try:
        meta.library.movies.auto_movie_setup(movielibraryfolder)
        plugin.notify(msg=_('Movies library folder'), title=_('Setup Done'), delay=1000, image=get_icon_path("movies"))
    except:
        plugin.notify(msg=_('Movies library folder'), title=_('Setup Failed'), delay=1000, image=get_icon_path("movies"))
    tvlibraryfolder = plugin.get_setting(SETTING_TV_LIBRARY_FOLDER)
    try:
        meta.library.tvshows.auto_tv_setup(tvlibraryfolder)
        plugin.notify(msg=_('TVShows library folder'), title=_('Setup Done'), delay=1000, image=get_icon_path("tv"))
    except:
        plugin.notify(msg=_('TVShows library folder'), title=_('Setup Failed'), delay=1000, image=get_icon_path("player"))
    xbmc.sleep(5000)
    while xbmc.getCondVisibility("Window.IsActive(dialoginfo)"):
        if not xbmc.getCondVisibility("Window.IsActive(dialoginfo)"):
            break
    plugin.notify(msg=_('Automated install'), title=_('Completed'), delay=5000, image=get_icon_path("meta"))
    xbmc.executebuiltin('ClearProperty(running,home)')
#$INFO[Window(home).Property(totalmeta)]   xbmc.getInfoLabel('Window(home).Property(totalmeta)')

#########   Main    #########

def main():
    if '/movies' in sys.argv[0]:
        xbmcplugin.setContent(int(sys.argv[1]), 'movies')
    elif '/tv' in sys.argv[0]:
        xbmcplugin.setContent(int(sys.argv[1]), 'tvshows')
    plugin.run()

if __name__ == '__main__':
    main()
