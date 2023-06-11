import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate, useragents
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)

@pluginmatcher(re.compile(r"""
    https?://playback\.dacast\.com/content/access?
""", re.VERBOSE))

class DaCast(Plugin):
    def _get_streams(self):
        self.session.http.headers = {
            'User-Agent': useragents.FIREFOX
        }
        hls_url = self.session.http.get(self.url, schema=validate.Schema(
                validate.parse_json(),
                {"hls": str},
                validate.get("hls")
        ))
        if not hls_url:
            log.error("Stream is either offline, or contentID is incorrect")
            return

        return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = DaCast