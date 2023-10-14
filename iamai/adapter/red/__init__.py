"""red 协议适配器。

本适配器适配了 red 协议。
协议详情请参考: [RedProtocol](https://chrononeko.github.io/QQNTRedProtocol/) 。
"""
import os
import json
import yaml
import asyncio
import aiohttp

from uu import Error
from functools import partial
from typing import TYPE_CHECKING, Any, Dict

from iamai.adapter.utils import WebSocketAdapter
from iamai.log import logger

from .config import USER_CONFIG, Config
from .message import RedMessage
from .event import RedEvent, get_event_class, MsgType
from .exceptions import *

if TYPE_CHECKING:
    from .message import T_RedMSG  # type: ignore


__all__ = ["RedAdapter"]


class RedAdapter(WebSocketAdapter[RedEvent, Config]):
    """Red 协议适配器。"""

    name: str = "red"
    Config = Config
    config: Config

    _api_response: Dict[Any, Any]
    _api_response_cond: asyncio.Condition = None  # type: ignore
    _api_id: int = 0

    def __getattr__(self, item: Any):
        return partial(self.call_api, item)

    async def startup(self):
        """初始化适配器。"""
        self.adapter_type = "ws"
        self.host = self.config.host
        self.port = self.config.port
        self.access_token = self.config.access_token
        self.reconnect_interval = self.config.reconnect_interval
        self._api_response_cond = asyncio.Condition()
        if self.config.auto_fill:
            logger.info("Auto Detecting Chronocat Config...")
            self.chronocat_config = self.get_red_config()
            if not self.chronocat_config:
                raise Error("Can not parse or find Chronocat Config file!")
            logger.success("Succeed to Parse Chronocat Config.")
            servers = self.chronocat_config["servers"]
            red = servers[0] if servers[0]["type"] == "red" else servers[1]
            self.port = red["port"]
            self.access_token = red["token"]
        logger.debug(f"token: {self.access_token}")
        await super().startup()

    async def websocket_connect(self):
        """创建正向 WebSocket 连接。"""
        logger.info("Tying to connect to WebSocket server...")
        async with self.session.ws_connect(
            f"ws://{self.host}:{self.port}/",
            headers={"Authorization": f"Bearer {self.access_token}"}
            if self.access_token
            else None,
        ) as self.websocket:
            connect = {
                "type": "meta::connect",
                "payload": {"token": self.access_token},
            }
            await self.websocket.send_json(connect)
            await self.handle_websocket()

    async def handle_websocket_msg(self, msg: aiohttp.WSMessage):
        """处理 WebSocket 消息。"""
        msg_dict = json.loads(msg.data)
        msg_data = msg_dict["payload"]
        if self.config.show_raw: logger.info(msg_data)
        if msg_dict["type"] == "meta::connect":
            self.self_id = msg_data.get("authData").get("account")
            logger.success(
                f"WebSocket connection "
                f"from {msg_data.get('name')}({msg_data.get('version')}) Bot {self.self_id} accepted!"
            )
        elif msg_dict["type"] == "message::recv":
            msg_data = msg_data[0]
            try:
                data = {}
                if msg_data["chatType"]:
                    data["post_type"] = "message"
                    data["sub_type"] = (
                        "private" if msg_data["chatType"] == 1 else "group"
                    )
                elif (
                    msg_data["msgType"] == MsgType.system and msg_data["sendType"] == 3
                ):
                    data["post_type"] = "notice"
                    sub_type = msg_data["elements"][0]["grayTipElement"]["groupElement"]
                    if sub_type:
                        if sub_type["type"] == 1:
                            data["sub_type"] = "member_add"
                        if sub_type["type"] == 8:
                            data["sub_type"] = "member_mute"
                        if sub_type["type"] == 5:
                            data["sub_type"] = "group_name_update"
                xml_type = msg_data["elements"][0]["grayTipElement"]["xmlElement"]
                if xml_type:
                    if (
                        xml_type["subElementType"] == 12
                        and xml_type["busiType"] == "1"
                        and xml_type["busiId"] == "10145"
                    ):
                        data["sub_type"] = "member_add"
                await self.handle_red_event(data)
            except Exception as e:
                logger.error(f"Event Handled Error with {e}")
        elif msg.type == aiohttp.WSMsgType.ERROR:
            logger.error(
                f"Websocket connection closed "
                f"with exception {self.websocket.exception()!r}"
            )

    async def handle_red_event(self, msg: Dict[str, Any]):
        """处理 red 事件。

        Args:
            msg: 接收到的信息。
        """
        post_type = msg.get("post_type")
        event_type = msg.get(f"{post_type}_type")
        sub_type = msg.get("sub_type", None)
        event_class = get_event_class(post_type, event_type, sub_type)
        red_event = event_class(adapter=self, **msg)

        await self.handle_event(red_event)

    async def call_api(self, api: str, **params) -> Dict[str, Any]:
        ...

    @staticmethod
    def get_red_config():
        if not os.path.exists(USER_CONFIG):
            return None
        with open(USER_CONFIG, encoding="utf-8") as f:
            chronocat_config = yaml.safe_load(f.read())
        return chronocat_config
