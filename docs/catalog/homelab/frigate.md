# Frigate (NVR with on-device AI)

Self-hosted Network Video Recorder that runs person/car/animal/package detection on the camera feed itself.

## What it does

Frigate is a self-hosted NVR (Network Video Recorder) designed to run alongside Home Assistant. It captures video from your cameras, runs AI detection (person, car, animal, package) on-device using a Coral USB stick or the CPU, and sends events to HA so you can build automations on top. No cloud required, no monthly fees.

## How to install

1. Frigate runs as a Docker container. The official docs recommend a small Linux box with a Google Coral USB accelerator.
2. Cameras connect to Frigate via RTSP. Most IP cameras support this out of the box.
3. Add the Frigate integration to Home Assistant to bring live streams + AI events into HA.

## How it works

Frigate pulls video from your cameras, decodes it locally, and runs object detection on every frame. Detected events are sent to HA as MQTT messages; HA renders them as camera tiles + automations.

## Useful links

- [Frigate homepage](https://frigate.video/) — official site
- [Frigate + Home Assistant guide](https://docs.frigate.video/integrations/home-assistant/) — official HA integration
- [Frigate hardware guide](https://docs.frigate.video/frigate/hardware/) — what box to buy
