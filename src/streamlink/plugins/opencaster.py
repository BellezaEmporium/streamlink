import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)

@pluginmatcher(re.compile(r"""
    https?://(?:\w+\.)?opencaster\.com/(?P<channel_name>[\w-])
""", re.VERBOSE))

class OpenCaster(Plugin):
    _re_hls = re.compile(r"""source\s*:\s*(["'])(?P<hls_url>https?://.*?\.m3u8.*?)\1""")
    def _get_streams(self):
        self.session.http.headers.update({"Origin": "https://www.opencaster.com"})
        hls_url = self.session.http.get(self.url, schema=validate.Schema(
                validate.transform(self._re_hls.search),
                validate.any(None, validate.get("hls_url"))
        ))
        if not hls_url:
            log.error("Not a correct 'opencaster' iframe")
            return

        return {"live": HLSStream(self.session, hls_url)}


__plugin__ = OpenCaster