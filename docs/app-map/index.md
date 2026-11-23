---
title: Sunflower App Map
sub: How the app works, one module at a time · **tap a module or a box** to open its map
modules: [launch, home, my-garden, plant-list, plant-detail, gallery]
links:
  screens: {Act: launch, Home: home, Garden: my-garden, List: plant-list, Detail: plant-detail, Gal: gallery, Share: plant-detail, Profile: gallery}
  services: {HomeS: home, GardenS: my-garden, ListS: plant-list, DetailS: plant-detail, GalS: gallery, SeedS: launch}
---

## Screens · how the user moves

The single activity opens Home on the My garden tab; plants open their detail page from either tab, and the detail page leads to the gallery.

```mermaid
flowchart TB
  subgraph LaunchArea [Launch]
    Act["App start<br/>GardenActivity"]
  end
  subgraph HomeArea [Home]
    Home["Home<br/>HomeScreen"]
  end
  subgraph GardenArea [My garden]
    Garden["My garden tab<br/>GardenScreen"]
  end
  subgraph ListArea [Plant list]
    List["Plant list tab<br/>PlantListScreen"]
  end
  subgraph DetailArea [Plant detail]
    Detail["Plant detail<br/>PlantDetailsScreen"]
    Share["Share chooser"]
  end
  subgraph GalArea [Gallery]
    Gal["Gallery<br/>GalleryScreen"]
    Profile["Photographer on unsplash.com"]
  end
  Act -->|home route| Home
  Home -->|tab 1| Garden
  Home -->|tab 2| List
  Garden -->|Add plant| List
  Garden -->|tap a plant| Detail
  List -->|tap a plant| Detail
  Detail -->|share| Share
  Detail -->|gallery icon, with Unsplash key| Gal
  Gal -->|tap a photo| Profile
```

- `───▷` opens
- `▭` tap to open its module

## Services · what the screens talk through {#services}

Two Room repositories are shared by the garden, the plant list and the detail page; the gallery alone talks to Unsplash.

```mermaid
flowchart LR
  subgraph Screens
    HomeS["Home"]
    GardenS["My garden"]
    ListS["Plant list"]
    DetailS["Plant detail"]
    GalS["Gallery"]
    SeedS["Launch seed"]
  end
  subgraph Services
    ListVM["PlantListViewModel"]
    PRepo["PlantRepository"]
    GRepo["GardenPlantingRepository"]
    PDao["PlantDao"]
    GDao["GardenPlantingDao"]
    DB["AppDatabase"]
    URepo["UnsplashRepository"]
    Src["UnsplashPagingSource"]
    Api["UnsplashService"]
  end
  HomeS -->|updateData| ListVM
  ListS -->|plants| ListVM
  ListVM -->|getPlants| PRepo
  DetailS -->|getPlant| PRepo
  DetailS -->|createGardenPlanting| GRepo
  DetailS -->|isPlanted| GRepo
  GardenS -->|getPlantedGardens| GRepo
  PRepo -->|getPlants| PDao
  GRepo -->|insertGardenPlanting| GDao
  PDao --- DB
  GDao --- DB
  SeedS -->|upsertAll| PDao
  GalS -->|getSearchResultStream| URepo
  URepo -->|load| Src
  Src -->|searchPhotos| Api
```

- `───▷` calls, labelled with the method
- `───` belongs to
- `▭` tap to open its module
