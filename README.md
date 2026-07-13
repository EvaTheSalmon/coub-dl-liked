# coub-dl

<div align="center">
    <img src=./logo.png width=400 />
</div>

[![build](https://github.com/mrcsin/coub-dl/actions/workflows/ci.yml/badge.svg)](https://github.com/mrcsin/coub-dl/actions/workflows/ci.yml)
[![Coverage Status](https://coveralls.io/repos/github/mrcsin/coub-dl/badge.svg?branch=master)](https://coveralls.io/github/mrcsin/coub-dl?branch=master)
[![Go Report Card](https://goreportcard.com/badge/github.com/mrcsin/coub-dl)](https://goreportcard.com/report/github.com/mrcsin/coub-dl)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A small command-line tool to download videos from [coub.com](https://coub.com).

A coub is a short looping video with a separate, usually longer, audio track.
`coub-dl` fetches both streams, loops the video to match the audio length, and
muxes them into a single portable `.mp4`. It copies Coub's existing video and
audio streams (typically H.264 and MP3) without re-encoding, and embeds the
title, author, tags, and source link as metadata. Already-downloaded files are
skipped.

## Requirements

- [Go 1.26+](https://go.dev/dl/) to build
- [`ffmpeg`](https://ffmpeg.org/) available in `PATH`

## Install

Prebuilt binaries for Linux, macOS, and Windows are attached to each
[release](https://github.com/mrcsin/coub-dl/releases). Or install with Go:

```sh
go install github.com/mrcsin/coub-dl@latest
```

Or build from source:

```sh
git clone https://github.com/mrcsin/coub-dl
cd coub-dl
go build -o coub-dl .
```

## Usage

### Download a single coub

```sh
coub-dl download [-out dir] [-name file] <link|permalink>
```

```sh
coub-dl download https://coub.com/view/2uywin   # -> ./2uywin.mp4
coub-dl download -out clips 2uywin              # -> clips/2uywin.mp4
coub-dl download -name funny-cat 2uywin         # -> ./funny-cat.mp4
```

No token is needed — single coubs are public. The output path is printed to
stdout; everything else goes to stderr.

### Sync all your liked coubs

```sh
coub-dl sync [-out dir] [-workers n]
```

```sh
export API_TOKEN=your_token
coub-dl sync                    # -> videos/YYYY/MM/<id>.mp4
coub-dl sync -out archive -workers 10
```

`sync` streams your likes page by page and downloads them concurrently
(5 workers by default), laying files out by month. It is idempotent: re-running
it re-downloads only what failed or is missing, so a second run is a free retry.

> **Note:** flags must come before the positional link
> (`coub-dl download -out clips 2uywin`, not `coub-dl download 2uywin -out clips`).

### Getting an API token

1. Log in to [coub.com](https://coub.com).
2. Open the page source of any page (`Ctrl+U`) and search for `api_token`.
3. Copy the 128-character value into the `API_TOKEN` environment variable.

## Docker

Run `coub-dl` without a local Go toolchain or `ffmpeg` install. The image bundles
`ffmpeg` and CA certificates and runs as a non-root user; both subcommands work.

```sh
docker build -t coub-dl .
docker run --rm -v "$PWD:/data" coub-dl download 2uywin -out /data
docker run --rm -e API_TOKEN=xxx -v "$PWD/videos:/data/videos" coub-dl sync -out /data/videos
```

The container runs as uid 1000, so downloaded files are owned by that uid. Pass
`--user "$(id -u):$(id -g)"` to own them as the host user instead (the mounted
directory must then be writable by that uid).

### Compose

`docker-compose.yml` defines a one-shot `sync` service:

```sh
export API_TOKEN=xxx
docker compose run --rm coub-dl
```

It builds the image, reads `API_TOKEN` from the environment, mounts `./videos`
to `/data/videos`, and exits when the sync completes.

### Scheduling

Keep the container a one-shot batch job and drive the schedule from outside it.
The simplest option is a host crontab entry:

```cron
0 3 * * *  cd /path/to/coub-dl && API_TOKEN=xxx docker compose run --rm coub-dl
```

`sync` exits non-zero if interrupted (`130`) or on error (`1`), so a wrapper can
tell an aborted run from a clean one. A commented `ofelia` sidecar in
`docker-compose.yml` shows a compose-only alternative.

## Flags

| Flag       | Commands           | Default        | Description                          |
| ---------- | ------------------ | -------------- | ------------------------------------ |
| `-out`     | `download`, `sync` | `.` / `videos` | output directory                     |
| `-name`    | `download`         | coub id        | output file name (without extension) |
| `-workers` | `sync`             | `5`            | concurrent downloads                 |

## Exit codes

`0` success · `1` a download or fetch failed · `64` bad usage / missing token ·
`130` interrupted (Ctrl-C / SIGTERM).

## Tests

```sh
go test ./...          # full suite
go test -short ./...   # skips the slow retry-backoff test
```

## License

[MIT](LICENSE)
