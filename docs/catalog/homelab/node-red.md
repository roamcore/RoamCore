# Node-RED (visual automations)

Visual flow-based programming for Home Assistant — drag-and-drop automations without writing YAML.

## What it does

Node-RED is a visual programming tool built around flows. You wire together nodes (events, conditions, services) on a canvas and Node-RED executes them. It's deeply integrated with Home Assistant via the official Node-RED add-on, and many RoamCore automations have a Node-RED flow equivalent.

## How to install

1. The official Home Assistant Node-RED add-on installs in a few clicks from the Add-on Store.
2. Once running, Node-RED is reachable on `http://your-ha:1880` for editing flows.
3. Pair it with Home Assistant using a long-lived access token so flows can call HA services.

## How it works

Node-RED stays running in the background. When a node fires (e.g. a state change in HA), it executes downstream nodes until the flow is done. The visual editor lets you see and modify live flows.

## Useful links

- [Node-RED](https://nodered.org/) — official site
- [HA Node-RED add-on](https://github.com/home-assistant/addons/blob/master/node-red/DOCS.md) — official install guide
- [Node-RED + HA cookbook](https://zachoweb.home.blog/2019/12/02/node-red-and-home-assistant-cookbook/) — flow examples
