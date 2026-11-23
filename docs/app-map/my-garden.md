---
title: My Garden Module
sub: "The plants the user has added, with planting and watering dates."
card_title: My garden
card: The user's planted plants and watering dates
---

## What it does

My garden is the first tab of Home. It lists every plant that has at least one row in `garden_plantings`, in a 2-column grid. Each card shows the plant's image, name, the date it was planted and the date it was last watered (formatted `MMM d, yyyy`), and "water in N days" from the plant's watering interval (7 days unless the catalog says otherwise). With no plantings, it shows an empty message and an **Add plant** button that scrolls the pager to the Plant list tab. Tapping a card opens that plant's details. The list stays subscribed for 5 s after the screen stops collecting (`WhileSubscribed(5000)`).

## Logic · class diagram {#classes}

The view-model exposes one Room query that joins each plant with its plantings; each card wraps one result in a small display model.

```mermaid
classDiagram
  direction LR
  class GardenScreen { <<page>> }
  class GardenPlantingListViewModel {
    <<view-model>>
    plantAndGardenPlantings
  }
  class GardenPlantingRepository {
    <<service>>
    getPlantedGardens()
  }
  class GardenPlantingDao {
    <<interface>>
    getPlantedGardens()
  }
  class PlantAndGardenPlantings {
    <<data>>
    plant
    gardenPlantings
  }
  class PlantAndGardenPlantingsViewModel {
    <<model>>
    plantName · imageUrl
    plantDateString · waterDateString
    wateringInterval
  }
  class Plant {
    <<data>>
    plantId · name
    wateringInterval
  }
  class GardenPlanting {
    <<data>>
    plantDate · lastWateringDate
  }
  GardenScreen --> GardenPlantingListViewModel : viewModel
  GardenPlantingListViewModel ..> GardenPlantingRepository : getPlantedGardens()
  GardenPlantingRepository ..> GardenPlantingDao : getPlantedGardens()
  GardenPlantingListViewModel o-- PlantAndGardenPlantings : plantAndGardenPlantings
  PlantAndGardenPlantings --> Plant : plant
  PlantAndGardenPlantings o-- GardenPlanting : gardenPlantings
  PlantAndGardenPlantingsViewModel --> PlantAndGardenPlantings : first planting
```

- `──▷` holds
- `◇──` list of
- `┄┄▷` uses

## Screen · widget composition {#widgets}

The screen picks between the empty state and the grid of cards.

```mermaid
classDiagram
  direction TB
  class GardenScreen { <<page>> }
  class EmptyGarden { <<widget>> }
  class Button { <<Add plant>> }
  class GardenList { <<widget>> }
  class LazyVerticalGrid { <<2 columns>> }
  class GardenListItem { <<widget>> }
  class ElevatedCard { <<plant card>> }
  class PlantAndGardenPlantingsViewModel { <<model>> }
  GardenScreen *-- EmptyGarden
  EmptyGarden *-- Button
  GardenScreen *-- GardenList
  GardenList *-- LazyVerticalGrid
  LazyVerticalGrid *-- GardenListItem
  GardenListItem *-- ElevatedCard
  GardenListItem --> PlantAndGardenPlantingsViewModel
```

- `◆──` contains
- `──▷` reads model

## Open a planted plant · sequence {#sequence}

The grid only appears once the join query returns at least one plant.

```mermaid
sequenceDiagram
  actor User
  participant Garden as GardenScreen
  participant VM as GardenPlantingListViewModel
  participant Repo as GardenPlantingRepository
  participant Dao as GardenPlantingDao
  participant Item as GardenListItem
  participant Nav as SunFlowerNavHost
  User->>Garden: opens My garden
  Garden->>VM: plantAndGardenPlantings
  VM->>Repo: getPlantedGardens()
  Repo->>Dao: getPlantedGardens()
  Dao-->>VM: plants joined with their plantings
  Note over Garden: empty list → EmptyGarden with Add plant
  VM-->>Garden: recomposes with the list
  Garden->>Item: one card per plant
  Item->>Item: wraps the plant for display
  User->>Item: taps a card
  Item->>Nav: tap callback with the plant
  Nav-->>User: opens plantDetail/{plantId}
```

## Key files {#files}

- `app/src/main/java/com/google/samples/apps/sunflower/compose/garden/` · garden grid, card, empty state
- `app/src/main/java/com/google/samples/apps/sunflower/viewmodels/GardenPlantingListViewModel.kt` · planted plants
- `app/src/main/java/com/google/samples/apps/sunflower/viewmodels/PlantAndGardenPlantingsViewModel.kt` · card text and dates
- `app/src/main/java/com/google/samples/apps/sunflower/data/GardenPlantingRepository.kt` · planting operations
- `app/src/main/java/com/google/samples/apps/sunflower/data/GardenPlantingDao.kt` · planting queries
- `app/src/main/java/com/google/samples/apps/sunflower/data/GardenPlanting.kt` · planting entity
- `app/src/main/java/com/google/samples/apps/sunflower/data/PlantAndGardenPlantings.kt` · plant + plantings relation
