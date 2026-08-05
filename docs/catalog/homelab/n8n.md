# n8n (workflow automation)

Self-hosted workflow tool — chain services, schedule tasks, and glue systems together without writing glue code.

## What it does

n8n is a self-hosted workflow automation tool. You build "flows" by connecting nodes (HTTP requests, MQTT, Home Assistant, Discord, etc.) and n8n runs them on a schedule or in response to a webhook. It's the middle layer between your van's sensors and the outside world.

## How to install

1. Install n8n on the same machine as Home Assistant, or on a separate small box in the van.
2. The official n8n Docker image is the simplest path. A single `docker run` is enough.
3. Make n8n reachable on the van's LAN (port 5678 by default) and you can edit flows from any device.

## How it works

n8n runs as a long-lived service. When a flow fires (on a schedule, a webhook, or an MQTT event), it executes the nodes in order and passes data between them.

## Useful links

- [n8n.io](https://n8n.io/) — official site
- [n8n Docker install](https://docs.n8n.io/hosting/installation/docker/) — the easy path
- [n8n + Home Assistant guide](https://n8n.io/integrations/home-assistant/) — connect flows to HA
