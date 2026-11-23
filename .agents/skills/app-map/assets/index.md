---
title: My App Map
sub: How the app works, one module at a time · **tap a module or a box** to open its map
modules: [launch, onboarding, home, settings]
links:
  screens: {Splash: launch, Welcome: onboarding, Home: home}
  services: {HomeS: home}
---

## Screens · how the user moves

One or two sentences: where the app opens and how the user gets around.

```mermaid
flowchart TB
  subgraph Launch
    Splash["Splash<br/>SplashPage"]
  end
  Splash -->|not onboarded| Welcome["Welcome<br/>WelcomePage"]
  Splash -->|onboarded| Home["Home<br/>HomeScreen"]
```

- `───▷` opens
- `▭` tap to open its module

## Services · what the screens talk through

One or two sentences: the services that own shared concerns.

```mermaid
flowchart LR
  subgraph Screens
    HomeS["Home"]
  end
  subgraph Services
    Logic["WondersLogic"]
  end
  HomeS -->|getData| Logic
```

- `───▷` calls, labelled with the method
- `▭` tap to open its module
