import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)

@pluginmatcher(re.compile(r'''https?://megavision\.univtec\.com/api/live/list_channels\?cname=(?P<channel>[a-z0-9]+)'''))
class MegaVision(Plugin):
    CHANNEL_MAP = {
        #Channels
        "canal19": 0,
        "canal21": 1,
        #Radios
        "fuego": 2,
        "corazon": 3,
        "lasabrosa": 4,
        "lalibertad": 5,
        "sonsomix": 6,
        "jiboa": 7,
    }

    _channelname_re = re.compile(r"""(?P<channel_id>{.+})""")
    def _get_streams(self):
        res = self.session.http.get(self.url).json()
        if not res:
            log.debug("No data found. Blocked ?")
        channel = self.match.groupdict().get("channel")
        if channel not in self.CHANNEL_MAP:
            log.error(f"Unknown channel: {channel}")
            return
        id = self.CHANNEL_MAP.get(channel)
        stream_info = res[id]
        m3u8_url = stream_info.get("HLSStream").get("url")
        if m3u8_url:
            yield from HLSStream.parse_variant_playlist(self.session, m3u8_url).items()
        else:
            log.debug("Unable to find URL.")

__plugin__ = MegaVision