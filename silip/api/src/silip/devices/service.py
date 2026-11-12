"""Installation use cases."""

from silip.devices.domain import DeviceRegistration, DeviceRegistry, DeviceSetup, RegistryError


def register(request: DeviceRegistration, registry: DeviceRegistry) -> DeviceSetup:
    if not request.consent_confirmed:
        raise RegistryError("Confirm household consent before registration")
    if request.sin_hash == "0" * 64:
        raise RegistryError("Replace the placeholder household hash")
    return registry.register(request)
