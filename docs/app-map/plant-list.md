---
title: Plant List Module
sub: "The full plant catalog, optionally filtered to one grow zone."
card_title: Plant list
card: The plant catalog with a grow-zone filter
---

## What it does

Plant list is the second tab of Home. It shows every plant in the catalog, sorted by name, as a 2-column grid of image cards. The filter icon in the Home app bar toggles a grow-zone filter: off shows all plants, on shows only grow zone 9 (the zone is fixed in `updateData()`). The chosen zone is written to `SavedStateHandle`, so it survives process death; "no filter" is stored as -1. Tapping a card opens the plant's details.

## Logic · class diagram {#classes}

The current grow zone is a flow; switching it switches which Room query the list follows.

```mermaid
classDiagram
  direction LR
  class PlantListScreen { <<page>> }
  class PlantListViewModel {
    <<view-model>>
    plants
    updateData()
    setGrowZoneNumber(num)
    clearGrowZoneNumber()
    isFiltered()
  }
  class PlantRepository {
    <<service>>
    getPlants()
    getPlantsWithGrowZoneNumber(growZoneNumber)
  }
  class PlantDao {
    <<interface>>
    getPlants()
    getPlantsWithGrowZoneNumber(growZoneNumber)
  }
  class Plant {
    <<data>>
    plantId · name
    growZoneNumber
    imageUrl
  }
  class SavedStateHandle { <<saved grow zone>> }
  PlantListScreen --> PlantListViewModel : viewModel
  PlantListViewModel ..> PlantRepository : getPlants()
  PlantListViewModel ..> PlantRepository : getPlantsWithGrowZoneNumber()
  PlantRepository ..> PlantDao : getPlants()
  PlantListViewModel ..> SavedStateHandle : saves the zone
  PlantListViewModel o-- Plant : plants
```

- `──▷` holds
- `◇──` list of
- `┄┄▷` uses

## Screen · widget composition {#widgets}

A grid of shared image cards; the same card is reused by the Gallery.

```mermaid
classDiagram
  direction TB
  class PlantListScreen { <<page>> }
  class LazyVerticalGrid { <<2 columns>> }
  class PlantListItem { <<widget>> }
  class ImageListItem { <<widget>> }
  class Card { <<image + name>> }
  class Plant { <<data>> }
  PlantListScreen *-- LazyVerticalGrid
  LazyVerticalGrid *-- PlantListItem
  PlantListItem *-- ImageListItem
  ImageListItem *-- Card
  PlantListItem --> Plant
```

- `◆──` contains
- `──▷` reads model

## Filter to grow zone 9 · sequence {#sequence}

`flatMapLatest` drops the old query as soon as the zone changes.

```mermaid
sequenceDiagram
  actor User
  participant Bar as HomeTopAppBar
  participant VM as PlantListViewModel
  participant Repo as PlantRepository
  participant Dao as PlantDao
  participant List as PlantListScreen
  User->>List: opens Plant list
  List->>VM: plants
  VM->>Repo: getPlants()
  Repo->>Dao: getPlants()
  Dao-->>List: all plants, by name
  User->>Bar: taps filter
  Bar->>VM: updateData()
  VM->>VM: setGrowZoneNumber(9)
  Note over VM: the zone is also saved to SavedStateHandle
  VM->>Repo: getPlantsWithGrowZoneNumber(9)
  Repo->>Dao: getPlantsWithGrowZoneNumber(9)
  Dao-->>List: zone 9 plants only
  User->>Bar: taps filter again
  Bar->>VM: updateData()
  VM->>VM: clearGrowZoneNumber()
  VM-->>List: back to all plants
```

## Key files {#files}

- `app/src/main/java/com/google/samples/apps/sunflower/compose/plantlist/` · plant grid and shared image card
- `app/src/main/java/com/google/samples/apps/sunflower/viewmodels/PlantListViewModel.kt` · plants and grow-zone filter
- `app/src/main/java/com/google/samples/apps/sunflower/data/PlantRepository.kt` · plant queries
- `app/src/main/java/com/google/samples/apps/sunflower/data/PlantDao.kt` · Room plant queries
- `app/src/main/java/com/google/samples/apps/sunflower/data/Plant.kt` · plant entity
- `app/src/main/java/com/google/samples/apps/sunflower/utilities/GrowZoneUtil.kt` · latitude → zone (only used by tests)
