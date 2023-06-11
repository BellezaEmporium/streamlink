import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)

@pluginmatcher(re.compile(r"https?://teveo\.com\.co/player/(.*?)\.js"))
class Teveo(Plugin):
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

__plugin__ = Teveo