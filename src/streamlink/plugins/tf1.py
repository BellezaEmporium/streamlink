"""
$description French live TV channels from TF1 Group, including LCI and TF1.
$url tf1.fr
$url tf1info.fr
$url lci.fr
$type live
$region France
$account Required on tf1.fr
"""

import json
import logging
import re

from streamlink.plugin import Plugin, PluginError, pluginargument, pluginmatcher
from streamlink.plugin.api import useragents, validate
from streamlink.plugin.plugin import pluginargument
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"""
    https?://(?:www\.)?
    (?:
        tf1\.fr/(?:
            (?P<live>[\w-]+)/direct/?
            |
            stream/(?P<stream>[\w-]+)
        )
        |
        (?P<lci>tf1info|lci)\.fr/direct/?
    )
""", re.VERBOSE))
@pluginargument(
    "email",
    requires=["password"],
    metavar="EMAIL",
    help="The email address used to register with tf1.fr.",
)
@pluginargument(
    "password",
    sensitive=True,
    metavar="PASSWORD",
    help="A tf1.fr account password to use with --tf1-username.",
)
@pluginargument(
    "purge-credentials",
    action="store_true",
    help="Purge cached tf1.fr credentials to initiate a new session and reauthenticate.",
)
class TF1(Plugin):
    _URL_API = "https://mediainfo.tf1.fr/mediainfocombo/{channel_id}"
    _URL_LOGIN = "https://compte.tf1.fr/accounts.login"
    _URL_TOKEN = "https://www.tf1.fr/token/gigya/web"
    _API_KEY = "3_hWgJdARhz_7l1oOp3a8BDLoR9cuWZpUaKG4aqF7gum9_iK3uTZ2VlDBl8ANf8FVk"
    # Gigya GDPR consent IDs
    _CONSENT_IDS = ["4", "10001", "10003", "10005", "10007", "10009", "10011", "10013", "10015", "10017", "10019"]

    _CACHE_KEY_USER_TOKEN = "token"

    def _login(self, login_id, password):
        status, *login_data = self.session.http.post(
            url=self._URL_LOGIN,
            data={
                "loginID": login_id,
                "password": password,
                "APIKey": self._API_KEY,
                "includeUserInfo": "true",
            },
            schema=validate.Schema(
                validate.parse_json(),
                validate.any(
                    validate.all(
                        {
                            "errorCode": 0,
                            "UID": str,
                            "UIDSignature": str,
                            "signatureTimestamp": str,
                        },
                        validate.union_get("UID", "UIDSignature", "signatureTimestamp"),
                        validate.transform(lambda data: ("success", *data)),
                    ),
                    validate.all(
                        {
                            "errorCode": int,
                            "errorDetails": str,
                        },
                        validate.union_get("errorCode", "errorDetails"),
                        validate.transform(lambda data: ("failure", *data)),
                    ),
                ),
            ),
        )

        if status != "success":
            error_code, error_details = login_data
            raise PluginError(f"{error_code=} - {error_details or 'Unknown error'}")

        uid, uid_signature, signature_timestamp = login_data
        log.debug(f"{uid=} {uid_signature=} {signature_timestamp=}")

        return self.session.http.post(
            url=self._URL_TOKEN,
            json={
                "uid": uid,
                "signature": uid_signature,
                "timestamp": int(signature_timestamp),
                "consent_ids": self._CONSENT_IDS,
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "token": str,
                },
                validate.get("token"),
            ),
        )

    def _get_channel(self):
        if self.match["live"]:
            channel = self.match["live"]
            channel_id = f"L_{channel.upper()}"
        elif self.match["lci"]:
            channel = "LCI"
            channel_id = "L_LCI"
        elif self.match["stream"]:
            channel = self.match["stream"]
            channel_id = f"L_FAST_v2l-{channel}"
        else:  # pragma: no cover
            raise PluginError("Invalid channel")

        return channel, channel_id

    def _api_call(self, channel_id, user_token):
        headers = {
            # forces HLS streams
            "User-Agent": useragents.IPHONE,
        }
        if user_token:
            headers["Authorization"] = f"Bearer {user_token}"

        return self.session.http.get(
            self._URL_API.format(channel_id=channel_id),
            params={
                "context": "MYTF1",
                "pver": "5015000",
            },
            headers=headers,
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "delivery": validate.any(
                        validate.all(
                            {
                                "code": 200,
                                "format": "hls",
                                "url": validate.url(),
                            },
                            validate.union_get("code", "url"),
                        ),
                        validate.all(
                            {
                                "code": int,
                                "error": str,
                            },
                            validate.union_get("code", "error"),
                        ),
                    ),
                },
                validate.get("delivery"),
            ),
        )
    
    def login(self, username, password):
        """
        Create session using Gigya's API for TF1.
        :return: Whether authentication was successful
        :rtype: bool
        """

        def auth_check():
            res = self.session.http.post(
            self.auth_url,
            data=dict(
                loginID=username,
                password=password,
                APIKey=self.gigya_api_key,
                includeUserInfo="true"
            ),
            headers={"Referer": self.url, "User-Agent": useragents.IPHONE})

            # If TF1 login is successful, get Gigya token.
            if res.status_code == 200:
                # make the session request to get the correct cookies
                session_res = self.session.http.post(
                    self.session_url,
                    data=json.dumps({
                        "uid": res.json()['userInfo']['UID'],
                        "signature": res.json()['userInfo']['UIDSignature'],
                        "timestamp": int(res.json()['userInfo']['signatureTimestamp']),
                        "consent_ids": ["1", "2", "3", "4", "10001", "10003", "10005", "10007", "10013", "10015", "10017", "10019", "10009", "10011", "13002", "13001", "10004", "10014", "10016", "10018", "10020", "10010", "10012", "10006", "10008"]
                    })
                )
                if session_res.status_code == 200:
                    self.user_token = session_res.json()['token']
                    return True
                else:
                    return False
            else:
                return False

        
        if auth_check() == True:
            log.debug("Already authenticated, skipping authentication")
            return True
        else:
            return False

    def _get_streams(self):
        if not self.get_option("username"):
            log.error(
                "In order to access your content, TF1 requires an account you must login with, using "
                + "--tf1-username and --tf1-password",
            )
            return
        if not self.login(self.get_option("username"), self.get_option("password")):
            log.error(
                "Could not authenticate, check your username and password.")
            return

        channel, channel_id = self._get_channel()
        log.debug(f"Found channel {channel} ({channel_id})")

        if self.get_option("purge-credentials"):
            log.info("Removing cached user-authentication token...")
            self.cache.set(self._CACHE_KEY_USER_TOKEN, None, 0)
            user_token = None
        else:
            user_token = self.cache.get(self._CACHE_KEY_USER_TOKEN)

        if (
            not user_token
            and (login_email := self.get_option("email"))
            and (login_password := self.get_option("password"))
        ):
            log.info("Acquiring new user-authentication token...")
            user_token = self._login(login_email, login_password)
            self.cache.set(self._CACHE_KEY_USER_TOKEN, user_token)

        code, data = self._api_call(channel_id, user_token)
        if code != 200:
            log.error(data)
            return

        return HLSStream.parse_variant_playlist(self.session, data)


__plugin__ = TF1
