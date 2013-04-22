# Author: Unknown
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of Sick Beard.
#
# Sick Beard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

import urllib
import re

import generic
import sickbeard

from sickbeard import tvcache
from sickbeard import logger
from sickbeard import show_name_helpers
from sickbeard.common import Overview


class IsoHuntProvider(generic.TorrentProvider):

    def __init__(self):
        generic.TorrentProvider.__init__(self, "IsoHunt")

        self.supportsBacklog = True

        self.cache = IsoHuntCache(self)

        #use html results instead of RSS feed in order to get ratings and comments
        self.urls = {'tv_latest': "https://isohunt.com/torrents/?ihs1=5&iho1=d&iht=3&age=0",
                    'search': "https://isohunt.com/torrents/?ihq=%s",
                    'torrent': "https://ca.isohunt.com/download/%d/%d.torrent" } #torrent filename is arbitrary, id is what matters

        self.html_result_re = '<tr class="hlRow"[^>]*>.*?(?P<rating>[-+]?\d+) rating, (?P<comments>\d+) comments on torrent.*?/torrent_details/(?P<id>\d+)/.*?tab=summary["\']>(?P<title>.*?)</a>.*?<td.*?(?P<seeders>\d+)</td>.*?<td.*?(?P<leechers>\d+)</td></tr>'

    def isEnabled(self):
        return sickbeard.ISOHUNT

    def imageName(self):
        return 'isohunt.png'

    def _get_title_and_url(self, item):
        url = item.url

        if url:
            url = url.replace('&amp;','&')

        return (item.title, url)

    def _getItemsFromData(self, data):
        """
        Retrieves a list of the torrents in the data string

        Returns: the list of IsohuntTorrentItems
        """

        """ use html results instead of RSS feed in order to get ratings and comments
        HTML table row example for searching "game of thrones"
        <!-- torrent details row -->
        <tr class="hlRow" onclick="windowlocation=link11.href" onmouseover="rowOver(11)" onmouseout="rowOut(11,'#cad9ea')">
            <!-- category cell -->
            <td class="row3">TV</td>
            <!-- toggle torrent details cell and Age -->
            <td class="row3" id="row_6_11">
                <a onclick="servOC(11,'/torrent_details/467572511/game+of+thrones','',ihTri11)">
                    <img class="tog" id="ihTri11" src="https://isohunt.com/img/serp-toggle-up.gif" title="Toggle torrent details below" height="19" width="19">
                </a>3.4d
            </td>
            <td style="background: none repeat scroll 0% 0% rgb(202, 217, 234);" class="row3" id="name11">
                <a href="/torrent_details/467572511/game+of+thrones?tab=comments" style="float:right; color:green; font-weight:bold" title="+24 rating, 28 comments on torrent">
                    <!-- rating -->
                    +24<img src="/img/serp_icon_star.gif" alt="rating" style="margin-left:1px" height="12" width="12">
                    <!-- # comments -->
                    28<img src="/img/serp_icon_bubble.gif" alt="comments" style="margin-left:2px" height="10" width="10">
                </a>
                <!-- Torrent Name -->
                <a id="link11" href="/torrent_details/467572511/game+of+thrones?tab=summary"><b>Game.of.Thrones</b>.S03E01.HDTV.x264-2HD.mp4</a>
            </td>
            <!-- SIZE -->
            <td class="row3" title="1 file">385.94 MB</td>
            <!-- SEEDS -->
            <td class="row3">45449</td>
            <!-- LEECHERS -->
            <td class="row3">2650</td>
        </tr>
        """
        match = re.compile(self.html_result_re, re.DOTALL).finditer(data)
        items = []
        for torrent in match:
            title = torrent.group('title')


            # Remove various html tags from the title

            #Isohunt sometimes puts categories in ahead of titles, get rid of </br> that seperates them
            title = re.sub('</?br>', ' ', title, re.DOTALL)
            #Isohunt bolds the search term, remove <b> tags
            title = re.sub('</?b>','', title, re.DOTALL)
            #Isohunt sometimes surrounds the title with <span> tags, remove them.
            title = re.sub('</?span.*?>','', title, re.DOTALL)
            #Do not know why but SickBeard skip release with '_' in name
            title = title.replace('_','.')

            rating = str(torrent.group('rating'))
            comments = int(torrent.group('comments'))
            id = int(torrent.group('id'))
            seeders = int(torrent.group('seeders'))
            leechers = int(torrent.group('leechers'))

            url = self.urls['torrent'] % (id, id)

            logger.log(u"title: "+title, logger.DEBUG)
            logger.log(u"url: "+url, logger.DEBUG)
            logger.log(u"comments: "+str(comments), logger.DEBUG)
            logger.log(u"rating: "+str(torrent.group('rating')), logger.DEBUG)
            logger.log(u"torrent id: "+str(id), logger.DEBUG)
            logger.log(u"seeders: "+str(seeders), logger.DEBUG)
            logger.log(u"leechers: "+str(leechers), logger.DEBUG)

            item = IsohuntTorrentItem(title, id, url, rating, comments, seeders, leechers)

            items.append(item)
        return items

    def _get_season_search_strings(self, show, season=None):
        ## borrowed from thepiratebay.py, thanks mr-orange!!

        search_string = {'Episode': []}

        if not show:
            return []

        seasonEp = show.getAllEpisodes(season)

        wantedEp = [x for x in seasonEp if show.getOverview(x.status) in (Overview.WANTED, Overview.QUAL)]

        #If Every episode in Season is a wanted Episode then search for Season first
        if wantedEp == seasonEp and not show.air_by_date:
            search_string = {'Season': [], 'Episode': []}
            for show_name in set(show_name_helpers.allPossibleShowNames(show)):
                ep_string = show_name +' S%02d' % int(season) #1) ShowName SXX
                search_string['Season'].append(ep_string)

                ep_string = show_name+' Season '+str(season)+' -Ep*' #2) ShowName Season X
                search_string['Season'].append(ep_string)

        #Building the search string with the episodes we need
        for ep_obj in wantedEp:
            search_string['Episode'] += self._get_episode_search_strings(ep_obj)[0]['Episode']

        #If no Episode is needed then return an empty list
        if not search_string['Episode']:
            return []

        logger.log(u"IsoHunt Season search strings: "+repr([search_string]), logger.DEBUG)

        return [search_string]

    def _is_item_acceptable(self, item):

        #Filter unseeded torrent
        if item.seeders == 0 or not item.title:
            return False

        if not show_name_helpers.filterBadReleases(item.title):
            return False

        # Filter negatively rated torrents
        if item.rating and item.rating.startswith('-'):
            logger.log(u"IsoHunt Provider found result " + item.title + " but it has a negative rating so I'm ignoring it", logger.DEBUG)
            return False

        return True

    def _doSearch(self, search_params, show=None):

        ## borrowed from thepiratebay.py, thanks mr-orange!!

        results = []
        items = {'Season': [], 'Episode': []}

        for mode in search_params.keys():
            for search_string in search_params[mode]:

                searchURL = self.urls['search'] % urllib.quote_plus(search_string)
                logger.log(u"Search string: " + searchURL, logger.DEBUG)

                data = self.getURL(searchURL)
                if not data:
                    return []

                #Extracting torrent information from data returned by searchURL
                for curItem in self._getItemsFromData(data):


                    #Filter unseeded and poorly rated torrents
                    if self._is_item_acceptable(curItem):
                        continue

                    items[mode].append(curItem)

            #TODO: Sort by rating....???????
            #For each search mode sort all the items by seeders
            #items[mode].sort(key=lambda tup: tup[3], reverse=True)

            results += items[mode]

        return results


    def _get_episode_search_strings(self, ep_obj):
        ## borrowed from thepiratebay.py, thanks mr-orange!!
        search_string = {'Episode': []}

        if not ep_obj:
            return []

        if ep_obj.show.air_by_date:
            for show_name in set(show_name_helpers.allPossibleShowNames(ep_obj.show)):
                ep_string = show_name_helpers.sanitizeSceneName(show_name) +' '+ str(ep_obj.airdate)
                search_string['Episode'].append(ep_string)
        else:
            for show_name in set(show_name_helpers.allPossibleShowNames(ep_obj.show)):
                ep_string = show_name_helpers.sanitizeSceneName(show_name) +' '+ \
                sickbeard.config.naming_ep_type[2] % {'seasonnumber': ep_obj.season, 'episodenumber': ep_obj.episode} +' OR '+\
                sickbeard.config.naming_ep_type[0] % {'seasonnumber': ep_obj.season, 'episodenumber': ep_obj.episode} +' OR '+\
                sickbeard.config.naming_ep_type[3] % {'seasonnumber': ep_obj.season, 'episodenumber': ep_obj.episode} \

                search_string['Episode'].append(ep_string)

        logger.log(u"IsoHunt Episode " +repr([search_string]), logger.DEBUG)
        return [search_string]


#title, url, rating, comments, seeders, leecherschers = curItem
class IsohuntTorrentItem():
    title = None
    id = None
    url = None
    rating = None
    comments = None
    seeders = None
    leechers = None

    def __init__(self, title, id, url, rating, comments, seeders, leechers):
        self.title = title
        self.id = id
        self.url = url
        self.rating = rating
        self.comments =  comments
        self.seeders = seeders
        self.leechers = leechers


class IsoHuntCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll every 15 minutes max
        self.minTime = 15

    def updateCache(self):
        if not self.shouldUpdate():
            return

        url = self.provider.urls['tv_latest']
        logger.log(u"IsoHunt cache update URL: "+ url, logger.DEBUG)
        data = self.provider.getURL(url)

        # as long as the http request worked we count this as an update
        if data:
            self.setLastUpdate()
        else:
            return []

        # now that we've loaded the latest results lets delete the old cache
        logger.log(u"Clearing "+self.provider.name+" cache and updating with new information")
        self._clearCache()

        # now lets parse the data for titles and urls and add them to the cache
        for curItem in self.provider._getItemsFromData(data):
            if self.provider._is_item_acceptable(curItem):
                self._parseItem(curItem)

    def _parseItem(self, item):

        (title, url) = self.provider._get_title_and_url(item)

        if not title or not url:
            return

        logger.log(u"Adding item to cache: "+title, logger.DEBUG)

        self._addCacheEntry(title, url)


provider = IsoHuntProvider()
