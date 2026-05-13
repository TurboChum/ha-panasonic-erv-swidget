# Panasonic ERV Home Assistant Integration

This repository is a custom Home Assistant integration for Panasonic ERV devices using the Swidget local API.

## Goals

- Provide a HACS-friendly custom integration.
- Map Swidget `/api/v1/state` to Home Assistant runtime entities.
- Use `/api/v1/command` for writes and `/api/v1/device_config` for configuration.
- Implement polling, command verification, retries, and boost recovery.
- Allow a configurable device name for Home Assistant devices and entities.

## Current status

- `Objectives and definitions.md` contains the feature and design spec.
- Initial scaffold for `custom_components/panasonic_erv` is included.

## Next steps

1. Implement the integration data coordinator and entity classes.
2. Add a config flow that accepts device name and device URL.
3. Add polling, retries, and validation behavior.
4. Add optional configuration entities for rarely changed device settings.

## Notes

This repository is intended to remain private until the integration is ready for public release.
