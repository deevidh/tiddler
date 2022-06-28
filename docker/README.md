# XTide Dockerfile

## Overview

Based on Ubuntu and uses xtide to generate tidal data for Leith.

## Build

```bash
docker build -t xtide-ubuntu .
```

## Run

```bash
docker run -t xtide-ubuntu -l leith -pi 28 -ml 3.0m -fc -zy
```

Information on xtide CLI usage can be found here:
- [XTide - Using the command line interface](https://flaterco.com/xtide/tty.html)
- [XTide - Modes](https://flaterco.com/xtide/modes.html)