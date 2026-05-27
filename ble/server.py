from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from dbus_next import BusType, Variant
from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface, dbus_property, method, PropertyAccess

from core.command_router import CommandRouter
from utils.json_utils import dumps_object


LOGGER = logging.getLogger(__name__)

APP_ROOT = "/com/pi/control"
SERVICE_PATH = f"{APP_ROOT}/service0"
COMMAND_CHARACTERISTIC_PATH = f"{SERVICE_PATH}/char0"
RESPONSE_CHARACTERISTIC_PATH = f"{SERVICE_PATH}/char1"
ADVERTISEMENT_PATH = f"{APP_ROOT}/advertisement0"

SERVICE_UUID = "7b4a9c34-9d2d-4b20-8a0e-38d66f78b001"
COMMAND_CHARACTERISTIC_UUID = "7b4a9c34-9d2d-4b20-8a0e-38d66f78b002"
RESPONSE_CHARACTERISTIC_UUID = "7b4a9c34-9d2d-4b20-8a0e-38d66f78b003"


class Application(ServiceInterface):
    def __init__(self, services: list["GattService"]):
        super().__init__("org.freedesktop.DBus.ObjectManager")
        self._services = services

    @method()
    def GetManagedObjects(self) -> "a{oa{sa{sv}}}":
        managed_objects: Dict[str, Dict[str, Dict[str, Variant]]] = {}
        for service in self._services:
            managed_objects[service.path] = {service.interface_name: service.as_dbus_properties()}
            for characteristic in service.characteristics:
                managed_objects[characteristic.path] = {characteristic.interface_name: characteristic.as_dbus_properties()}
        return managed_objects


class GattService(ServiceInterface):
    interface_name = "org.bluez.GattService1"

    def __init__(self, path: str, uuid: str, primary: bool = True) -> None:
        super().__init__(self.interface_name)
        self.path = path
        self.uuid = uuid
        self.primary = primary
        self.characteristics: list[GattCharacteristic] = []

    def as_dbus_properties(self) -> Dict[str, Variant]:
        return {
            "UUID": Variant("s", self.uuid),
            "Primary": Variant("b", self.primary),
            "Includes": Variant("ao", []),
        }

    @dbus_property(access=PropertyAccess.READ)
    def UUID(self) -> "s":
        return self.uuid

    @dbus_property(access=PropertyAccess.READ)
    def Primary(self) -> "b":
        return self.primary

    @dbus_property(access=PropertyAccess.READ)
    def Includes(self) -> "ao":
        return []


class GattCharacteristic(ServiceInterface):
    interface_name = "org.bluez.GattCharacteristic1"

    def __init__(self, path: str, uuid: str, service: GattService, flags: list[str]) -> None:
        super().__init__(self.interface_name)
        self.path = path
        self.uuid = uuid
        self.service = service
        self.flags = flags
        self._value = b""
        self._notify_enabled = False

    def as_dbus_properties(self) -> Dict[str, Variant]:
        return {
            "UUID": Variant("s", self.uuid),
            "Service": Variant("o", self.service.path),
            "Flags": Variant("as", self.flags),
            "Value": Variant("ay", self._value),
        }

    @dbus_property(access=PropertyAccess.READ)
    def UUID(self) -> "s":
        return self.uuid

    @dbus_property(access=PropertyAccess.READ)
    def Service(self) -> "o":
        return self.service.path

    @dbus_property(access=PropertyAccess.READ)
    def Flags(self) -> "as":
        return self.flags

    @dbus_property(access=PropertyAccess.READ)
    def Value(self) -> "ay":
        return self._value

    @method()
    def ReadValue(self, options: "a{sv}") -> "ay":
        return self._value

    @method()
    async def WriteValue(self, value: "ay", options: "a{sv}") -> None:
        if self.interface_name != "org.bluez.GattCharacteristic1":
            return
        self._value = bytes(value)

    @method()
    def StartNotify(self) -> None:
        self._notify_enabled = True

    @method()
    def StopNotify(self) -> None:
        self._notify_enabled = False

    async def publish(self, raw_bytes: bytes) -> None:
        self._value = raw_bytes
        self.emit_properties_changed({"Value": Variant("ay", self._value)}, [])


class CommandCharacteristic(GattCharacteristic):
    def __init__(self, path: str, service: GattService, router: CommandRouter, response_characteristic: "ResponseCharacteristic") -> None:
        super().__init__(path=path, uuid=COMMAND_CHARACTERISTIC_UUID, service=service, flags=["write", "write-without-response"])
        self._router = router
        self._response_characteristic = response_characteristic

    @method()
    async def WriteValue(self, value: "ay", options: "a{sv}") -> None:
        raw_payload = bytes(value).decode("utf-8", errors="replace")
        LOGGER.info("Incoming BLE command payload: %s", raw_payload)
        response = self._router.route_raw(raw_payload, source="ble")
        await self._response_characteristic.publish(dumps_object(response).encode("utf-8"))


class ResponseCharacteristic(GattCharacteristic):
    def __init__(self, path: str, service: GattService) -> None:
        super().__init__(path=path, uuid=RESPONSE_CHARACTERISTIC_UUID, service=service, flags=["read", "notify"])

    @method()
    async def WriteValue(self, value: "ay", options: "a{sv}") -> None:
        self._value = bytes(value)


class Advertisement(ServiceInterface):
    interface_name = "org.bluez.LEAdvertisement1"

    def __init__(self, path: str, service_uuid: str, local_name: str = "PiControl") -> None:
        super().__init__(self.interface_name)
        self.path = path
        self.service_uuid = service_uuid
        self.local_name = local_name

    def as_dbus_properties(self) -> Dict[str, Variant]:
        return {
            "Type": Variant("s", "peripheral"),
            "ServiceUUIDs": Variant("as", [self.service_uuid]),
            "LocalName": Variant("s", self.local_name),
            "Discoverable": Variant("b", True),
        }

    @dbus_property(access=PropertyAccess.READ)
    def Type(self) -> "s":
        return "peripheral"

    @dbus_property(access=PropertyAccess.READ)
    def ServiceUUIDs(self) -> "as":
        return [self.service_uuid]

    @dbus_property(access=PropertyAccess.READ)
    def LocalName(self) -> "s":
        return self.local_name

    @dbus_property(access=PropertyAccess.READ)
    def Discoverable(self) -> "b":
        return True

    @method()
    def Release(self) -> None:
        LOGGER.info("BLE advertisement released")


@dataclass(slots=True)
class PiControlBleServer:
    router: CommandRouter
    local_name: str = "PiControl"
    _bus: Optional[MessageBus] = None
    _app: Optional[Application] = None
    _service: Optional[GattService] = None
    _command_char: Optional[CommandCharacteristic] = None
    _response_char: Optional[ResponseCharacteristic] = None
    _advertisement: Optional[Advertisement] = None
    _stopped: bool = False

    async def run_forever(self) -> None:
        self._stopped = False
        self._bus = await MessageBus(bus_type=BusType.SYSTEM).connect()

        self._service = GattService(SERVICE_PATH, SERVICE_UUID, primary=True)
        self._response_char = ResponseCharacteristic(RESPONSE_CHARACTERISTIC_PATH, self._service)
        self._command_char = CommandCharacteristic(COMMAND_CHARACTERISTIC_PATH, self._service, self.router, self._response_char)
        self._service.characteristics.extend([self._command_char, self._response_char])
        self._app = Application([self._service])
        self._advertisement = Advertisement(ADVERTISEMENT_PATH, SERVICE_UUID, self.local_name)

        self._bus.export(APP_ROOT, self._app)
        self._bus.export(self._service.path, self._service)
        self._bus.export(self._command_char.path, self._command_char)
        self._bus.export(self._response_char.path, self._response_char)
        self._bus.export(self._advertisement.path, self._advertisement)

        gatt_manager = await self._get_interface("/org/bluez/hci0", "org.bluez.GattManager1")
        advertising_manager = await self._get_interface("/org/bluez/hci0", "org.bluez.LEAdvertisingManager1")

        await gatt_manager.call_register_application(APP_ROOT, {})
        await advertising_manager.call_register_advertisement(self._advertisement.path, {})
        LOGGER.info("BLE server started as %s", self.local_name)

        try:
            while not self._stopped:
                await asyncio.sleep(1)
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        self._stopped = True
        if self._bus is None:
            return
        try:
            advertising_manager = await self._get_interface("/org/bluez/hci0", "org.bluez.LEAdvertisingManager1")
            await advertising_manager.call_unregister_advertisement(self._advertisement.path if self._advertisement else ADVERTISEMENT_PATH)
        except Exception:
            LOGGER.exception("Failed to unregister BLE advertisement")
        try:
            gatt_manager = await self._get_interface("/org/bluez/hci0", "org.bluez.GattManager1")
            await gatt_manager.call_unregister_application(APP_ROOT)
        except Exception:
            LOGGER.exception("Failed to unregister BLE application")

    async def _get_interface(self, path: str, interface_name: str) -> Any:
        assert self._bus is not None
        introspection = await self._bus.introspect("org.bluez", path)
        proxy_object = self._bus.get_proxy_object("org.bluez", path, introspection)
        return proxy_object.get_interface(interface_name)
