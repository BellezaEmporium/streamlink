"""
$description Colombian hosting services for live TV channels. Not to be confused with Teveo.com.cu.
$url teveo.com.co
$type live
$region Colombia
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)

# haven't found better.
@pluginmatcher(re.compile(r"https?://teveo\.com\.co/player/(.*?)\.js"))
class TeveoCo(Plugin):
    _playlist_re = re.compile(r'"src":"(.*?)"')
    stream_schema = validate.Schema(
        validate.transform(_playlist_re.search),
        validate.any(None, validate.all(validate.get(1), validate.url()))
    )

    def _get_streams(self):
        url = self.session.http.get(self.url,schema = self.stream_schema)
        if not url:
            log.error('No URL has been found, either link is incorrect or no resource file has been given')
        return HLSStream.parse_variant_playlist(self.session, url)

__plugin__ = TeveoCo