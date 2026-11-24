---
title: Plant Detail Module
sub: "One plant: image, watering needs, description, add to garden, share and gallery."
card_title: Plant detail
card: A plant's page, add to garden and share
---

## What it does

Opened at `plantDetail/{plantId}` from either Home tab. A full-width header image sits above the plant's name, its watering needs ("every N days") and an HTML description with clickable links. While the plant is not in the garden a **+** button sits on the image's bottom edge; tapping it inserts a `GardenPlanting` dated today and shows a short "Added plant to garden" snackbar, after which the button disappears because `isPlanted` turns true. The gallery icon appears only when the build has an Unsplash key (`UNSPLASH_ACCESS_KEY` is not `"null"`) and opens `gallery/{plantName}`. Scrolling the name to within 190 dp of the top fades the header out and a top app bar with the plant's name in; back and share stay available in both states, and share opens the system chooser with a text about the plant.

## Logic · class diagram {#classes}

The view-model follows the plant and whether it is planted; a small scroller object decides when the toolbar shows.

```mermaid
classDiagram
  direction LR
  class PlantDetailsScreen { <<page>> }
  class PlantDetailViewModel {
    <<view-model>>
    plantId
    plant · isPlanted
    showSnackbar
    plantInGarden()
    dismissSnackbar()
    hasValidUnsplashKey()
  }
  class PlantRepository {
    <<service>>
    getPlant(plantId)
  }
  class GardenPlantingRepository {
    <<service>>
    isPlanted(plantId)
    createGardenPlanting(plantId)
  }
  class PlantDetailsCallbacks {
    <<data>>
    onFabClick · onBackClick
    onShareClick · onGalleryClick
  }
  class PlantDetailsScroller {
    <<model>>
    scrollState · namePosition
    toolbarTransitionState
    getToolbarState(density)
  }
  class ToolbarState { <<enum>> }
  class GalleryScreen { <<page>> }
  PlantDetailsScreen --> PlantDetailViewModel : plantDetailsViewModel
  PlantDetailViewModel ..> PlantRepository : getPlant()
  PlantDetailViewModel ..> GardenPlantingRepository : isPlanted()
  PlantDetailViewModel ..> GardenPlantingRepository : createGardenPlanting()
  PlantDetailsScreen ..> PlantDetailsCallbacks : builds
  PlantDetailsScroller --> ToolbarState : toolbarTransitionState
  PlantDetailsScreen ..> GalleryScreen : opens
```

- `──▷` holds
- `┄┄▷` uses · opens

## Screen · widget composition {#widgets}

A scrolling column with the header image, the add button and the plant's information, with a toolbar layered on top.

```mermaid
classDiagram
  direction TB
  class PlantDetailsScreen { <<page>> }
  class TextSnackbarContainer { <<widget>> }
  class PlantDetails { <<widget>> }
  class PlantDetailsContent { <<widget>> }
  class PlantImage { <<widget>> }
  class PlantFab { <<widget>> }
  class PlantInformation { <<widget>> }
  class PlantDescription { <<widget>> }
  class PlantToolbar { <<widget>> }
  class PlantDetailsToolbar { <<widget>> }
  class PlantHeaderActions { <<widget>> }
  class PlantDetailsScroller { <<model>> }
  class PlantDetailsCallbacks { <<data>> }
  PlantDetailsScreen *-- TextSnackbarContainer
  TextSnackbarContainer *-- PlantDetails
  PlantDetails *-- PlantDetailsContent
  PlantDetails *-- PlantToolbar
  PlantDetails --> PlantDetailsScroller
  PlantDetails --> PlantDetailsCallbacks
  PlantDetailsContent *-- PlantImage
  PlantDetailsContent *-- PlantFab
  PlantDetailsContent *-- PlantInformation
  PlantInformation *-- PlantDescription
  PlantToolbar *-- PlantDetailsToolbar
  PlantToolbar *-- PlantHeaderActions
```

- `◆──` contains
- `──▷` reads model

## Header and toolbar · state machine {#states}

`PlantToolbar` shows the header buttons while `HIDDEN` and the full app bar while `SHOWN`; both fade with a low-stiffness spring.

```mermaid
stateDiagram-v2
  [*] --> HIDDEN
  HIDDEN --> SHOWN : scroll passes name position − 190 dp
  SHOWN --> HIDDEN : scroll back above it
```

## Add a plant to My garden · sequence {#sequence}

The + button hides itself because `isPlanted` is a live Room query, not because the tap hides it.

```mermaid
sequenceDiagram
  actor User
  participant Screen as PlantDetailsScreen
  participant VM as PlantDetailViewModel
  participant GRepo as GardenPlantingRepository
  participant Dao as GardenPlantingDao
  participant Snack as TextSnackbarContainer
  User->>Screen: opens a plant
  Screen->>VM: plant · isPlanted
  VM->>GRepo: isPlanted(plantId)
  GRepo-->>Screen: false → shows the + button
  User->>Screen: taps +
  Screen->>VM: plantInGarden()
  VM->>GRepo: createGardenPlanting(plantId)
  GRepo->>Dao: insertGardenPlanting(gardenPlanting)
  Dao-->>Screen: isPlanted emits true, + disappears
  VM-->>Screen: showSnackbar = true
  Screen->>Snack: shows "Added plant to garden"
  Snack->>VM: dismissSnackbar()
```

## Key files {#files}

- `app/src/main/java/com/google/samples/apps/sunflower/compose/plantdetail/` · detail screen, toolbar, scroller
- `app/src/main/java/com/google/samples/apps/sunflower/viewmodels/PlantDetailViewModel.kt` · plant, planted state, add
- `app/src/main/java/com/google/samples/apps/sunflower/compose/utils/TextSnackbarContainer.kt` · snackbar wrapper
- `app/src/main/java/com/google/samples/apps/sunflower/compose/Modifiers.kt` · visible() modifier
- `app/src/main/java/com/google/samples/apps/sunflower/compose/Dimens.kt` · paddings and header height
