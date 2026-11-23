---
title: Home Module
sub: "One sentence: what the user does here."
card_title: Home
card: 4–8 words for the overview card
screenshots:
  - file: shots/home/01_carousel.jpg
    caption: A wonder in the carousel
---

## What it does

3–6 plain sentences: what the user gets, the rules the code enforces (timings, limits, what is
saved) with the real numbers, and where the module hands off.

## Logic · class diagram {#classes}

One sentence naming the main idea, not listing boxes.

```mermaid
classDiagram
  direction LR
  class HomeScreen { <<page>> }
  class WondersLogic {
    <<service>>
    all
    getData(type)
  }
  HomeScreen ..> WondersLogic : getData()
```

- `──▷` holds
- `◇──` list of
- `┄┄▷` uses
- `──▷|` extends

## Screen · widget composition {#widgets}

One sentence: how the screen is put together.

```mermaid
classDiagram
  direction TB
  class HomeScreen { <<page>> }
```

- `◆──` contains
- `──▷` reads model
- `┄┄▷` builds

## Swipe to the next wonder · sequence {#sequence}

One sentence on the rule the flow depends on.

```mermaid
sequenceDiagram
  actor User
  participant Home as HomeScreen
  User->>Home: swipe left
```

## Key files {#files}

- `lib/ui/screens/home/wonders_home_screen.dart` · carousel and swipe handling
