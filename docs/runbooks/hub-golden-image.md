# Hub golden image

Your Hub is a small computer that runs your dashboard. The golden image is the exact, known-good version of that computer's software, captured as a single file. If your Hub ever has to be replaced or restored, you flash this file and everything comes back the way it was.

## §1 What this is

The golden image is one file. That file is everything your Hub needs to start: the operating system, the dashboard, the Victron link, the offline map, every connection you have set up. When you flash it, the Hub boots and shows your dashboard the same way it did when the image was last built.

You do not need to know how it was built. If your Hub stops working for any reason — a power surge, a failed update, a card that died — flashing the golden image brings it back. The image is updated whenever RoamCore itself changes in a way that affects the Hub (new version of the dashboard, new feature, new supported device). Most weeks that does not happen, so most weeks you do not need to think about the image at all.

## §2 When to rebuild it

The image gets rebuilt when something inside the Hub changes in a way that matters to you: a new version of RoamCore, a new supported device, a new rule template, a bug fix that affects what you see on the dashboard. The RoamCore team rebuilds the image whenever one of those things ships, and you get the new image the same way you got the last one — your Hub tells you an update is available, and you flash it.

You do not need to rebuild it yourself for normal use. You only need to build a fresh image if you are a Hub maker, a release engineer, or someone who needs to capture a custom version of the Hub (for example, with extra connections pre-wired for a specific van build).

## §3 How to build it

`bash scripts/build/hub-golden-image.sh`

If you are running this on a normal computer, the script tells you what it is doing as it goes — it checks your tools, reads the build manifest, downloads the base image, checks the download is correct, and either runs the bake (on a Linux computer with Docker installed) or tells you clearly that the bake did not happen here and what the next step would be on a real build host.

You only need Docker installed if you actually want to produce the image file on your computer. If you just want to check the build manifest and the base image are still healthy, you can run the script on any computer with curl and sha256sum installed.

## §4 How to verify it

The verifier (the smoke check) tells you, in plain English, whether the build script + manifest + their cross-references are healthy. A green output means the foundation is ready; a red output names the exact thing that needs attention. If the verifier is red on your computer, the build pipeline needs a fix before you ship a new Hub — paste the red line into the support thread and someone will help.

If you want to check the image file itself once it has been built (on the build host), the script prints the SHA256 of the produced image at the end. That SHA is what you compare against the manifest — if they match, the image is exactly what was specified.

## §5 Developer reference

The golden image is built by combining three things:

- The base image — a pinned version of Home Assistant OS, downloaded from the official Home Assistant releases and verified against its known SHA256.
- The RoamCore layer — the contents of `homeassistant/custom_components/`, the RoamCore add-ons under `homeassistant/addons/`, and the RoamCore packages under `homeassistant/packages/`.
- The Dockerfile — the recipe for assembling the two layers into a single flashable image.

The full manifest lives at `scripts/build/hub-golden-image.manifest.yml`. It carries the base image URL, the base image SHA256, the list of files in the RoamCore layer, the output filename, and a placeholder for the output SHA256 that gets pinned after the first real bake.

To build the image on a Linux host with Docker installed:

```
bash scripts/build/hub-golden-image.sh
```

The script is idempotent — re-running it skips the download if the cached copy is still good, and skips the bake if the existing output SHA already matches the manifest pin.

To check the pipeline is healthy on any host:

```
bash scripts/checks/hub-golden-image-smoke.sh
```

The verifier checks that the build script exists and is executable, that the manifest parses as YAML, that the script references the manifest path, that the base image URL is reachable, that the base image SHA is a 64-character hex string, that the script's help text is in plain English, that the output filename ends in `.img.gz`, and that the script includes the retry-and-cache patterns that make a re-run safe.

Build-host prerequisites: Linux (the bake uses loop-mounts that are Linux-only), Docker (the script invokes the build via `docker build`), `curl`, `sha256sum`, `xz-utils`, and at least 5 GB of free disk for the cached base image + the working staging directory. Outbound HTTPS to `github.com` is required for the base-image download.

When the first real bake runs, copy the printed SHA256 into `output.expected_sha256` in `scripts/build/hub-golden-image.manifest.yml`. From that point on, the script's idempotency check skips the bake whenever the existing output already matches the pinned SHA — re-runs become safe no-ops.