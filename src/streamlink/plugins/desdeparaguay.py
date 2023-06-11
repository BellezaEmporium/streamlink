import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"""
    https?://www\.desdepylabs\.com/External/tvaccion/(?P<channel_name>[^/&?]+)
""", re.VERBOSE))
class DesdePyLabs(Plugin):
    _re_hls = re.compile(r"""src\s*=\s*(["'])(?P<hls_url>https?://.*?\.m3u8.*?)\1""")

    def _get_streams(self):
        channel = self.match.group("channel_name")
        _hls_url = "https://www.desdepylabs.com/external/tvaccionmov/" + channel

        # unprotected HLS endpoint
        result = self.session.http.get(_hls_url, schema=validate.Schema(
            validate.transform(self._re_hls.search),
            validate.get("hls_url")
        ))
        # Puede funcionar...
        if result:
            if channel == "venusmedia":
                hls_url = result.replace("_int_alta", "")
            else:
                hls_url = result.replace("_int", "_py")
        else:
            log.error("Not a correct 'pylabs' iframe")
            return

        return {"live": HLSStream(self.session, hls_url)}


__plugin__ = DesdePyLabs
