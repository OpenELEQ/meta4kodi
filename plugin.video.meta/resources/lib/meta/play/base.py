from traceback import print_exc
from xbmcswift2 import xbmc, xbmcgui

from meta import plugin
from meta.gui import dialogs
from meta.utils.executor import execute
from meta.utils.text import to_unicode, urlencode_path, apply_parameters
from meta.library.tools import get_movie_from_library, get_episode_from_library
from meta.play.players import get_players
from meta.play.lister import Lister

from settings import SETTING_MOVIES_ENABLED_PLAYERS, SETTING_TV_ENABLED_PLAYERS
from language import get_string as _


@plugin.cached(TTL=60, cache="trakt")
def get_trakt_ids(*args, **kwargs):
    from trakt import trakt
    return trakt.find_trakt_ids(*args, **kwargs)

def active_players(media, filters={}):
    if media == "movies":
        setting = SETTING_MOVIES_ENABLED_PLAYERS
    elif media == "tvshows":
        setting = SETTING_TV_ENABLED_PLAYERS
    else:
        raise Exception("invalid parameter %s" % media)
        
    try:
        enabled = plugin.get_setting(setting)
    except:
        enabled = []
        
    return [p for p in get_players(media, filters) \
            if p.id in enabled]

def action_cancel(clear_playlist=True):
    if clear_playlist:
        xbmc.PlayList(xbmc.PLAYLIST_VIDEO).clear()
    plugin.set_resolved_url()
    xbmc.executebuiltin('Dialog.Close(okdialog, true)')    
    
def action_activate(link):
    xbmc.executebuiltin('Container.Update("%s")' % link)
    #action_cancel()
    
def action_play(item):
    #action_cancel()
    plugin.play_video(item)
    
def action_resolve(item):
    #plugin.set_resolved_url(item)
    action_play(item)
            
def get_video_link(players, params, mode, use_simple=False):
    lister = Lister()
    
    # Extend parameters
    for lang, lang_params in params.items():
        for key, value in lang_params.items():
            if isinstance(value, basestring):
                params[lang][key + "_+"] = value.replace(" ", "+")
                params[lang][key + "_-"] = value.replace(" ", "-")
                params[lang][key + "_escaped"] = value.replace(" ", "%2520")
                params[lang][key + "_escaped+"] = value.replace(" ", "%252B")
        
    pDialog = None
    selection = None
    try:
        if len(players) > 1 and use_simple:
            index = dialogs.select(_("Play with..."), [player.title for player in players])
            if index == -1:
                return None
            players = [players[index]]
            
        resolve_f = lambda p : resolve_player(p, lister, params)
        
        if len(players) > 1:
            pDialog = xbmcgui.DialogProgress()
            pDialog.create('Meta', 'Working...')
            dialogs.wait_for_dialog("progressdialog", 5)
            populator = lambda : execute(resolve_f, players, lister.stop_flag)
            selection = dialogs.select_ext(_("Play with..."), populator, len(players))
            
        else:
            result = resolve_f(players[0])
            if result:
                title, links = result
                if len(links) == 1:
                    selection = links[0]
                else:
                    index = dialogs.select(_("Play with..."), [x['label'] for x in links])
                    if index > -1:
                        selection = links[index]
            else:
                dialogs.ok(_("Error"), _("Video not found :("))
    finally:
        lister.stop()

    return selection
    
def resolve_player(player, lister, params):
    results = []
    
    for command_group in player.commands:  
        if xbmc.abortRequested or not lister.is_active():
            return
        
        command_group_results = []
        for command in command_group:
            if xbmc.abortRequested or not lister.is_active():
                return
            
            lang = command.get("language", "en")
            if not lang in params:
                continue
                
            parameters = params[lang]
            try:
                link = apply_parameters(to_unicode(command["link"]), parameters)
            except:
                print_exc()
                continue
                
            if link == "movies" and player.media == "movies":
                video = get_movie_from_library(parameters['imdb'])
                
                if video:
                    command_group_results.append(video)
            
            elif link == "tvshows" and player.media == "tvshows":
                video = get_episode_from_library(parameters['id'], parameters['season'], parameters['episode'])

                if not video:
                    video = get_episode_from_library(parameters['tmdb'], parameters['season'], parameters['episode'])

                if video:
                    command_group_results.append(video)
                    
            elif not command.get("steps"):
                command_group_results.append(
                    {
                        'label': player.title,
                        'path': urlencode_path(link),
                        'action': command.get("action", "PLAY")
                    }
                )
                
            else:
                steps = [to_unicode(step) for step in command["steps"]]
                files, dirs = lister.get(link, steps, parameters)
                if command.get("action", "PLAY") == "ACTIVATE":
                    files += dirs

                if files:
                    command_group_results += [
                        {
                            'label': f['label'],
                            'path': player.postprocess(f['path']),
                            'action': command.get("action", "PLAY")
                        } for f in files]
            
            if command_group_results:
                break

        results += command_group_results
        
    if results:
        return player.title, results
