---
title: Home Module
sub: "The shell: app bar, the two tabs and the grow-zone filter."
card_title: Home
card: App bar and the My garden / Plant list tabs
---

## What it does

Home is the start route (`home`). A centred app bar shows the app name and collapses as the content scrolls (`enterAlwaysScrollBehavior`). Below it a `TabRow` and a `HorizontalPager` hold the two pages of `SunflowerPage`: **My garden** and **Plant list**; tapping a tab animates the pager to it. The filter icon appears only while the Plant list page is showing; it calls `PlantListViewModel.updateData()`, which toggles between all plants and grow zone 9. Tapping a plant on either page navigates to `plantDetail/{plantId}`.

## Logic · class diagram {#classes}

Home owns the pager and the filter button; each tab page brings its own view-model.

```mermaid
classDiagram
  direction LR
  class SunFlowerNavHost { <<widget>> }
  class Screen {
    <<data>>
    route
    navArguments
  }
  class HomeScreen { <<page>> }
  class SunflowerPage {
    <<enum>>
    MY_GARDEN
    PLANT_LIST
    titleResId · drawableResId
  }
  class PlantListViewModel {
    <<view-model>>
    updateData()
  }
  class GardenScreen { <<page>> }
  class PlantListScreen { <<page>> }
  SunFlowerNavHost ..> Screen : route
  SunFlowerNavHost ..> HomeScreen : startDestination
  HomeScreen o-- SunflowerPage : pages
  HomeScreen ..> PlantListViewModel : updateData()
  HomeScreen ..> GardenScreen : MY_GARDEN page
  HomeScreen ..> PlantListScreen : PLANT_LIST page
```

- `◇──` list of
- `┄┄▷` uses · opens

## Screen · widget composition {#widgets}

A `Scaffold` with the collapsing app bar on top and the tab row plus pager below.

```mermaid
classDiagram
  direction TB
  class HomeScreen { <<page>> }
  class Scaffold { <<screen frame>> }
  class HomeTopAppBar { <<widget>> }
  class CenterAlignedTopAppBar { <<app name + filter icon>> }
  class HomePagerScreen { <<widget>> }
  class TabRow { <<tabs>> }
  class HorizontalPager { <<pages>> }
  class GardenScreen { <<page>> }
  class PlantListScreen { <<page>> }
  class SunflowerPage { <<enum>> }
  HomeScreen *-- Scaffold
  Scaffold *-- HomeTopAppBar
  HomeTopAppBar *-- CenterAlignedTopAppBar
  Scaffold *-- HomePagerScreen
  HomePagerScreen *-- TabRow
  HomePagerScreen *-- HorizontalPager
  HorizontalPager *-- GardenScreen
  HorizontalPager *-- PlantListScreen
  HomePagerScreen --> SunflowerPage
```

- `◆──` contains
- `──▷` reads model

## Switch tab and filter the plant list · sequence {#sequence}

The filter icon only exists while the pager's current page is Plant list.

```mermaid
sequenceDiagram
  actor User
  participant Home as HomeScreen
  participant Pager as HomePagerScreen
  participant Bar as HomeTopAppBar
  participant VM as PlantListViewModel
  participant List as PlantListScreen
  User->>Home: opens the app
  Home->>Pager: shows My garden (page 0)
  User->>Pager: taps the Plant list tab
  Pager->>Pager: scrolls to page 1
  Pager->>List: composes the plant grid
  Home->>Bar: currentPage is PLANT_LIST
  Bar-->>User: shows the filter icon
  User->>Bar: taps filter
  Bar->>VM: updateData()
  Note over VM: not filtered → zone 9 · filtered → all plants
  VM-->>List: plants emits the new list
  List-->>User: grid shows the filtered plants
```

## Key files {#files}

- `app/src/main/java/com/google/samples/apps/sunflower/compose/home/` · home screen, pager, app bar, tabs enum
- `app/src/main/java/com/google/samples/apps/sunflower/compose/SunflowerApp.kt` · navigation between screens
