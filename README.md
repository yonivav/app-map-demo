# App Map demo: the map follows the code

A live demo of [App Map](https://github.com/yonivav/app-map), an AI agent skill that maps a mobile
app into clickable UML. This repo is Google's [Sunflower](https://github.com/android/sunflower)
sample (Kotlin, Jetpack Compose, Apache-2.0; its original README is in
[SUNFLOWER-README.md](SUNFLOWER-README.md)) with App Map installed in automatic mode:

- **The map:** [docs/app-map/](docs/app-map/index.md) (Markdown GitHub renders), and the
  clickable site at **https://yonivav.github.io/app-map-demo/docs/app-map/**.
- **On every pull request** [`.github/workflows/app-map-update.yml`](.github/workflows/app-map-update.yml)
  checks whether the code change leaves the map behind. If it does, an AI agent (Gemini CLI, on
  Google's free tier) updates the affected pages and commits them to the pull request.
  [`.github/workflows/app-map-check.yml`](.github/workflows/app-map-check.yml) builds and checks
  the map.
- **While coding with an agent,** the rule in [AGENTS.md](AGENTS.md) and [CLAUDE.md](CLAUDE.md)
  makes it update the map in the same change.

See the pull requests for the bot at work: a developer changes code, the map follows.

Set up the same in your app: `~/.app-map/install.sh --auto --agent gemini` (see the
[App Map README](https://github.com/yonivav/app-map#make-it-automatic)).
