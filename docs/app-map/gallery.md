---
title: Gallery Module
sub: "Unsplash photos of the plant, paged and pull-to-refresh."
card_title: Gallery
card: Unsplash photos of a plant
---

## What it does

Opened at `gallery/{plantName}` from a plant's detail page, only in builds with an Unsplash key. It searches Unsplash for the plant's name and shows the photos in a 2-column grid of cards labelled with the photographer's name, loading 25 per page starting at page 1 and stopping at the response's `total_pages`. Pulling down reloads the search; the spinner ends when the refresh finishes or fails. Tapping a photo opens the photographer's Unsplash profile in the browser with sunflower referral parameters; the back arrow returns to the plant.

## Logic · class diagram {#classes}

The view-model asks the repository for a paging stream; a paging source turns page keys into Unsplash search calls.

```mermaid
classDiagram
  direction LR
  class GalleryScreen { <<page>> }
  class GalleryViewModel {
    <<view-model>>
    plantPictures
    refreshData()
  }
  class UnsplashRepository {
    <<service>>
    getSearchResultStream(query)
  }
  class UnsplashPagingSource {
    <<service>>
    load(params)
    getRefreshKey(state)
  }
  class UnsplashService {
    <<interface>>
    searchPhotos(query, page, perPage, clientId)
    create()
  }
  class UnsplashSearchResponse {
    <<data>>
    results · totalPages
  }
  class UnsplashPhoto {
    <<data>>
    id · urls · user
  }
  class UnsplashPhotoUrls {
    <<data>>
    small
  }
  class UnsplashUser {
    <<data>>
    name · username
    attributionUrl
  }
  GalleryScreen --> GalleryViewModel : viewModel
  GalleryViewModel ..> UnsplashRepository : getSearchResultStream()
  UnsplashRepository ..> UnsplashPagingSource : builds
  UnsplashPagingSource ..> UnsplashService : searchPhotos()
  UnsplashService ..> UnsplashSearchResponse : returns
  UnsplashSearchResponse o-- UnsplashPhoto : results
  UnsplashPhoto --> UnsplashPhotoUrls : urls
  UnsplashPhoto --> UnsplashUser : user
```

- `──▷` holds
- `◇──` list of
- `┄┄▷` uses

## Screen · widget composition {#widgets}

A `Scaffold` with a back bar and a pull-to-refresh grid of photo cards.

```mermaid
classDiagram
  direction TB
  class GalleryScreen { <<page>> }
  class Scaffold { <<screen frame>> }
  class GalleryTopBar { <<widget>> }
  class LazyVerticalGrid { <<2 columns>> }
  class PhotoListItem { <<widget>> }
  class ImageListItem { <<widget>> }
  class PullToRefreshContainer { <<refresh spinner>> }
  class UnsplashPhoto { <<data>> }
  GalleryScreen *-- Scaffold
  Scaffold *-- GalleryTopBar
  Scaffold *-- LazyVerticalGrid
  Scaffold *-- PullToRefreshContainer
  LazyVerticalGrid *-- PhotoListItem
  PhotoListItem *-- ImageListItem
  PhotoListItem --> UnsplashPhoto
```

- `◆──` contains
- `──▷` reads model

## Browse a plant's photos · sequence {#sequence}

The view-model loads on creation, so the grid fills without any user action.

```mermaid
sequenceDiagram
  actor User
  participant Gal as GalleryScreen
  participant VM as GalleryViewModel
  participant Repo as UnsplashRepository
  participant Src as UnsplashPagingSource
  participant Api as UnsplashService
  User->>Gal: taps the gallery icon on a plant
  Gal->>VM: plantPictures
  VM->>VM: refreshData()
  VM->>Repo: getSearchResultStream(plantName)
  Repo->>Src: builds with page size 25
  Src->>Src: load(params)
  Src->>Api: searchPhotos(query, 1, perPage)
  Api-->>Src: results and total_pages
  Src-->>Gal: first page of photos
  Note over Src: next key stops at total_pages
  User->>Gal: pulls down
  Gal->>VM: refreshData()
  User->>Gal: taps a photo
  Gal-->>User: opens the photographer's attributionUrl
```

## Key files {#files}

- `app/src/main/java/com/google/samples/apps/sunflower/compose/gallery/` · gallery grid and top bar
- `app/src/main/java/com/google/samples/apps/sunflower/viewmodels/GalleryViewModel.kt` · photo stream and refresh
- `app/src/main/java/com/google/samples/apps/sunflower/data/UnsplashRepository.kt` · pager config
- `app/src/main/java/com/google/samples/apps/sunflower/data/UnsplashPagingSource.kt` · page keys and loads
- `app/src/main/java/com/google/samples/apps/sunflower/api/` · Retrofit Unsplash API
- `app/src/main/java/com/google/samples/apps/sunflower/data/` · Unsplash response models (`Unsplash*.kt`)
